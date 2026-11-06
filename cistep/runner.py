"""
Core of ci-step: parse a GitHub Actions workflow and run its steps locally,
one at a time, with optional per-step snapshots so you can roll back.

MVP scope: runs `run:` steps in a shell. `uses:` steps (marketplace actions)
can't execute locally, so they're reported as skipped rather than faked.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SNAPSHOT_IGNORE = shutil.ignore_patterns(
    ".git", "node_modules", ".cistep-snapshots", "__pycache__", ".venv", "venv"
)


@dataclass
class Step:
    index: int
    name: str
    run: str | None
    uses: str | None
    shell: str
    env: dict = field(default_factory=dict)

    @property
    def runnable(self) -> bool:
        return bool(self.run)


@dataclass
class StepResult:
    step: Step
    status: str  # ok | failed | skipped
    returncode: int | None
    output: str


def load_workflow(path: str | Path) -> dict:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict) or "jobs" not in data:
        raise ValueError(f"{path}: not a workflow (no 'jobs' key)")
    return data


def list_jobs(wf: dict) -> list[str]:
    return list(wf.get("jobs", {}).keys())


def steps_for(wf: dict, job: str) -> list[Step]:
    jobs = wf.get("jobs", {})
    if job not in jobs:
        raise KeyError(f"job '{job}' not found; have: {', '.join(jobs) or '(none)'}")
    raw_steps = jobs[job].get("steps", []) or []
    steps = []
    for i, s in enumerate(raw_steps):
        name = s.get("name") or s.get("uses") or (s.get("run", "").splitlines() or [""])[0][:50] or f"step {i}"
        steps.append(Step(index=i, name=name, run=s.get("run"), uses=s.get("uses"),
                          shell=s.get("shell", "bash"), env=s.get("env", {}) or {}))
    return steps


def snapshot(src: str | Path, dest: str | Path) -> Path:
    """Copy the working tree (minus VCS/build noise) to dest for later rollback."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=SNAPSHOT_IGNORE)
    return dest


def restore(snapshot_dir: str | Path, target: str | Path) -> None:
    """Restore files from a snapshot back into target (overwrites touched files)."""
    snapshot_dir = Path(snapshot_dir)
    target = Path(target)
    for item in snapshot_dir.rglob("*"):
        rel = item.relative_to(snapshot_dir)
        out = target / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)


def run_step(step: Step, cwd: str | Path, extra_env: dict | None = None) -> StepResult:
    if not step.runnable:
        return StepResult(step, "skipped", None,
                          f"(uses: {step.uses}) — marketplace actions can't run locally")
    env = {**os.environ, **step.env, **(extra_env or {})}
    shell = step.shell if step.shell in ("bash", "sh") else "bash"
    proc = subprocess.run([shell, "-e", "-o", "pipefail", "-c", step.run],
                          cwd=str(cwd), env=env, capture_output=True, text=True)
    status = "ok" if proc.returncode == 0 else "failed"
    return StepResult(step, status, proc.returncode, (proc.stdout + proc.stderr).strip())


def run_steps(steps: list[Step], cwd: str | Path, start: int = 0, end: int | None = None,
              rollback: bool = False, snapshot_root: str | Path = ".cistep-snapshots",
              on_result=None) -> list[StepResult]:
    results = []
    sel = steps[start:(end + 1 if end is not None else None)]
    for step in sel:
        if rollback:
            snapshot(cwd, Path(snapshot_root) / f"before-step-{step.index}-{int(time.time())}")
        result = run_step(step, cwd)
        results.append(result)
        if on_result:
            on_result(result)
        if result.status == "failed":
            break
    return results
