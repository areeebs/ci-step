#!/usr/bin/env python3
"""
ci-step CLI.

  python3 -m cistep list   -w .github/workflows/ci.yml [-j job]
  python3 -m cistep run    -w .github/workflows/ci.yml -j job [--from N] [--to N] [--only N] [--rollback]
  python3 -m cistep restore <snapshot-dir> [target]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from .runner import load_workflow, list_jobs, steps_for, run_steps, restore
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from cistep.runner import load_workflow, list_jobs, steps_for, run_steps, restore


def _resolve_job(wf, job):
    jobs = list_jobs(wf)
    if job:
        return job
    if len(jobs) == 1:
        return jobs[0]
    raise SystemExit(f"multiple jobs; pick one with -j: {', '.join(jobs)}")


def cmd_list(args):
    wf = load_workflow(args.workflow)
    if not args.job:
        print("jobs:", ", ".join(list_jobs(wf)))
    job = _resolve_job(wf, args.job) if args.job or len(list_jobs(wf)) == 1 else None
    if job:
        print(f"\nsteps in '{job}':")
        for s in steps_for(wf, job):
            kind = "run" if s.runnable else f"uses {s.uses}"
            print(f"  [{s.index}] {s.name}  ({kind})")
    return 0


def cmd_run(args):
    wf = load_workflow(args.workflow)
    job = _resolve_job(wf, args.job)
    steps = steps_for(wf, job)
    if args.only is not None:
        start = end = args.only
    else:
        start = args.from_ or 0
        end = args.to
    print(f"running job '{job}' steps [{start}..{end if end is not None else len(steps)-1}]"
          f"{' with rollback snapshots' if args.rollback else ''}\n")

    def report(r):
        print(f"[{r.step.index}] {r.step.name}: {r.status.upper()}")
        if r.output:
            for line in r.output.splitlines():
                print(f"    {line}")

    results = run_steps(steps, cwd=args.cwd, start=start, end=end,
                        rollback=args.rollback, on_result=report)
    failed = [r for r in results if r.status == "failed"]
    print(f"\n{len(results)} step(s) run, {len(failed)} failed")
    return 1 if failed else 0


def cmd_restore(args):
    restore(args.snapshot, args.target)
    print(f"restored {args.snapshot} -> {args.target}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cistep", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list jobs and steps")
    pl.add_argument("-w", "--workflow", required=True)
    pl.add_argument("-j", "--job")
    pl.set_defaults(func=cmd_list)

    pr = sub.add_parser("run", help="run steps locally")
    pr.add_argument("-w", "--workflow", required=True)
    pr.add_argument("-j", "--job")
    pr.add_argument("--from", dest="from_", type=int, help="start at step index")
    pr.add_argument("--to", type=int, help="stop at step index (inclusive)")
    pr.add_argument("--only", type=int, help="run only this step index")
    pr.add_argument("--rollback", action="store_true", help="snapshot before each step")
    pr.add_argument("--cwd", default=".")
    pr.set_defaults(func=cmd_run)

    prs = sub.add_parser("restore", help="restore a snapshot")
    prs.add_argument("snapshot")
    prs.add_argument("target", nargs="?", default=".")
    prs.set_defaults(func=cmd_restore)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
