from app.imports.parsers.base import BaseStatementParser
from app.imports.parsers.csv_parser import CSVStatementParser
from app.imports.parsers.xlsx_parser import XLSXStatementParser
from app.imports.parsers.pdf_parser import PDFStatementParser
from app.imports.exceptions import ParseError


def get_parser_for_file_type(file_type: str) -> BaseStatementParser:
    ft = file_type.strip().upper()
    if ft == "CSV":
        return CSVStatementParser()
    elif ft in ("XLSX", "XLS"):
        return XLSXStatementParser()
    elif ft == "PDF":
        return PDFStatementParser()
    else:
        raise ParseError(f"Unsupported statement format '{file_type}'. Supported formats: CSV, XLSX, PDF.")


__all__ = [
    "BaseStatementParser",
    "CSVStatementParser",
    "XLSXStatementParser",
    "PDFStatementParser",
    "get_parser_for_file_type",
]
