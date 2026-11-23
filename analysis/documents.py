"""Turn an uploaded resume file (.txt, .docx or .pdf) into plain text.

Nothing is saved: the file only lives in memory (or Django's temp file) for the request.
"""
import os
import re

from docx import Document
from pypdf import PdfReader

from .exceptions import UnreadableFile

MAX_PDF_PAGES = 20      # a resume is 1-3 pages; this caps the work a hostile PDF can cause

# The first bytes of each format. A .docx is a zip file, so it starts with "PK".
_SIGNATURES = {".docx": b"PK", ".pdf": b"%PDF"}


def extract_text(file) -> str:
    ext = os.path.splitext(file.name)[1].lower()

    # 1. The name comes from the client: check the file really looks like what it claims to be
    signature = _SIGNATURES.get(ext)
    if signature is not None:
        start = file.read(len(signature))
        file.seek(0)                                  # rewind, or the parser would get a cut-off file
        if start != signature:
            raise UnreadableFile(f"That file isn't a valid {ext} file.")

    # 2. Parse it, once, in the way that matches its type
    try:
        if ext == ".txt":
            text = _read_txt(file)
        elif ext == ".docx":
            text = _read_docx(file)
        elif ext == ".pdf":
            text = _read_pdf(file)
        else:
            raise UnreadableFile(f"Unsupported file type: {ext}")
    except UnreadableFile:
        raise                                         # our own, clearer message: pass it on unchanged
    except Exception as exc:                          # corrupt file, wrong encoding, broken zip...
        raise UnreadableFile("Couldn't read that file. It may be damaged; try saving it again.") from exc

    # 3. Only now can we tell whether there are real words in it
    text = _tidy(text)
    if not text:
        if ext == ".pdf":
            raise UnreadableFile(
                "No text found in that PDF. It may be a scanned image; paste your resume text instead."
            )
        raise UnreadableFile("That file has no text in it.")
    return text


def _read_txt(file) -> str:
    try:
        return file.read().decode("utf-8-sig")        # utf-8-sig also drops the BOM some editors add
    except UnicodeDecodeError as exc:
        raise UnreadableFile("That .txt file isn't UTF-8 text. Save it as UTF-8 and try again.") from exc


def _read_docx(file) -> str:
    doc = Document(file)
    lines = [p.text for p in doc.paragraphs]
    # Many resume templates put skills or dates in tables, which aren't in doc.paragraphs
    for table in doc.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                if cell.text not in cells:            # merged cells repeat the same text
                    cells.append(cell.text)
            lines.append(" | ".join(c for c in cells if c.strip()))
    return "\n".join(lines)


def _read_pdf(file) -> str:
    reader = PdfReader(file)
    if reader.is_encrypted:
        raise UnreadableFile("That PDF is password-protected. Remove the password and try again.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise UnreadableFile(f"That PDF has more than {MAX_PDF_PAGES} pages. Upload just your resume.")
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _tidy(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)            # at most one blank line in a row
    return text.strip()
