import json
import logging
from typing import Dict, Any
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.models.schemas import InterviewQuestionResponse, AnswerEvaluationResponse
from app.services.interview_dataset_service import dataset_service
from app.services.scoring_service import scoring_service

logger = logging.getLogger(__name__)

class OpenRouterLLMService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY is not set. API calls will fail.")
        
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key or "missing_api_key_override",
            timeout=45.0,
        )
        self.models = [settings.OPENROUTER_MODEL] + [
            m for m in [
                "google/gemma-4-26b-a4b-it:free",
                "google/gemma-4-31b-it:free",
                "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                "liquid/lfm-2.5-2.6b:free",
            ] if m != settings.OPENROUTER_MODEL
        ]

    async def generate_question(self, resume_text: str, job_role: str, difficulty: str) -> InterviewQuestionResponse:
        """Generates a single resume-specific interview question."""
        exemplars = dataset_service.find_question_exemplars(job_role, limit=2)
        exemplar_prompt = ""
        if exemplars:
            exemplar_prompt = "\nHere are high-quality reference questions from our expert interview dataset:\n"
            for ex in exemplars:
                target = ex.get("target", {})
                exemplar_prompt += f"- Topic: {ex.get('topic')}\n  Question: {target.get('question')}\n  Expected evaluation points: {', '.join(target.get('expected_points', []))}\n"

        prompt = f"""
You are an expert technical interviewer hiring for a {difficulty} level {job_role} role.
Read the provided resume carefully.

Resume:
{resume_text}
{exemplar_prompt}
Task:
1. Generate EXACTLY ONE interview question based on the candidate's resume.
2. The question MUST directly relate to something actually present in the resume (a project, technology, work experience, education, achievement, or technical skill).
3. Do not invent resume information.
4. Do not ask generic questions like "Tell me about yourself."
5. Match the difficulty level ({difficulty}).

You MUST return the result as a strict JSON object with exactly the following schema:
{{
    "question": "The interview question",
    "question_type": "resume_based",
    "topic": "The specific topic from the resume (e.g., 'React hooks in E-commerce project')",
    "source": "resume"
}}
"""
        messages = [
            {"role": "system", "content": "You are a JSON-only API. You must strictly output valid JSON matching the requested schema. Do not include markdown formatting or backticks."},
            {"role": "user", "content": prompt}
        ]
        
        last_error = None
        for i, model in enumerate(self.models[:2]):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=3.5
                )
                
                content = response.choices[0].message.content
                if content is None:
                    logger.warning(f"Model {model} returned empty content, trying next model...")
                    last_error = ValueError(f"Model {model} returned empty content")
                    continue
                    
                # Clean up if model mistakenly included markdown
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                    
                parsed_json = json.loads(content)
                logger.info(f"Successfully generated question using model: {model}")
                return InterviewQuestionResponse(**parsed_json)
                
            except json.JSONDecodeError as e:
                logger.error(f"Model {model} returned invalid JSON: {content[:50]}")
                last_error = ValueError(f"AI returned invalid response (non-JSON). Content: {content[:50]}")
                continue
            except ValidationError as e:
                logger.error(f"Model {model} output failed Pydantic validation: {e.errors()}")
                last_error = ValueError("The LLM returned JSON that does not match the required schema.")
                continue
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Model {model} failed: {error_str[:100]}")
                last_error = RuntimeError(f"OpenRouter API request failed: {error_str}")
                if "429" in error_str or "rate-limited" in error_str.lower() or "connection" in error_str.lower():
                    logger.info("OpenRouter free tier rate-limited. Switching instantly to dataset intelligence.")
                    break
                continue
        
        # All models failed: fallback to dataset exemplar
        logger.error(f"All models failed. Last error: {last_error}")
        if exemplars:
            ex = exemplars[0]
            target = ex.get("target", {})
            if target.get("question"):
                return InterviewQuestionResponse(
                    question=target.get("question"),
                    question_type="resume_based",
                    topic=ex.get("topic") or "Technical Architecture",
                    source="dataset_exemplar"
                )
        return InterviewQuestionResponse(
            question=f"Could you elaborate on your experience as a {job_role}, specifically focusing on the skills mentioned in your resume?",
            question_type="resume_based",
            topic="General Experience",
            source="resume_fallback"
        )


    async def evaluate_answer(self, resume_text: str, job_role: str, question: str, answer: str) -> AnswerEvaluationResponse:
        """Evaluates a candidate's answer and optionally provides a follow-up question."""
        followup_exemplars = dataset_service.find_followup_exemplars(job_role, limit=2)
        exemplar_prompt = ""
        if followup_exemplars:
            exemplar_prompt = "\nHere are reference follow-up question strategies from our expert interview dataset:\n"
            for ex in followup_exemplars:
                target = ex.get("target", {})
                nq = target.get("next_question") or {}
                if nq and nq.get("question"):
                    exemplar_prompt += f"- Action: {target.get('action')}, Topic: {ex.get('topic')}\n  Follow-up Question: {nq.get('question')}\n"

        prompt = f"""
You are an expert technical interviewer hiring for a {job_role} role.

Resume:
{resume_text}

Interview Question:
{question}

Candidate Answer:
{answer}
{exemplar_prompt}
Task:
1. Evaluate the candidate's answer based on Relevance, Technical depth, Correctness, Clarity, and Completeness. Each score must be an integer from 0 to 100.
2. Provide a brief list of strengths and areas for improvement (improvements).
3. Provide a brief overall evaluation narrative.
4. Keep feedback interview-related, professional, and do not invent facts about the resume. Do not judge based on protected characteristics.
5. If the answer needs clarification or deeper investigation into their experience, set follow_up_needed to true and generate exactly ONE follow-up question.
6. The follow-up question must connect the resume, the previous question, and the candidate's answer. Do not generate unrelated generic questions. Do not claim they used a technology not mentioned.
7. If the answer is complete and satisfactory, set follow_up_needed to false and follow_up_question to null.

You MUST return the result as a strict JSON object with exactly the following schema:
{{
    "score": <0-100>,
    "relevance": <0-100>,
    "technical_depth": <0-100>,
    "clarity": <0-100>,
    "completeness": <0-100>,
    "strengths": ["..."],
    "improvements": ["..."],
    "evaluation": "...",
    "follow_up_needed": true/false,
    "follow_up_question": "..." or null
}}
"""

        messages = [
            {"role": "system", "content": "You are a JSON-only API. You must strictly output valid JSON matching the requested schema. Do not include markdown formatting or backticks."},
            {"role": "user", "content": prompt}
        ]

        last_error = None
        for i, model in enumerate(self.models[:2]):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=3.5
                )
                
                content = response.choices[0].message.content
                if content is None:
                    logger.warning(f"Model {model} returned empty content, trying next model...")
                    last_error = ValueError(f"Model {model} returned empty content")
                    continue
                    
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                    
                parsed_json = json.loads(content)
                logger.info(f"Successfully evaluated answer using model: {model}")
                return AnswerEvaluationResponse(**parsed_json)
                
            except json.JSONDecodeError as e:
                logger.error(f"Model {model} returned invalid JSON: {content[:50]}")
                last_error = ValueError(f"AI returned invalid response (non-JSON). Content: {content[:50]}")
                continue
            except ValidationError as e:
                logger.error(f"Model {model} output failed Pydantic validation: {e.errors()}")
                last_error = ValueError("The LLM returned JSON that does not match the required schema.")
                continue
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Model {model} failed: {error_str[:100]}")
                last_error = RuntimeError(f"OpenRouter API request failed: {error_str}")
                if "429" in error_str or "rate-limited" in error_str.lower() or "connection" in error_str.lower():
                    logger.info("OpenRouter free tier rate-limited. Switching instantly to dataset intelligence.")
                    break
                continue
        
        # All models failed, return an honest objective evaluation instantly
        logger.error(f"All models failed to evaluate. Last error: {last_error}")
        res = scoring_service.evaluate(
            question=question,
            answer=answer,
            job_role=job_role,
            resume_text=resume_text
        )
        return AnswerEvaluationResponse(
            score=res["score"],
            relevance=res["relevance"],
            technical_depth=res["technical_depth"],
            clarity=res["clarity"],
            completeness=res["completeness"],
            strengths=res["strengths"],
            improvements=res["improvements"],
            evaluation=res["evaluation"],
            follow_up_needed=res["follow_up_needed"],
            follow_up_question=(
                f"You mentioned that briefly. Could you dive deeper into the specific tools, architecture, and tradeoffs involved in your approach?"
                if res["follow_up_needed"] else None
            )
        )

    def compute_fast_evaluation(self, question: str, answer: str, job_role: str, resume_text: str, difficulty: str = "Medium") -> AnswerEvaluationResponse:
        """High-speed honest evaluation based on transparent rubric metrics."""
        res = scoring_service.evaluate(
            question=question,
            answer=answer,
            job_role=job_role,
            resume_text=resume_text,
            difficulty=difficulty
        )

        return AnswerEvaluationResponse(
            score=res["score"],
            relevance=res["relevance"],
            technical_depth=res["technical_depth"],
            clarity=res["clarity"],
            completeness=res["completeness"],
            strengths=res["strengths"],
            improvements=res["improvements"],
            evaluation=res["evaluation"],
            follow_up_needed=res["follow_up_needed"],
            follow_up_question=None
        )

    async def handle_turn(self, resume_text: str, job_role: str, difficulty: str, question: str, answer: str, turn_index: int, phase: str):
        """Unified 3-part interview round: executes in < 0.5s for instant candidate flow."""
        import asyncio

        # 1. High-speed evaluation: try cloud LLM with 1.2s timeout, otherwise instant heuristic
        try:
            eval_res = await asyncio.wait_for(
                self.evaluate_answer(
                    resume_text=resume_text,
                    job_role=job_role,
                    question=question,
                    answer=answer
                ),
                timeout=1.2
            )
        except Exception:
            eval_res = self.compute_fast_evaluation(question, answer, job_role, resume_text, difficulty)

        word_count = len(answer.strip().split())
        is_shallow = word_count < 14 or eval_res.technical_depth < 55 or eval_res.completeness < 55

        # 2. Determine 3-Part Flow instantly
        next_question = ""
        next_phase = phase
        is_followup = False

        if phase == "intro" or turn_index <= 1:
            # Transition from Part 1 (Intro) to Part 2 (Technical)
            next_phase = "technical"
            tech_q = dataset_service.get_fast_technical_question(resume_text, job_role, difficulty, index=0)
            next_question = f"Thank you for the introduction! Let's dive into your technical experience:\n\n{tech_q}"

        elif phase == "technical" or (turn_index >= 2 and turn_index <= 4):
            # In Part 2: Technical
            if is_shallow and turn_index < 4:
                # Ask a dynamic follow-up to probe deeper into their technical answer
                is_followup = True
                next_phase = "technical"
                skills = dataset_service.extract_key_skills(answer + " " + question + " " + resume_text)
                primary_topic = skills[0] if skills else "this architecture"
                followup_templates = [
                    f"You mentioned {primary_topic} briefly. Could you dive deeper into your implementation, specifically detailing the model architecture, configuration choices, and how you evaluated performance?",
                    f"Regarding your work with {primary_topic}, what specific challenges or edge cases did you encounter, and what engineering tradeoffs guided your decisions?",
                    f"Could you elaborate further on how {primary_topic} was deployed and tested, and how you handled latency or scaling issues?"
                ]
                next_question = followup_templates[turn_index % len(followup_templates)]
            elif turn_index >= 4:
                # Transition to Part 3 (Soft Skills & Behavioral)
                next_phase = "softskill"
                soft_q = dataset_service.get_softskill_question(0)
                next_question = f"Great technical discussion. Now let's explore your teamwork and problem-solving approach:\n\n{soft_q}"
            else:
                # Next technical question from resume
                next_phase = "technical"
                next_question = dataset_service.get_fast_technical_question(resume_text, job_role, difficulty, index=turn_index)

        else:
            # Part 3: Soft Skills & Overall
            next_phase = "softskill"
            soft_index = max(1, turn_index - 4)
            if soft_index >= 3:
                next_phase = "completed"
                next_question = dataset_service.get_softskill_question(3)
            else:
                next_question = dataset_service.get_softskill_question(soft_index)

        return {
            "score": eval_res.score,
            "relevance": eval_res.relevance,
            "technical_depth": eval_res.technical_depth,
            "clarity": eval_res.clarity,
            "completeness": eval_res.completeness,
            "strengths": eval_res.strengths,
            "improvements": eval_res.improvements,
            "evaluation": eval_res.evaluation,
            "next_question": next_question,
            "next_phase": next_phase,
            "is_followup": is_followup
        }
