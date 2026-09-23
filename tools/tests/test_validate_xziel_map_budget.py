import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "validate_xziel_map_budget.py"

spec = importlib.util.spec_from_file_location(
    "validate_xziel_map_budget",
    SCRIPT,
)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)

MANIFEST = validator.load_manifest(
    REPO_ROOT
    / "engine"
    / "config"
    / "xziel_engine_limits.v1.json"
)


class XzielBudgetValidatorTests(unittest.TestCase):
    def test_engine_contract_matches_manifest(self):
        findings = validator.verify_engine_source(
            REPO_ROOT,
            MANIFEST,
        )
        self.assertEqual([], findings)

    def test_small_xmap_passes(self):
        content = """xziel_map 2
player_spawn 0 0 0 0
zombie_spawn 1 0 1
floor 1 1 1 1 1
box 1 1 1 1 1 1
door 2000 0 0 0 1 1 1 100
window 3000 0 0 0 1 1 1 100
interaction 4000 0 0 0 1 1 1 100
arena -10 10 -10 10
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.xmap"
            path.write_text(content, encoding="utf-8")
            report, findings = validator.inspect_xmap(
                path,
                MANIFEST,
            )

        self.assertEqual(2, report["version"])
        self.assertEqual(1, report["records"]["door"])
        self.assertFalse(
            any(item.severity == "ERROR" for item in findings)
        )

    def test_xmap_v3_is_not_shipping_yet(self):
        content = """xziel_map 3
player_spawn 0 0 0 0 0
player_spawn 1 1 0 0 0
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "online.xmap"
            path.write_text(content, encoding="utf-8")
            _report, findings = validator.inspect_xmap(
                path,
                MANIFEST,
            )

        self.assertTrue(
            any(
                item.severity == "ERROR"
                and "current shipping parser" in item.message
                for item in findings
            )
        )

    def test_xzsm_header_passes(self):
        header = struct.pack(
            "<4sIIII",
            b"XZSM",
            5,
            32,
            100_000,
            150_000,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.xzsm"
            path.write_bytes(header + bytes(128))
            report, findings = validator.inspect_xzsm(
                path,
                MANIFEST,
            )

        self.assertEqual(32, report["batches"])
        self.assertFalse(
            any(item.severity == "ERROR" for item in findings)
        )

    def test_xzsm_hard_limit_fails(self):
        hard = MANIFEST["hard_limits"]["static_mesh"]
        header = struct.pack(
            "<4sIIII",
            b"XZSM",
            5,
            hard["max_batches"] + 1,
            100,
            100,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "too_many_batches.xzsm"
            path.write_bytes(header)
            _report, findings = validator.inspect_xzsm(
                path,
                MANIFEST,
            )

        self.assertTrue(
            any(
                item.severity == "ERROR"
                and "batches" in item.message
                for item in findings
            )
        )


if __name__ == "__main__":
    unittest.main()
