import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "shared" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "shared" / "tools"))
if str(ROOT / "shared" / "workflows") not in sys.path:
    sys.path.insert(0, str(ROOT / "shared" / "workflows"))
if str(ROOT / "shared" / "workflows" / "validators") not in sys.path:
    sys.path.insert(0, str(ROOT / "shared" / "workflows" / "validators"))

import kb  # noqa: E402
import coordinator  # noqa: E402
import check_checklist  # noqa: E402
import check_dynamic_kb_status  # noqa: E402
import check_select_candidate  # noqa: E402


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
        self.assertEqual(sample["trigger_reasons"], ["new_decisions"])
        self.assertIn("trigger_evidence", sample)
        self.assertNotIn("file", sample)

    def test_check_memory_trigger_next_step_command_includes_snapshot_path(self):
        node = {"id": "check_memory_trigger", "required_outputs": []}
        cmd = coordinator._next_step_command(node, "post_task_20260424_120307", project="ecr-ecn")
        self.assertIn('"snapshot_path": "shared/kb/memory/YYYY-MM-DD.md"', cmd)
        self.assertIn('"snapshot_id": "YYYY-MM-DD"', cmd)
        self.assertIn('"trigger_reasons": ["new_decisions"]', cmd)
        self.assertNotIn('"file": "memory/"', cmd)


class ChecklistGuardrailTests(unittest.TestCase):
    def test_low_signal_answer_is_rejected(self):
        self.assertTrue(check_checklist._is_low_signal_answer("ok done"))
        self.assertFalse(check_checklist._is_low_signal_answer("checked 3 rows; null rate 0%; duplicate count 0"))


class DynamicKbStatusGuardrailTests(unittest.TestCase):
    def test_missing_kb_entry_ids_fails_closed(self):
        ok, message = check_dynamic_kb_status.validate({"outputs": {}, "root": str(ROOT)})
        self.assertFalse(ok)
        self.assertIn("kb_entry_ids missing", message)


class SelectCandidateGuardrailTests(unittest.TestCase):
    def test_invalid_skill_name_is_rejected_before_db_access(self):
        ok, message = check_select_candidate.validate(
            {
                "outputs": {
                    "learning_id": "STD-L001",
                    "suggested_skill": "Bad Skill",
                    "overlap_found": False,
                },
                "root": str(ROOT),
            }
        )
        self.assertFalse(ok)
        self.assertIn("kebab-case", message)


if __name__ == "__main__":
    unittest.main()
