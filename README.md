# ci-step

Run and **debug your CI workflow steps locally** — one at a time, with
rollback — instead of the commit → push → wait → read-logs loop.

Tools like `act` run a whole GitHub Actions workflow locally, but you still
can't stop at a step, poke around, re-run just that step, and undo its changes.
`ci-step` is built around that debugging loop.

> Inspired by a recurring developer wish ("I hate that I need to write commands
> in YAML, commit, and then look at the result" — plus "give me record and
> rollback"). This is a clean-room take on that idea, not a fork of anything.

## Install

```bash
pip install -r requirements.txt   # just PyYAML
```

## Use

List the jobs and steps in a workflow:

```bash
python3 -m cistep list -w .github/workflows/ci.yml
```

Run the whole job locally:

```bash
python3 -m cistep run -w .github/workflows/ci.yml -j build
```

Run just one step, or a range — the core debugging move:

```bash
python3 -m cistep run -w .github/workflows/ci.yml -j build --only 3
python3 -m cistep run -w .github/workflows/ci.yml -j build --from 2 --to 4
```

Snapshot the working tree before each step so you can undo:

```bash
python3 -m cistep run -w .github/workflows/ci.yml -j build --rollback
python3 -m cistep restore .cistep-snapshots/before-step-3-<ts> .
```

## What runs and what doesn't

- `run:` steps execute in a real shell (`bash -e -o pipefail`), with each step's
  `env:` applied, and execution stops at the first failing step — like CI.
- `uses:` steps (marketplace actions) are reported as **skipped**: they can't run
  locally, and ci-step won't pretend otherwise.

## Roadmap

- Interactive pause/continue/edit between steps (true step debugger).
- GitLab CI and Circle support.
- Matrix expansion and container (`container:`) steps.
- Secret/ env-file injection.

## License

[MIT](LICENSE).
