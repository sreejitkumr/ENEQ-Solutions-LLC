import io
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter


def _preserve_pdf_header(original_pdf: bytes, result_pdf: bytes) -> bytes:
    """Preserve the first two PDF header lines, including the binary marker."""
    if not original_pdf.startswith(b"%PDF-"):
        return result_pdf

    original_first_newline = original_pdf.find(b"\n", original_pdf.find(b"%PDF-"))
    if original_first_newline < 0:
        return result_pdf

    original_second_newline = original_pdf.find(b"\n", original_first_newline + 1)
    if original_second_newline < 0:
        return result_pdf

    result_first_newline = result_pdf.find(b"\n", result_pdf.find(b"%PDF-"))
    if result_first_newline < 0:
        return result_pdf

    result_second_newline = result_pdf.find(b"\n", result_first_newline + 1)
    if result_second_newline < 0:
        return result_pdf

    original_header = original_pdf[: original_second_newline + 1]
    result_header = result_pdf[: result_second_newline + 1]

    if len(original_header) != len(result_header):
        return result_pdf

    return original_header + result_pdf[result_second_newline + 1:]


def embed_attachments_in_pdf(pdf_bytes: bytes, attachments: list[dict], session_attachments: dict = None) -> bytes:
    """Embed attachment files inside a PDF so recipients can download them."""
    if not attachments:
        return pdf_bytes

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    attachments_added = 0
    for attachment in attachments:
        file_name = attachment.get("name")
        if not file_name:
            continue

        file_path = attachment.get("path")
        file_data = None

        if file_path and Path(file_path).exists():
            file_data = Path(file_path).read_bytes()
        elif session_attachments:
            file_id = attachment.get("file_id")
            if file_id and file_id in session_attachments:
                file_data = session_attachments[file_id].get("data")

        if file_data is None:
            continue

        writer.add_attachment(file_name, file_data)
        attachments_added += 1

    if attachments_added == 0:
        return pdf_bytes

    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    result_pdf = output_buffer.getvalue()

    return _preserve_pdf_header(pdf_bytes, result_pdf)
