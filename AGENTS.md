# Common Task Framework

Design-first repository: `specs/ctf.spec.toml` is the behavioral contract and `src/`
is still empty.

## Commands

Everything runs in Docker. qed, Lean, black, flake8, and mypy are absent from the
host; python3 and pytest are present, so the suite also runs directly.

- `docker compose build` — build the image; the first build compiles Lean 4.28 and
  qed from source and takes minutes.
- `docker compose run --rm devarops make verify` — check the spec.
- `docker compose run --rm devarops make tests` — run `tests/`.
- `docker compose run --rm devarops make check` — black, flake8, mypy at 100 columns.
- The compose volume mounts the repo at `/workdir`, so paths resolve from the repo
  root.
- Container name: `common_task_framework_ci`.

## Toolchain

- qed is cloned from its default branch at build time, so pin a commit when a verify
  result must be reproducible.
- `make check` covers `tests/` only; add the package path once `src/` gains one.

## Spec workflow

- One spec, `specs/ctf.spec.toml`. Behavior is defined there; this file does not
  restate it.
- All criteria exist; unimplemented behavior carries `skip = "Not implemented"`.
- Land the test first, then delete the `skip` line. Never weaken a criterion to make
  it pass.
- `make tests` runs `tests/test_repository.py`, which checks that the spec parses and
  every criterion is traceable.

## Conventions

- Commits: one gitmoji, a capitalized imperative summary, a blank line, then a body
  explaining why. `first commit` predates this.
- Terminology was renamed in `0725f3c` and the older names are wrong: `Evaluation
  Criteria` (not Acceptance Criteria), `rationale`/`recommendation` (not
  `why_explanation`/`kr_instruction`), one `scores` array, and an ELO body of
  `participant_a`/`participant_b`/`result`.
- `.gitignore` lists `.gitignore` and `.aider*`, so editing it never shows in
  `git status` and it stays untracked.

## Layout

- `specs/ctf.spec.toml` — the contract; each `verify` names a selector in `tests/`.
- `tests/` — pytest suite.
- `examples/tmp/` — prototypes: an OpenRouter `curl` call, two sample replies, and
  two sample challenge texts.
- `src/` — implementation, still empty.
