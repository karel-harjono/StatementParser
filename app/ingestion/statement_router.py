import logging

from app.ingestion.csv_parser import (
    AmexCsvParser,
    GenericCsvParser,
)
from app.ingestion.pdf_parser import RbcPdfParser

logger = logging.getLogger(__name__)


class StatementRouter:
    """
    Tries each registered parser in order; uses the first one that claims
    it can handle the file.  More specific parsers must be registered before
    generic fallbacks.

    Default order:
        AmexCsvParser   – specific CSV columns (Date, Date Processed, Description, Amount)
        RbcPdfParser    – any .pdf (RBC Visa statement format)
        GenericCsvParser – any .csv (last resort)
    """

    def __init__(self, parsers: list | None = None):
        self.parsers = parsers or [
            AmexCsvParser(),  # Amex comes as CSV – must be before generic CSV fallback
            RbcPdfParser(),  # RBC comes as PDF
            GenericCsvParser(),  # generic CSV last – most permissive
        ]

    def parse(self, file_path: str) -> list[dict]:
        for parser in self.parsers:
            if parser.can_handle(file_path):
                logger.info(
                    "StatementRouter: using %s for %s",
                    parser.__class__.__name__,
                    file_path,
                )
                return parser.parse(file_path)
        raise ValueError(f"No parser found for {file_path!r}")
