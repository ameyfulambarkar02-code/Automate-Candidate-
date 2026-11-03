from io import BytesIO
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from app.config import get_settings


class GoogleDriveService:
    def __init__(self, credentials):
        self.api = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def download(self, file_id: str) -> tuple[bytes, dict[str, Any]]:
        metadata = self.api.files().get(
            fileId=file_id,
            fields="id,name,mimeType,size",
            supportsAllDrives=True,
        ).execute()
        if int(metadata.get("size", 0)) > get_settings().max_upload_bytes:
            raise ValueError(f"Drive file exceeds the configured {get_settings().max_upload_bytes}-byte limit.")
        buffer = BytesIO()
        downloader = MediaIoBaseDownload(
            buffer, self.api.files().get_media(fileId=file_id, supportsAllDrives=True)
        )
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue(), metadata

    def create_candidate_folder(self, parent_id: str | None, name: str) -> dict[str, str]:
        existing = self._find_child(parent_id or "root", name, "application/vnd.google-apps.folder")
        if existing:
            return {
                "id": existing["id"],
                "name": existing.get("name", name),
                "webViewLink": existing.get("webViewLink", ""),
            }
        metadata: dict[str, Any] = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        result = self.api.files().create(
            body=metadata,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        ).execute()
        return {"id": result["id"], "name": result["name"], "webViewLink": result.get("webViewLink", "")}

    def upload(self, folder_id: str, name: str, content: bytes, mime_type: str) -> str:
        existing = self._find_child(folder_id, name)
        if existing:
            return existing["id"]
        media = MediaIoBaseUpload(BytesIO(content), mimetype=mime_type, resumable=True)
        result = self.api.files().create(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        ).execute()
        return result["id"]

    def _find_child(self, parent_id: str, name: str, mime_type: str | None = None) -> dict[str, str] | None:
        escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
        mime_filter = f" and mimeType = '{mime_type}'" if mime_type else ""
        result = self.api.files().list(
            q=f"name = '{escaped_name}' and '{parent_id}' in parents and trashed = false{mime_filter}",
            pageSize=1,
            fields="files(id,name,webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = result.get("files", [])
        return files[0] if files else None

    def folder_link(self, folder_id: str) -> str:
        return f"https://drive.google.com/drive/folders/{folder_id}"
