import io

TEXT_EXTS = {
    ".txt",
    ".md",
    ".markdown",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".json",
    ".csv",
    ".xml",
    ".html",
    ".css",
    ".yml",
    ".yaml",
    ".sh",
    ".sql",
    ".ini",
    ".conf",
    ".java",
    ".c",
    ".cpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
}

IMAGE_PREFIXES = ("image/",)

DOC_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/msword": "docx",
    "application/vnd.ms-excel": "xlsx",
}


def detect_kind(filename: str, content_type: str) -> str:
    if content_type.startswith(IMAGE_PREFIXES):
        return "image"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in TEXT_EXTS or content_type.startswith("text/"):
        return "text"
    return "doc"


def extract_text(filename: str, content_type: str, data: bytes) -> str:
    kind = detect_kind(filename, content_type)
    if kind == "text":
        return data.decode("utf-8", errors="ignore")
    if kind == "image":
        return ""

    doc_type = DOC_TYPES.get(content_type)
    if doc_type == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if doc_type == "docx":
        import docx

        document = docx.Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append("\t".join(cell.text for cell in row.cells))
        return "\n".join(parts)
    if doc_type == "xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        lines = []
        for sheet in wb.worksheets:
            lines.append(f"[{sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    lines.append("\t".join(cells))
        wb.close()
        return "\n".join(lines)
    return ""
