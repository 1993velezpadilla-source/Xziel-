from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from tools import ToolBox, ToolError


def test_workspace_escape_blocked(tmp_path):
    tb = ToolBox(tmp_path)
    try:
        tb.read_file("../outside.txt")
    except ToolError:
        pass
    else:
        raise AssertionError("workspace escape was not blocked")


def test_write_and_read(tmp_path):
    tb = ToolBox(tmp_path)
    tb.write_file("a/b.txt", "hello")
    assert tb.read_file("a/b.txt") == "hello"


def test_calculator(tmp_path):
    tb = ToolBox(tmp_path)
    assert tb.calculate("2 + 3 * 4") == "14"


def test_destructive_host_command_blocked(tmp_path, monkeypatch):
    monkeypatch.delenv("PICHY_UNSAFE_SHELL", raising=False)
    tb = ToolBox(tmp_path)
    try:
        tb.shell("sudo reboot")
    except ToolError:
        pass
    else:
        raise AssertionError("destructive command was not blocked")
