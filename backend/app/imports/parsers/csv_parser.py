import csv
import io
from typing import List, Dict, Any, Tuple
from app.imports.parsers.base import BaseStatementParser
from app.imports.exceptions import ParseError


class CSVStatementParser(BaseStatementParser):
    """
    Robust CSV parser with encoding autodetection, delimiter sniffing,
    BOM handling, and empty row stripping.
    """

    def parse_bytes(
        self, file_bytes: bytes, filename: str
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        if not file_bytes:
            raise ParseError(f"Uploaded CSV file '{filename}' is empty.")

        # Decode with fallback encodings
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text = file_bytes.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            raise ParseError(f"Unable to decode CSV file '{filename}'. Please ensure it is saved in UTF-8 format.")

        # Strip null bytes if present
        text = text.replace("\x00", "")

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise ParseError(f"CSV file '{filename}' contains no readable lines.")

        # Detect delimiter from sample
        sample = "\n".join(lines[:10])
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",;\t|")
            delimiter = dialect.delimiter
        except Exception:
            # Fallback heuristic: count commas vs tabs vs semicolons
            c_cnt = sample.count(",")
            s_cnt = sample.count(";")
            t_cnt = sample.count("\t")
            if s_cnt > c_cnt and s_cnt > t_cnt:
                delimiter = ";"
            elif t_cnt > c_cnt and t_cnt > s_cnt:
                delimiter = "\t"
            else:
                delimiter = ","

        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        raw_rows = list(reader)

        # Find header row (first non-empty row)
        header_idx = -1
        headers: List[str] = []
        for idx, row in enumerate(raw_rows):
            cleaned = [c.strip() for c in row if c and c.strip()]
            if cleaned:
                header_idx = idx
                headers = [c.strip() for c in row]
                break

        if header_idx == -1 or not headers:
            raise ParseError(f"CSV file '{filename}' does not contain a header row.")

        # Deduplicate and sanitize headers
        sanitized_headers = []
        seen = {}
        for h in headers:
            clean_h = h.strip()
            if not clean_h:
                clean_h = "Unnamed"
            if clean_h in seen:
                seen[clean_h] += 1
                sanitized_headers.append(f"{clean_h}_{seen[clean_h]}")
            else:
                seen[clean_h] = 1
                sanitized_headers.append(clean_h)

        data_rows: List[Dict[str, Any]] = []
        for line_num, row in enumerate(raw_rows[header_idx + 1 :], start=header_idx + 2):
            if not row or not any(str(c).strip() for c in row):
                continue  # skip completely blank rows

            row_dict: Dict[str, Any] = {"__row_number__": line_num}
            for col_idx, col_name in enumerate(sanitized_headers):
                val = row[col_idx].strip() if col_idx < len(row) else ""
                row_dict[col_name] = val

            data_rows.append(row_dict)

        if not data_rows:
            raise ParseError(f"CSV file '{filename}' has headers but no data rows.")

        return sanitized_headers, data_rows
