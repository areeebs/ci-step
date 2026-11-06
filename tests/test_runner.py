import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cistep.runner import (load_workflow, list_jobs, steps_for, run_step,
                           run_steps, snapshot, restore)

WF = ROOT / "examples/workflow.yml"


class Parsing(unittest.TestCase):
    def test_jobs_and_steps(self):
        wf = load_workflow(WF)
        self.assertEqual(list_jobs(wf), ["build"])
        steps = steps_for(wf, "build")
        self.assertEqual(len(steps), 4)
        self.assertFalse(steps[0].runnable)   # uses: actions/checkout
        self.assertTrue(steps[1].runnable)    # run: echo

    def test_unknown_job_raises(self):
        with self.assertRaises(KeyError):
            steps_for(load_workflow(WF), "nope")


class Running(unittest.TestCase):
    def test_run_echo_step(self):
        steps = steps_for(load_workflow(WF), "build")
        res = run_step(steps[1], cwd=ROOT)
        self.assertEqual(res.status, "ok")
        self.assertIn("hello from ci-step", res.output)

    def test_uses_step_skipped(self):
        steps = steps_for(load_workflow(WF), "build")
        self.assertEqual(run_step(steps[0], cwd=ROOT).status, "skipped")

    def test_stops_on_failure(self):
        from cistep.runner import Step
        steps = [Step(0, "ok", "true", None, "bash"),
                 Step(1, "boom", "exit 3", None, "bash"),
                 Step(2, "never", "echo nope", None, "bash")]
        results = run_steps(steps, cwd=ROOT)
        self.assertEqual([r.status for r in results], ["ok", "failed"])


class SnapshotRestore(unittest.TestCase):
    def test_snapshot_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / "work"
            work.mkdir()
            (work / "a.txt").write_text("original")
            snap = snapshot(work, Path(d) / "snap")
            (work / "a.txt").write_text("changed")
            restore(snap, work)
            self.assertEqual((work / "a.txt").read_text(), "original")


if __name__ == "__main__":
    unittest.main()
