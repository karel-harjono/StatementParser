"""
OCR fallback for scanned/image-based PDFs.
Not implemented in the MVP – raises NotImplementedError if called.
Install 'pytesseract' and 'pdf2image' (+ system Tesseract) to enable.
"""

import logging

logger = logging.getLogger(__name__)


class OcrFallbackParser:
    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def parse(self, file_path: str) -> list[dict]:
        raise NotImplementedError(
            "OCR fallback is not implemented. "
            "Install pytesseract + pdf2image and implement this parser."
        )
