import logging

from app.ingestion.csv_parser import ChaseCsvParser, BoACsvParser, GenericCsvParser
from app.ingestion.pdf_parser import AmexPdfParser

logger = logging.getLogger(__name__)


class StatementRouter:
    """
    Tries each registered parser in order; uses the first one that claims
    it can handle the file.  More specific parsers should be registered
    before generic fallbacks.
    """

    def __init__(self, parsers: list | None = None):
        self.parsers = parsers or [
            ChaseCsvParser(),
            BoACsvParser(),
            AmexPdfParser(),
            GenericCsvParser(),   # generic CSV last – most permissive
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
