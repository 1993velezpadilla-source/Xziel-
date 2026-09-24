from pathlib import Path
import base64
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.attachments import AttachmentStore


def test_text_attachment_round_trip_and_inline(tmp_path: Path):
    store = AttachmentStore(tmp_path / "uploads")
    item = store.save_b64(
        "session1",
        "../notes?.txt",
        "text/plain",
        base64.b64encode(b"hello map").decode("ascii"),
    )
    assert item.filename == "notes_.txt"
    loaded = store.load("session1", item.attachment_id)
    content = store.to_message_content("Read this", [loaded])
    assert isinstance(content, str)
    assert "hello map" in content
    assert "notes_.txt" in content


def test_image_attachment_becomes_multimodal_content(tmp_path: Path):
    store = AttachmentStore(tmp_path / "uploads")
    raw = b"\x89PNG\r\n\x1a\nnot-a-real-image-but-good-for-payload-test"
    item = store.save_b64(
        "session1",
        "floorplan.png",
        "image/png",
        base64.b64encode(raw).decode("ascii"),
    )
    content = store.to_message_content("Use this floorplan", [item])
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_attachment_rejects_invalid_base64(tmp_path: Path):
    store = AttachmentStore(tmp_path / "uploads")
    try:
        store.save_b64("session1", "x.txt", "text/plain", "%%%")
    except ValueError as exc:
        assert "base64" in str(exc)
    else:
        raise AssertionError("invalid base64 must be rejected")


def test_attachment_ids_cannot_escape_session_directory(tmp_path: Path):
    store = AttachmentStore(tmp_path / "uploads")
    try:
        store.load("session1", "../../secret")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("unsafe attachment id must be rejected")


def test_save_bytes_supports_generated_image_persistence(tmp_path: Path):
    store = AttachmentStore(tmp_path / "uploads")
    item = store.save_bytes("session1", "generated.png", "image/png", b"png-bytes")
    loaded = store.load("session1", item.attachment_id)
    assert loaded.filename == "generated.png"
    assert loaded.data_path.read_bytes() == b"png-bytes"
