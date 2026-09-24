from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.app import compose_image_prompt, new_session_id


def test_new_image_concept_does_not_include_old_prompt():
    assert compose_image_prompt("old monster", "new robot", True) == "new robot"


def test_image_revision_preserves_context():
    out = compose_image_prompt("church giant", "make it taller", False)
    assert "church giant" in out
    assert "make it taller" in out
    assert "Preserve the identity" in out


def test_session_ids_are_nonempty_and_unique():
    a = new_session_id()
    b = new_session_id()
    assert a
    assert b
    assert a != b
