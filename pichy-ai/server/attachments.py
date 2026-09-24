from __future__ import annotations

import base64
import json
import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 250_000
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class StoredAttachment:
    attachment_id: str
    filename: str
    mime_type: str
    size: int
    data_path: Path


class AttachmentStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_filename(name: str) -> str:
        cleaned = _SAFE_NAME.sub("_", Path(name).name).strip("._")
        return cleaned[:120] or "attachment"

    def save_b64(self, session_id: str, filename: str, mime_type: str, b64_data: str) -> StoredAttachment:
        try:
            raw = base64.b64decode(b64_data, validate=True)
        except Exception as exc:
            raise ValueError("invalid base64 attachment") from exc
        if not raw:
            raise ValueError("attachment is empty")
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"attachment exceeds {MAX_ATTACHMENT_BYTES} bytes")

        aid = uuid.uuid4().hex
        session_dir = self.root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        safe_name = self._safe_filename(filename)
        guessed = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        mime = (mime_type or guessed).split(";", 1)[0].strip().lower()
        data_path = session_dir / f"{aid}.bin"
        meta_path = session_dir / f"{aid}.json"
        data_path.write_bytes(raw)
        meta_path.write_text(
            json.dumps(
                {
                    "attachment_id": aid,
                    "filename": safe_name,
                    "mime_type": mime,
                    "size": len(raw),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return StoredAttachment(aid, safe_name, mime, len(raw), data_path)

    def load(self, session_id: str, attachment_id: str) -> StoredAttachment:
        if not re.fullmatch(r"[0-9a-f]{32}", attachment_id):
            raise FileNotFoundError("invalid attachment id")
        session_dir = self.root / session_id
        meta_path = session_dir / f"{attachment_id}.json"
        data_path = session_dir / f"{attachment_id}.bin"
        if not meta_path.is_file() or not data_path.is_file():
            raise FileNotFoundError("attachment not found")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return StoredAttachment(
            attachment_id=attachment_id,
            filename=meta["filename"],
            mime_type=meta["mime_type"],
            size=int(meta["size"]),
            data_path=data_path,
        )

    def to_message_content(self, message: str, attachments: list[StoredAttachment]) -> str | list[dict[str, Any]]:
        if not attachments:
            return message

        has_image = any(a.mime_type.startswith("image/") for a in attachments)
        if not has_image:
            chunks = [message]
            for item in attachments:
                raw = item.data_path.read_bytes()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = ""
                if text:
                    text = text[:MAX_TEXT_CHARS]
                    chunks.append(f"\n\n[Attached file: {item.filename} | {item.mime_type}]\n{text}")
                else:
                    chunks.append(
                        f"\n\n[Attached file: {item.filename} | {item.mime_type} | {item.size} bytes. "
                        "Binary content stored but not inlined.]"
                    )
            return "".join(chunks)

        content: list[dict[str, Any]] = [{"type": "text", "text": message}]
        for item in attachments:
            raw = item.data_path.read_bytes()
            if item.mime_type.startswith("image/"):
                data = base64.b64encode(raw).decode("ascii")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{item.mime_type};base64,{data}"},
                    }
                )
            else:
                try:
                    text = raw.decode("utf-8")[:MAX_TEXT_CHARS]
                except UnicodeDecodeError:
                    text = f"[Binary attachment {item.filename}, {item.size} bytes]"
                content.append(
                    {
                        "type": "text",
                        "text": f"\nAttached file {item.filename} ({item.mime_type}):\n{text}",
                    }
                )
        return content
