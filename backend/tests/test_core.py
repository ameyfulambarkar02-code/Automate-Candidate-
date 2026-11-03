from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.document_generator import generate_document
from app.services.google_forms_service import extract_form_id
from app.services.translator import translate_field


def test_extract_google_form_id_from_edit_url():
    assert extract_form_id("https://docs.google.com/forms/d/Abc_123/edit") == "Abc_123"
    assert extract_form_id("https://docs.google.com/forms/u/2/d/Abc_123/viewform") == "Abc_123"


def test_rejects_non_google_form_url():
    try:
        extract_form_id("https://example.com/forms/d/Abc_123")
    except ValueError as exc:
        assert "valid Google Forms URL" in str(exc)
    else:
        raise AssertionError("Invalid form URL was accepted")


def test_translation_preserves_numbers_and_education_abbreviations():
    def fake_translate(value: str) -> str:
        return value.replace("Rahul", "राहुल").replace("Patil", "पाटील")

    translated = translate_field("education", "Rahul Patil 82% B.A.M.S. 2025", fake_translate)
    assert translated == "राहुल पाटील 82% B.A.M.S. 2025"
    assert translate_field("mobile_number", "9876543210", fake_translate) == "9876543210"


def test_mock_translation_has_sample_marathi_mapping():
    assert translate_field("candidate_name", "Rahul Patil") == "राहुल पाटील"
    assert translate_field("birth_place", "Pune") == "पुणे"


def test_document_generation_replaces_split_paragraph_and_table_placeholders(tmp_path):
    template = tmp_path / "template.docx"
    output = tmp_path / "candidate.docx"
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("Candidate: {{CANDIDATE_")
    paragraph.add_run("NAME}}")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "{{MOBILE_NUMBER}}"

    image = Image.new("RGB", (20, 40), color="blue")
    photo_buffer = BytesIO()
    image.save(photo_buffer, format="PNG")
    document.add_paragraph("Photo: {{PHOTO}}")
    document.save(template)

    generate_document(
        template,
        output,
        {"candidate_name": "राहुल पाटील", "mobile_number": "9876543210"},
        photo_buffer.getvalue(),
    )
    generated = Document(output)
    assert "Candidate: राहुल पाटील" == "".join(run.text for run in generated.paragraphs[0].runs)
    assert generated.tables[0].cell(0, 0).text == "9876543210"
    assert len(generated.inline_shapes) == 1
    shape = generated.inline_shapes[0]
    assert round(shape.height / shape.width, 2) == 2.0


def test_health_and_admin_authentication():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/dashboard/stats").status_code == 401
        assert client.get("/api/auth/google/callback?state=not-signed").status_code == 400
