import os
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List, Dict

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class InterviewContext(BaseModel):
    role: str
    difficulty: str
    resume_text: str
    
class LLMEngine:
    def __init__(self, context: InterviewContext):
        self.context = context
        self.history = [
            {"role": "system", "content": self._build_system_prompt()}
        ]
        
    def _build_system_prompt(self) -> str:
        return f"""
You are a highly experienced hiring manager conducting a technical and behavioral interview.
Role: {self.context.role}
Difficulty: {self.context.difficulty}
Resume Snippet: {self.context.resume_text[:2000]}

Rules:
1. Ask one targeted question at a time. Do not send multiple questions.
2. Based on the resume, challenge the user on their claims.
3. Keep it conversational but strictly professional.
"""

    async def get_next_question(self, user_answer: str = None) -> str:
        if user_answer:
            self.history.append({"role": "user", "content": user_answer})
            
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=self.history,
            temperature=0.7,
            max_tokens=150
        )
        
        reply = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": reply})
        return reply

    async def generate_evaluation(self, full_transcript: List[Dict]) -> dict:
        # Final scoring logic utilizing OpenAI JSON mode
        pass
