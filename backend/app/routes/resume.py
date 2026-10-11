from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.models.schemas import ResumeUploadResponse
from app.services.resume_parser import ResumeParser
from app.services.resume_service import clean_resume_text

router = APIRouter()

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """
    Accepts a PDF resume, extracts the text, cleans it, and returns it.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    # Read the file to check size
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
        raw_text, page_count = ResumeParser.extract_text_from_pdf_bytes(file_bytes)
        
        if not raw_text:
            raise ValueError("No extractable text found in the PDF.")
            
        cleaned_text = clean_resume_text(raw_text)
        
        return ResumeUploadResponse(
            success=True,
            filename=file.filename,
            page_count=page_count,
            text=cleaned_text,
            error=None
        )
    except Exception as e:
        return ResumeUploadResponse(
            success=False,
            error=str(e)
        )
