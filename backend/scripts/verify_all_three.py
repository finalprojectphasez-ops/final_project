import urllib.request
import json
import io

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("TEST 1: Resume PDF Extraction (/api/resume/upload)")
print("=" * 60)

minimal_pdf = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 55 >> stream
BT /F1 12 Tf 72 712 Td (John Doe: React, FastAPI, Docker Developer) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000350 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
424
%%EOF"""

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="sample_resume.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
).encode("utf-8") + minimal_pdf + f"\r\n--{boundary}--\r\n".encode("utf-8")

req1 = urllib.request.Request(
    f"{BASE_URL}/api/resume/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
)

resume_text = ""
try:
    with urllib.request.urlopen(req1) as resp:
        res1 = json.loads(resp.read().decode("utf-8"))
        print("Success:", res1.get("success"))
        print("Filename:", res1.get("filename"))
        print("Extracted Text:", res1.get("text"))
        resume_text = res1.get("text")
except Exception as e:
    print("Upload error:", e)

if not resume_text:
    resume_text = "John Doe: Senior Full Stack Engineer with 5 years experience in React, FastAPI, Docker, and PostgreSQL caching."

print("\n" + "=" * 60)
print("TEST 2: Job Role Question Generation (/api/interview/generate-question)")
print("=" * 60)

req2 = urllib.request.Request(
    f"{BASE_URL}/api/interview/generate-question",
    data=json.dumps({
        "resume_text": resume_text,
        "job_role": "Full Stack Engineer",
        "difficulty": "Mid"
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

first_question = ""
try:
    with urllib.request.urlopen(req2) as resp:
        res2 = json.loads(resp.read().decode("utf-8"))
        first_question = res2.get("question")
        print("Question:", first_question)
        print("Topic:", res2.get("topic"))
        print("Source:", res2.get("source"))
except Exception as e:
    print("Question error:", e)

print("\n" + "=" * 60)
print("TEST 3: Dynamic Follow-Up Question (/api/interview/evaluate-answer)")
print("=" * 60)

req3 = urllib.request.Request(
    f"{BASE_URL}/api/interview/evaluate-answer",
    data=json.dumps({
        "resume_text": resume_text,
        "job_role": "Full Stack Engineer",
        "question": first_question or "How did you use Docker with FastAPI?",
        "answer": "I used Docker to containerize my backend service."
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req3) as resp:
        res3 = json.loads(resp.read().decode("utf-8"))
        print("Candidate Score:", res3.get("score"))
        print("Technical Depth:", res3.get("technical_depth"))
        print("Follow-up Needed?:", res3.get("follow_up_needed"))
        print("Dynamic Follow-Up Question:", res3.get("follow_up_question"))
except Exception as e:
    print("Followup error:", e)

print("=" * 60)
