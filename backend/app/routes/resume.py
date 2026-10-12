from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.models.schemas import ResumeUploadResponse, ProfessionalProfile
from app.services.resume_parser import ResumeParser
from app.services.resume_service import clean_resume_text
from app.services.local_interview_model import local_interview_model

router = APIRouter()

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".doc", ".txt", ".text")


class ExtractTextRequest(BaseModel):
    resume_text: str


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts PDF, DOCX, or TXT resume, extracts and cleans text locally,
    extracts the validated 15-field professional profile, and returns it.
    Scanned PDFs without text layer return a clear extraction error.
    """
    lower_filename = file.filename.lower()
    if not any(lower_filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, and TXT files are supported."
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 5MB limit."
        )

    try:
        raw_text, page_count = ResumeParser.parse_file(file.filename, file_bytes)
        if not raw_text or not raw_text.strip():
            raise ValueError("No extractable text found in the uploaded resume.")

        cleaned_text = clean_resume_text(raw_text)
        # Extract 15-field professional profile using shared local model
        profile = local_interview_model.extract_resume_profile(cleaned_text)

        return ResumeUploadResponse(
            success=True,
            filename=file.filename,
            page_count=page_count,
            text=cleaned_text,
            profile=profile,
            error=None
        )
    except Exception as e:
        return ResumeUploadResponse(
            success=False,
            filename=file.filename,
            error=str(e)
        )


@router.post("/extract-text")
async def extract_resume_from_text(req: ExtractTextRequest):
    """
    Extracts the 15-field professional profile directly from raw resume text.
    """
    if not req.resume_text or not req.resume_text.strip():
        return {"success": False, "error": "Resume text is empty.", "profile": None}

    cleaned = clean_resume_text(req.resume_text)
    profile = local_interview_model.extract_resume_profile(cleaned)
    return {
        "success": True,
        "text": cleaned,
        "profile": profile.model_dump() if profile else None,
        "error": None
    }
