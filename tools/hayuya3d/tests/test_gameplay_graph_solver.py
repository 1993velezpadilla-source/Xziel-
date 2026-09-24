#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAYUYA3D = HERE.parent
sys.path.insert(0, str(HAYUYA3D))

from gameplay_graph_solver import evaluate_gameplay_graph


class GameplayGraphSolverTests(unittest.TestCase):
    def test_looping_map_reports_loop_and_reachability(self):
        report = evaluate_gameplay_graph(
            nodes=["spawn", "a", "b", "c", "exit"],
            edges=[
                {"a": "spawn", "b": "a"},
                {"a": "a", "b": "b"},
                {"a": "b", "b": "c"},
                {"a": "c", "b": "a"},
                {"a": "c", "b": "exit"},
            ],
            start="spawn",
            required_nodes=["exit"],
            terminal_nodes=["exit"],
        )
        self.assertTrue(report["pass"])
        self.assertTrue(report["has_loop"])
        self.assertEqual(report["unreachable_required_nodes"], [])

    def test_locked_progression_edge_is_not_reachable_before_token(self):
        report = evaluate_gameplay_graph(
            nodes=["spawn", "power", "vault"],
            edges=[
                {"a": "spawn", "b": "power"},
                {"a": "power", "b": "vault", "requires": ["power_on"]},
            ],
            start="spawn",
            required_nodes=["vault"],
            terminal_nodes=["vault"],
        )
        self.assertFalse(report["pass"])
        self.assertIn("vault", report["unreachable_required_nodes"])
        self.assertEqual(report["metrics"]["locked_edge_count"], 1)

        unlocked = evaluate_gameplay_graph(
            nodes=["spawn", "power", "vault"],
            edges=[
                {"a": "spawn", "b": "power"},
                {"a": "power", "b": "vault", "requires": ["power_on"]},
            ],
            start="spawn",
            required_nodes=["vault"],
            terminal_nodes=["vault"],
            available_tokens=["power_on"],
        )
        self.assertTrue(unlocked["pass"])

    def test_one_way_trap_is_detected(self):
        report = evaluate_gameplay_graph(
            nodes=["spawn", "drop", "trap"],
            edges=[
                {"a": "spawn", "b": "drop", "bidirectional": False},
                {"a": "drop", "b": "trap", "bidirectional": False},
            ],
            start="spawn",
            required_nodes=["trap"],
        )
        self.assertFalse(report["pass"])
        self.assertIn("trap", report["dead_ends"])
        self.assertIn("unintended_directed_dead_ends", report["failures"])

    def test_articulation_point_is_reported(self):
        report = evaluate_gameplay_graph(
            nodes=["spawn", "hub", "left", "right"],
            edges=[
                {"a": "spawn", "b": "hub"},
                {"a": "hub", "b": "left"},
                {"a": "hub", "b": "right"},
            ],
            start="spawn",
            terminal_nodes=["left", "right"],
        )
        self.assertIn("hub", report["articulation_points"])


if __name__ == "__main__":
    unittest.main()
