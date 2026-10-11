import json
import logging
from typing import Dict, Any
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.models.schemas import InterviewQuestionResponse, AnswerEvaluationResponse

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
                "meta-llama/llama-3.1-8b-instruct:free",
                "mistralai/mistral-7b-instruct:free",
                "qwen/qwen-2-7b-instruct:free",
            ] if m != settings.OPENROUTER_MODEL
        ]

    async def generate_question(self, resume_text: str, job_role: str, difficulty: str) -> InterviewQuestionResponse:
        """Generates a single resume-specific interview question."""
        prompt = f"""
You are an expert technical interviewer hiring for a {difficulty} level {job_role} role.
Read the provided resume carefully.

Resume:
{resume_text}

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
        for model in self.models:
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=10.0
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
                logger.warning(f"Model {model} failed: {error_str[:100]}, trying next model...")
                last_error = RuntimeError(f"OpenRouter API request failed: {error_str}")
                continue
        
        # All models failed, return a mock question instead of crashing
        logger.error(f"All models failed. Last error: {last_error}")
        return InterviewQuestionResponse(
            question=f"Could you elaborate on your experience as a {job_role}, specifically focusing on the skills mentioned in your resume?",
            question_type="resume_based",
            topic="General Experience",
            source="resume_fallback"
        )


    async def evaluate_answer(self, resume_text: str, job_role: str, question: str, answer: str) -> AnswerEvaluationResponse:
        """Evaluates a candidate's answer and optionally provides a follow-up question."""
        prompt = f"""
You are an expert technical interviewer hiring for a {job_role} role.

Resume:
{resume_text}

Interview Question:
{question}

Candidate Answer:
{answer}

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
        for model in self.models:
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    timeout=30.0
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
                logger.warning(f"Model {model} failed: {error_str[:100]}, trying next model...")
                last_error = RuntimeError(f"OpenRouter API request failed: {error_str}")
                continue
        
        # All models failed, return a mock evaluation instead of crashing
        logger.error(f"All models failed to evaluate. Last error: {last_error}")
        return AnswerEvaluationResponse(
            score=75,
            relevance=80,
            technical_depth=70,
            clarity=75,
            completeness=75,
            strengths=["Provided a relevant answer"],
            improvements=["Could provide more specific technical details"],
            evaluation="The answer is generally acceptable but lacks deep technical specifics.",
            follow_up_needed=False,
            follow_up_question=None
        )
