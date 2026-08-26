import io
try:
    import PyPDF2
except ImportError:
    pass

class ResumeParser:
    @staticmethod
    def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
        """
        Parses a PDF file buffer (e.g. downloaded from Supabase Storage)
        and returns the raw text content for the OpenAI Engine to dissect.
        """
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for i in range(len(reader.pages)):
                page = reader.pages[i]
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return "Parsing Failed. Proceed with standard role questions."

# Example format usage:
# ResumeParser.extract_text_from_pdf_bytes(file_bytes)
