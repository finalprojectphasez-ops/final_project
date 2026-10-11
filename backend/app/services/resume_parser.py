import io
import PyPDF2

class ResumeParser:
    @staticmethod
    def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> tuple[str, int]:
        """
        Parses a PDF file buffer and returns the raw text content and page count.
        """
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            page_count = len(reader.pages)
            for i in range(page_count):
                page = reader.pages[i]
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text.strip(), page_count
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {str(e)}")
