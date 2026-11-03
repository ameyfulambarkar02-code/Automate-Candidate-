from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Cm
from docx.text.paragraph import Paragraph

PHOTO_TOKEN = "{{PHOTO}}"


def _replace_in_paragraph(paragraph: Paragraph, values: dict[str, str], photo: bytes | None) -> None:
    runs = paragraph.runs
    if not runs:
        return
    full_text = "".join(run.text for run in runs)
    tokens = {f"{{{{{key.upper()}}}}}": value for key, value in values.items()}
    if photo and PHOTO_TOKEN in full_text:
        tokens[PHOTO_TOKEN] = ""
    matches = []
    for token, value in tokens.items():
        start = 0
        while (index := full_text.find(token, start)) >= 0:
            matches.append((index, index + len(token), value))
            start = index + len(token)
    if not matches:
        return
    matches.sort(reverse=True)
    offsets = []
    cursor = 0
    for run in runs:
        offsets.append((cursor, cursor + len(run.text)))
        cursor += len(run.text)
    for start, end, value in matches:
        start_run = next((i for i, (a, b) in enumerate(offsets) if a <= start < b), len(runs) - 1)
        end_run = next((i for i, (a, b) in enumerate(offsets) if a < end <= b), len(runs) - 1)
        start_local = start - offsets[start_run][0]
        end_local = end - offsets[end_run][0]
        if start_run == end_run:
            runs[start_run].text = runs[start_run].text[:start_local] + value + runs[start_run].text[end_local:]
        else:
            runs[start_run].text = runs[start_run].text[:start_local] + value
            for index in range(start_run + 1, end_run):
                runs[index].text = ""
            runs[end_run].text = runs[end_run].text[end_local:]
        if photo and full_text[start:end] == PHOTO_TOKEN:
            runs[start_run].add_picture(BytesIO(photo), width=Cm(4))


def _paragraphs_and_tables(container):
    for paragraph in container.paragraphs:
        yield paragraph
    for table in container.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from _paragraphs_and_tables(cell)


def generate_document(
    template_path: str | Path,
    output_path: str | Path,
    values: dict[str, str],
    photo: bytes | None = None,
) -> Path:
    template = Path(template_path)
    if not template.exists():
        raise FileNotFoundError(f"DOCX template not found: {template}")
    document = Document(template)
    containers = [document]
    for section in document.sections:
        containers.extend([section.header, section.footer])
    visited = set()
    for container in containers:
        for paragraph in _paragraphs_and_tables(container):
            if id(paragraph) not in visited:
                visited.add(id(paragraph))
                _replace_in_paragraph(paragraph, values, photo)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    return output
