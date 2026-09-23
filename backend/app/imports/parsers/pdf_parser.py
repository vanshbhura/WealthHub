import io
import re
from typing import List, Dict, Any, Tuple
import pypdf
from app.imports.parsers.base import BaseStatementParser
from app.imports.exceptions import ParseError


class PDFStatementParser(BaseStatementParser):
    """
    Text-based PDF parser extracting structured table rows from digital statements.
    Enforces a strict zero-fabrication policy: if text extraction is low confidence
    or lacks structured tabular data, it raises a safe, descriptive ParseError.
    """

    UNRELIABLE_MSG = (
        "Unable to reliably extract structured transaction data from this PDF. "
        "Please use CSV/XLSX or a supported statement format."
    )

    def parse_bytes(
        self, file_bytes: bytes, filename: str
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        if not file_bytes:
            raise ParseError(f"Uploaded PDF file '{filename}' is empty.")

        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except Exception as e:
            raise ParseError(f"Failed to open PDF file '{filename}': {str(e)}")

        if reader.is_encrypted:
            raise ParseError("The uploaded PDF is password-protected. Please upload an unencrypted statement or CSV/XLSX.")

        num_pages = len(reader.pages)
        if num_pages == 0:
            raise ParseError(self.UNRELIABLE_MSG)

        # Extract text across pages
        extracted_text = []
        for p_idx in range(min(num_pages, 50)):  # limit check to 50 pages for safety
            try:
                page_text = reader.pages[p_idx].extract_text()
                if page_text:
                    extracted_text.append(page_text)
            except Exception:
                continue

        full_text = "\n".join(extracted_text).strip()
        if not full_text or len(full_text) < 40:
            # Scanned / raster image PDF with no text layer
            raise ParseError(self.UNRELIABLE_MSG)

        # Look for table structures: lines with dates and numbers
        # Common line pattern: Date ... Description ... Amount or Quantity ... Price
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        # Heuristic to find potential table header
        header_candidates = [
            ["date", "description", "amount"],
            ["date", "particulars", "debit", "credit"],
            ["trade date", "symbol", "quantity", "price"],
            ["date", "symbol", "qty", "price", "amount"],
            ["transaction date", "type", "amount"],
            ["date", "action", "quantity", "price"],
        ]

        found_header: List[str] = []
        header_line_idx = -1

        for idx, line in enumerate(lines[:30]):
            lowered = line.lower()
            # Check if line matches common header words
            words = re.split(r"[\t,|]+|\s{2,}", line)
            words = [w.strip() for w in words if w.strip()]
            if len(words) >= 3:
                low_words = [w.lower() for w in words]
                for cand in header_candidates:
                    if sum(1 for c in cand if any(c in w for w in low_words)) >= 2:
                        found_header = words
                        header_line_idx = idx
                        break
            if found_header:
                break

        # Fallback: if no multi-space header found, check for CSV-like or pipe-separated lines
        if not found_header:
            for idx, line in enumerate(lines[:30]):
                if "," in line and len(line.split(",")) >= 3:
                    parts = [p.strip() for p in line.split(",") if p.strip()]
                    low_parts = [p.lower() for p in parts]
                    if any("date" in p for p in low_parts) and any("amount" in p or "qty" in p or "price" in p for p in low_parts):
                        found_header = parts
                        header_line_idx = idx
                        break

        if not found_header or header_line_idx == -1:
            raise ParseError(self.UNRELIABLE_MSG)

        sanitized_headers = []
        seen = {}
        for h in found_header:
            clean_h = h.strip()
            if clean_h in seen:
                seen[clean_h] += 1
                sanitized_headers.append(f"{clean_h}_{seen[clean_h]}")
            else:
                seen[clean_h] = 1
                sanitized_headers.append(clean_h)

        # Parse following rows
        data_rows: List[Dict[str, Any]] = []
        date_pattern = re.compile(r"^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}")

        for line_num, line in enumerate(lines[header_line_idx + 1:], start=header_line_idx + 2):
            # Split by 2+ spaces, tab, comma, or pipe
            parts = re.split(r"[\t,|]+|\s{2,}", line)
            parts = [p.strip() for p in parts if p.strip()]

            # Must start with a date or contain at least len(headers)-1 columns
            if not parts:
                continue

            first_col = parts[0]
            if not date_pattern.match(first_col) and len(parts) < len(sanitized_headers) - 1:
                continue  # likely footer or non-row text

            row_dict: Dict[str, Any] = {"__row_number__": line_num}
            for col_idx, col_name in enumerate(sanitized_headers):
                val = parts[col_idx] if col_idx < len(parts) else ""
                row_dict[col_name] = val

            data_rows.append(row_dict)

        if len(data_rows) == 0:
            raise ParseError(self.UNRELIABLE_MSG)

        return sanitized_headers, data_rows
