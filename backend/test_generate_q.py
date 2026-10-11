import asyncio
import httpx

async def run_test():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as ac:
        response = await ac.post("/api/interview/generate-question", json={
            "resume_text": "Software engineer with Python, React and FastAPI experience.",
            "job_role": "Full Stack Engineer",
            "difficulty": "Easy"
        })
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(run_test())
