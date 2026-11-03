import re

from app.config import get_settings

NUMBER_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]*\d|\d)(?!\w)")
ABBREVIATION_PATTERN = re.compile(r"(?<![A-Za-z])(?:B\.A\.M\.S\.|M\.B\.B\.S\.|B\.Sc\.|M\.Sc\.|B\.Com\.|M\.Com\.)(?![A-Za-z])", re.I)
FIELD_RULES = {
    "candidate_name": "name",
    "name": "name",
    "birth_place": "place",
    "place": "place",
    "education": "text",
    "address": "text",
    "mobile_number": "preserve",
    "mobile": "preserve",
    "dob": "preserve",
    "date_of_birth": "preserve",
    "time": "preserve",
    "height": "preserve",
    "blood_group": "preserve",
    "registration_id": "preserve",
    "amount": "preserve",
}
MOCK_TRANSLATIONS = {
    "Rahul Patil": "राहुल पाटील",
    "Solapur": "सोलापूर",
    "Pune": "पुणे",
    "Education": "शिक्षण",
    "Address": "पत्ता",
}


def _translate_mock(text: str) -> str:
    if text in MOCK_TRANSLATIONS:
        return MOCK_TRANSLATIONS[text]
    for english, marathi in MOCK_TRANSLATIONS.items():
        text = re.sub(re.escape(english), marathi, text, flags=re.IGNORECASE)
    return text


def _translate_google(text: str) -> str:
    if get_settings().translation_mock:
        return _translate_mock(text)
    from google.cloud import translate_v2 as translate

    response = translate.Client().translate(text, target_language="mr", format_="text")
    return response["translatedText"]


def translate_field(field: str, value: str, translator=_translate_google) -> str:
    text = str(value)
    if not text or FIELD_RULES.get(field.lower(), "text") == "preserve" or not re.search(r"[A-Za-z]", text):
        return text
    protected = []

    def replace_match(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"ZXQSAFE{len(protected) - 1}QXZ"

    text = ABBREVIATION_PATTERN.sub(replace_match, text)
    text = NUMBER_PATTERN.sub(replace_match, text)
    translated = translator(text)
    for index, original in enumerate(protected):
        translated = translated.replace(f"ZXQSAFE{index}QXZ", original)
    return translated


def translate_fields(values: dict[str, object], translator=_translate_google) -> dict[str, str]:
    return {key: translate_field(key, str(value), translator) for key, value in values.items()}
