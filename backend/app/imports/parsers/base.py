from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple


class BaseStatementParser(ABC):
    """Abstract base class for all file parsers (CSV, XLSX, PDF)."""

    @abstractmethod
    def parse_bytes(
        self, file_bytes: bytes, filename: str
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Parses raw bytes into:
        1. List of column headers (strings)
        2. List of raw row dicts, with each dict containing '__row_number__' and column values
        """
        pass
