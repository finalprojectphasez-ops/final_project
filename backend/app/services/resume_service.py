import re

def clean_resume_text(raw_text: str) -> str:
    """
    Cleans raw text extracted from a PDF resume.
    Removes obvious extraction artifacts like excessive whitespace,
    repeated blank lines, and unnecessary control characters,
    while preserving the original meaning and structure.
    """
    if not raw_text:
        return ""

    # Remove null bytes and other non-printable control characters (except newlines and tabs)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', raw_text)

    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Replace 3 or more newlines with exactly 2 newlines (paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip leading/trailing whitespace on each line
    lines = [line.strip() for line in text.split('\n')]
    
    # Rejoin lines
    text = '\n'.join(lines)
    
    # Final strip
    return text.strip()
