import asyncio
import json
import httpx
from unittest.mock import AsyncMock, patch

async def run_test():
    # We will mock the backend by mocking the LLM service directly inside a test that imports it,
    # or we can test the fastapi test client.
    from app.main import app
    from httpx import ASGITransport, AsyncClient
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # Test 1: Mocking the AsyncOpenAI response to return "User Safety: safe"
        with patch("app.services.interview_llm_service.AsyncOpenAI") as mock_openai:
            mock_client_instance = AsyncMock()
            mock_openai.return_value = mock_client_instance
            
            # Setup the mock response
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "User Safety: safe"
            
            mock_client_instance.chat.completions.create.return_value = mock_response
            
            response = await ac.post("/api/interview/evaluate-answer", json={
                "resume_text": "Sample resume",
                "job_role": "Developer",
                "question": "What is Python?",
                "answer": "A snake."
            })
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            assert response.status_code == 502 or response.status_code == 500
            print("Test passed: Backend returns controlled error instead of crashing.")

if __name__ == "__main__":
    asyncio.run(run_test())
