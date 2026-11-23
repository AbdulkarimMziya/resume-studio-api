import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from docx import Document
from pypdf import PdfWriter

URL = "/api/extract-text/"


# ---- Helpers: build real files in memory, so the tests need no fixture files on disk ----

def make_docx(paragraphs=(), table=None) -> bytes:
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    if table:
        t = doc.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, value in enumerate(row):
                t.cell(r, c).text = value
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def make_pdf(lines) -> bytes:
    """A minimal one-page PDF with real (selectable) text, written by hand."""
    content = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(f"({line}) '" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return out


def make_blank_pdf(pages=1) -> bytes:
    """Pages with no text at all, like a scanned resume."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def upload(api_client, name, content: bytes, content_type="application/octet-stream"):
    file = SimpleUploadedFile(name, content, content_type=content_type)
    return api_client.post(URL, {"file": file}, format="multipart")


# ---- Happy paths ----

def test_txt_upload(api_client):
    response = upload(api_client, "cv.txt", b"Junior developer.\nPython, Django.", "text/plain")
    assert response.status_code == 200
    assert response.data == {"text": "Junior developer.\nPython, Django."}


def test_txt_with_bom(api_client):
    response = upload(api_client, "cv.txt", "﻿Junior developer.".encode("utf-8"), "text/plain")
    assert response.status_code == 200
    assert response.data["text"] == "Junior developer."


def test_docx_upload(api_client):
    content = make_docx(["Jane Doe", "Junior developer. Helped with testing."])
    response = upload(api_client, "CV.DOCX", content)          # extension check ignores case
    assert response.status_code == 200
    assert response.data["text"] == "Jane Doe\nJunior developer. Helped with testing."


def test_docx_table_text_is_included(api_client):
    content = make_docx(["Skills"], table=[["Python", "Django"], ["SQL", "Docker"]])
    response = upload(api_client, "cv.docx", content)
    assert response.status_code == 200
    assert "Python | Django" in response.data["text"]
    assert "SQL | Docker" in response.data["text"]


def test_pdf_upload(api_client):
    content = make_pdf(["Jane Doe", "Junior developer. Helped with testing."])
    response = upload(api_client, "cv.pdf", content, "application/pdf")
    assert response.status_code == 200
    assert "Jane Doe" in response.data["text"]
    assert "Helped with testing." in response.data["text"]


def test_extra_blank_lines_are_collapsed(api_client):
    response = upload(api_client, "cv.txt", b"Line one   \n\n\n\n\nLine two\n\n")
    assert response.status_code == 200
    assert response.data["text"] == "Line one\n\nLine two"


# ---- Rejected by the serializer: {"file": [...]} ----

def test_missing_file(api_client):
    response = api_client.post(URL, {}, format="multipart")
    assert response.status_code == 400
    assert "file" in response.data


def test_empty_file(api_client):
    response = upload(api_client, "cv.txt", b"")
    assert response.status_code == 400
    assert "file" in response.data


@pytest.mark.parametrize("name", ["cv.doc", "cv.rtf", "cv.png", "cv"])
def test_unsupported_extension(api_client, name):
    response = upload(api_client, name, b"some bytes")
    assert response.status_code == 400
    assert "file" in response.data


def test_file_over_2_mb(api_client):
    response = upload(api_client, "cv.txt", b"a" * (2 * 1024 * 1024 + 1))
    assert response.status_code == 400
    assert "file" in response.data


# ---- Passed the serializer but couldn't be read: {"detail": "..."} ----

def test_renamed_file_is_rejected(api_client):
    response = upload(api_client, "cv.pdf", b"This is really a text file")
    assert response.status_code == 400
    assert "detail" in response.data


def test_corrupt_docx(api_client):
    response = upload(api_client, "cv.docx", b"PK\x03\x04 not really a zip")
    assert response.status_code == 400
    assert "detail" in response.data


def test_corrupt_pdf(api_client):
    response = upload(api_client, "cv.pdf", b"%PDF-1.4 and then garbage")
    assert response.status_code == 400
    assert "detail" in response.data


def test_non_utf8_txt(api_client):
    response = upload(api_client, "cv.txt", "Résumé".encode("latin-1"))
    assert response.status_code == 400
    assert "UTF-8" in response.data["detail"]


def test_blank_docx(api_client):
    response = upload(api_client, "cv.docx", make_docx(["   ", ""]))
    assert response.status_code == 400
    assert "detail" in response.data


def test_pdf_without_text(api_client):
    response = upload(api_client, "cv.pdf", make_blank_pdf())
    assert response.status_code == 400
    assert "scanned" in response.data["detail"]


def test_pdf_with_too_many_pages(api_client):
    response = upload(api_client, "cv.pdf", make_blank_pdf(pages=21))
    assert response.status_code == 400
    assert "pages" in response.data["detail"]


def test_text_over_resume_limit(api_client):
    response = upload(api_client, "cv.txt", b"word " * 7_000)   # 35,000 characters
    assert response.status_code == 400
    assert "30,000" in response.data["detail"]


# ---- Method, media type and docs ----

def test_json_body_is_unsupported(api_client):
    response = api_client.post(URL, {"file": "cv.txt"}, format="json")
    assert response.status_code == 415


def test_get_is_not_allowed(api_client):
    response = api_client.get(URL)
    assert response.status_code == 405


def test_schema_lists_the_endpoint(api_client):
    response = api_client.get("/api/schema/")
    assert response.status_code == 200
    assert URL in response.data["paths"]
