import re
from typing import Any

from googleapiclient.discovery import build

FORM_ID_PATTERN = re.compile(r"(?:/forms/d/|/forms/u/\d+/d/)([A-Za-z0-9_-]+)")


def extract_form_id(form_url: str) -> str:
    match = FORM_ID_PATTERN.search(form_url.strip())
    if not match or not form_url.startswith(("https://docs.google.com/forms/", "https://forms.google.com/")):
        raise ValueError("Enter a valid Google Forms URL that you have permission to access.")
    return match.group(1)


class GoogleFormsService:
    def __init__(self, credentials):
        self.api = build("forms", "v1", credentials=credentials, cache_discovery=False)

    def get_form(self, form_id: str) -> dict[str, Any]:
        return self.api.forms().get(formId=form_id).execute()

    def get_questions(self, form_id: str) -> list[dict[str, str]]:
        form = self.get_form(form_id)
        questions = []
        for item in form.get("items", []):
            question = item.get("questionItem", {}).get("question", {})
            if question:
                questions.append({"item_id": str(question.get("questionId", item.get("itemId", ""))), "title": item.get("title", "")})
            for grouped in item.get("questionGroupItem", {}).get("questions", []):
                questions.append({"item_id": str(grouped.get("questionId", "")), "title": item.get("title", "")})
        return questions

    def list_responses(self, form_id: str) -> list[dict[str, Any]]:
        responses = []
        token = None
        while True:
            result = self.api.forms().responses().list(formId=form_id, pageSize=500, pageToken=token).execute()
            responses.extend(result.get("responses", []))
            token = result.get("nextPageToken")
            if not token:
                return responses

    def response_values(self, form_id: str, response: dict[str, Any]) -> dict[str, Any]:
        questions = {q["item_id"]: q["title"] for q in self.get_questions(form_id)}
        data = {}
        answers_by_id = {}
        for item_id, answer in response.get("answers", {}).items():
            title = questions.get(item_id, item_id)
            texts = answer.get("textAnswers", {}).get("answers", [])
            files = answer.get("fileUploadAnswers", {}).get("answers", [])
            values = [item["value"] for item in texts if item.get("value") is not None]
            upload_ids = [item["fileId"] for item in files if item.get("fileId")]
            value = values[0] if len(values) == 1 else values if values else upload_ids
            data[title] = value
            answers_by_id[item_id] = value
        data["_answers_by_id"] = answers_by_id
        return data
