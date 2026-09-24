from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.memory import SessionMemory


def test_session_memory_round_trip(tmp_path: Path):
    store = SessionMemory(tmp_path / "memory.sqlite3")
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    store.save("abc", history, "old image prompt")

    loaded = store.load("abc")
    assert loaded is not None
    assert loaded["history"] == history
    assert loaded["last_image_prompt"] == "old image prompt"


def test_session_memory_upsert_and_delete(tmp_path: Path):
    store = SessionMemory(tmp_path / "memory.sqlite3")
    store.save("abc", [{"role": "user", "content": "one"}])
    store.save("abc", [{"role": "user", "content": "two"}])

    loaded = store.load("abc")
    assert loaded is not None
    assert loaded["history"][0]["content"] == "two"
    assert store.delete("abc") is True
    assert store.load("abc") is None


def test_list_recent_is_bounded(tmp_path: Path):
    store = SessionMemory(tmp_path / "memory.sqlite3")
    for i in range(5):
        store.save(f"s{i}", [{"role": "user", "content": str(i)}])
    rows = store.list_recent(3)
    assert len(rows) == 3
    assert all("session_id" in row for row in rows)
