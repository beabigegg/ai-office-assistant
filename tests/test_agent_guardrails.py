import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "shared" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "shared" / "tools"))
if str(ROOT / "shared" / "workflows") not in sys.path:
    sys.path.insert(0, str(ROOT / "shared" / "workflows"))

import kb  # noqa: E402
import coordinator  # noqa: E402


class KbConfidenceCompatibilityTests(unittest.TestCase):
    def test_learning_confidence_accepts_canonical_labels(self):
        self.assertEqual(kb._normalize_learning_confidence("high"), "high")
        self.assertEqual(kb._normalize_learning_confidence("medium"), "medium")
        self.assertEqual(kb._normalize_learning_confidence("low"), "low")

    def test_learning_confidence_maps_legacy_numeric_scores(self):
        self.assertEqual(kb._normalize_learning_confidence("0.90"), "high")
        self.assertEqual(kb._normalize_learning_confidence("0.60"), "medium")
        self.assertEqual(kb._normalize_learning_confidence("0.30"), "low")

    def test_learning_confidence_rejects_out_of_range_values(self):
        with self.assertRaises(Exception):
            kb._normalize_learning_confidence("1.20")


class CoordinatorSampleOutputTests(unittest.TestCase):
    def test_check_memory_trigger_uses_snapshot_outputs(self):
        node = {
            "id": "check_memory_trigger",
            "required_outputs": [
                {"path_contains": "memory/", "description": "memory snapshot if conditions met"}
            ],
        }
        sample = coordinator._format_sample_outputs(node, project="ecr-ecn")
        self.assertEqual(sample["memory_conditions_met"], True)
        self.assertEqual(sample["snapshot_path"], "shared/kb/memory/YYYY-MM-DD.md")
        self.assertEqual(sample["snapshot_id"], "YYYY-MM-DD")
        self.assertNotIn("file", sample)

    def test_check_memory_trigger_next_step_command_includes_snapshot_path(self):
        node = {"id": "check_memory_trigger", "required_outputs": []}
        cmd = coordinator._next_step_command(node, "post_task_20260424_120307", project="ecr-ecn")
        self.assertIn('"snapshot_path": "shared/kb/memory/YYYY-MM-DD.md"', cmd)
        self.assertIn('"snapshot_id": "YYYY-MM-DD"', cmd)
        self.assertNotIn('"file": "memory/"', cmd)


if __name__ == "__main__":
    unittest.main()
