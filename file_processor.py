"""
File Processor - Document Ingestion Pipeline
Handles PDF, CSV, XLSX, TXT extraction and intelligent chunking
"""

import os
import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class FileProcessor:
    """
    Document ingestion and processing engine.
    Extracts text from multiple file formats and prepares for AI context injection.
    """

    def process(self, filepath: str) -> str:
        """Route file to appropriate processor based on extension"""
        ext = filepath.rsplit(".", 1)[-1].lower()

        processors = {
            "pdf": self._process_pdf,
            "csv": self._process_csv,
            "xlsx": self._process_excel,
            "xls": self._process_excel,
            "txt": self._process_txt,
        }

        processor = processors.get(ext)
        if not processor:
            raise ValueError(f"Unsupported file type: .{ext}")

        logger.info(f"Processing {ext.upper()} file: {os.path.basename(filepath)}")
        return processor(filepath)

    # ── PDF Processor ──────────────────────────────────────────────────────
    def _process_pdf(self, filepath: str) -> str:
        """
        Extract text from PDF using PyPDF2.
        Handles multi-page documents with progressive extraction.
        """
        try:
            import PyPDF2
        except ImportError:
            raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")

        text_parts = []

        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)
            logger.info(f"PDF has {total_pages} pages")

            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(f"[Page {page_num + 1}]\n{page_text.strip()}")
                except Exception as e:
                    logger.warning(f"Could not extract page {page_num + 1}: {e}")

        if not text_parts:
            raise ValueError("No readable text found in PDF. The file may be image-based.")

        return "\n\n".join(text_parts)

    # ── CSV Processor ──────────────────────────────────────────────────────
    def _process_csv(self, filepath: str) -> str:
        """
        Convert CSV data to natural language format.
        Example: "Product: iPhone | Price: ₹80,000 | Stock: Available"
        This format is much easier for AI to understand than raw CSV.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas not installed. Run: pip install pandas")

        df = pd.read_csv(filepath)
        df = df.fillna("N/A")

        # Convert column names: clean whitespace and special chars
        df.columns = [col.strip() for col in df.columns]

        total_rows = len(df)
        logger.info(f"CSV has {total_rows} rows, {len(df.columns)} columns")

        # Build header context
        text_parts = [
            f"Dataset Summary: {total_rows} records",
            f"Fields: {', '.join(df.columns.tolist())}",
            "---"
        ]

        # Convert each row to readable text (limit to 300 rows max for context)
        max_rows = min(total_rows, 300)
        for idx, row in df.head(max_rows).iterrows():
            row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
            text_parts.append(f"Record {idx + 1}: {row_text}")

        if total_rows > max_rows:
            text_parts.append(f"[Note: Showing first {max_rows} of {total_rows} records]")

        return "\n".join(text_parts)

    # ── Excel Processor ────────────────────────────────────────────────────
    def _process_excel(self, filepath: str) -> str:
        """
        Process Excel files with multiple sheets support.
        Converts each sheet to natural language format.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas not installed. Run: pip install pandas openpyxl")

        xl = pd.ExcelFile(filepath)
        all_text = []

        for sheet_name in xl.sheet_names:
            df = pd.read_excel(filepath, sheet_name=sheet_name).fillna("N/A")
            sheet_text = [f"\n=== Sheet: {sheet_name} ==="]
            sheet_text.append(f"Rows: {len(df)} | Columns: {', '.join(str(c) for c in df.columns)}")

            max_rows = min(len(df), 200)
            for idx, row in df.head(max_rows).iterrows():
                row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
                sheet_text.append(f"Row {idx + 1}: {row_text}")

            all_text.append("\n".join(sheet_text))

        return "\n\n".join(all_text)

    # ── TXT Processor ──────────────────────────────────────────────────────
    def _process_txt(self, filepath: str) -> str:
        """Read plain text files with encoding detection"""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for enc in encodings:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        raise ValueError("Could not decode text file with any supported encoding")

    # ── Text Chunking ──────────────────────────────────────────────────────
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better context coverage.

        Why overlap? When a sentence spans a chunk boundary,
        overlap ensures full context is preserved.

        Args:
            text: Full extracted text
            chunk_size: Target characters per chunk
            overlap: Characters to repeat between chunks

        Returns:
            List of text chunks
        """
        # Clean the text first
        text = self._clean_text(text)

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at a sentence boundary
            if end < len(text):
                # Find last ". " or "\n" within the chunk
                last_sentence = max(
                    text.rfind(". ", start, end),
                    text.rfind("\n", start, end)
                )
                if last_sentence > start + (chunk_size // 2):
                    end = last_sentence + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap  # Apply overlap for continuity

        return chunks

    def build_context_string(self, chunks: List[str], source_name: str) -> str:
        """
        Package chunks into a structured context string for the AI.
        Includes source attribution.
        """
        header = f"=== Document: {source_name} ===\n"
        body = "\n\n".join(chunks)
        return f"{header}{body}"

    def _clean_text(self, text: str) -> str:
        """
        Remove noise from extracted text:
        - Multiple blank lines → single line
        - Control characters
        - Excessive whitespace
        """
        text = re.sub(r'\r\n', '\n', text)            # Normalize line endings
        text = re.sub(r'\n{3,}', '\n\n', text)        # Collapse blank lines
        text = re.sub(r'[ \t]{2,}', ' ', text)        # Collapse spaces
        text = re.sub(r'[^\x20-\x7E\n\u00A0-\uFFFF]', '', text)  # Remove control chars
        return text.strip()
