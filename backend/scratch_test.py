import requests
import os
import json
from fpdf import FPDF

API_BASE = "http://127.0.0.1:8000/api"

def create_dummy_pdf(filename: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="John Doe", ln=True)
    pdf.cell(200, 10, txt="Software Engineer", ln=True)
    pdf.cell(200, 10, txt="Experience: Built an E-commerce site using React and Node.js.", ln=True)
    pdf.cell(200, 10, txt="Skills: Python, JavaScript, React, FastAPI.", ln=True)
    pdf.output(filename)

def test_flow():
    print("--- 1. Testing PDF Upload ---")
    pdf_path = "dummy_resume.pdf"
    create_dummy_pdf(pdf_path)
    
    with open(pdf_path, "rb") as f:
        files = {"file": ("dummy_resume.pdf", f, "application/pdf")}
        res = requests.post(f"{API_BASE}/resume/upload", files=files)
        
    os.remove(pdf_path)
    
    if res.status_code != 200:
        print("Upload Failed!", res.status_code, res.text)
        return
        
    upload_data = res.json()
    print(json.dumps(upload_data, indent=2))
    
    if not upload_data.get("success"):
        print("Upload reported failure.")
        return
        
    resume_text = upload_data.get("text")
    print(f"\nExtracted Text length: {len(resume_text)}")

    print("\n--- 2. Testing OpenRouter generate-question ---")
    q_payload = {
        "resume_text": resume_text,
        "job_role": "Full Stack Developer",
        "difficulty": "Medium"
    }
    res_q = requests.post(f"{API_BASE}/interview/generate-question", json=q_payload)
    if res_q.status_code != 200:
        print("Generate question failed!", res_q.status_code, res_q.text)
        return
        
    q_data = res_q.json()
    print(json.dumps(q_data, indent=2))
    question = q_data.get("question")
    
    print("\n--- 3. Testing OpenRouter evaluate-answer ---")
    eval_payload = {
        "resume_text": resume_text,
        "job_role": "Full Stack Developer",
        "question": question,
        "answer": "I used React and Node.js for the E-commerce site. I managed state with React Context API."
    }
    res_eval = requests.post(f"{API_BASE}/interview/evaluate-answer", json=eval_payload)
    if res_eval.status_code != 200:
        print("Evaluate answer failed!", res_eval.status_code, res_eval.text)
        return
        
    eval_data = res_eval.json()
    print(json.dumps(eval_data, indent=2))

if __name__ == "__main__":
    test_flow()
