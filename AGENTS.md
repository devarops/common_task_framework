# Common Task Framework

Design-first repository: `specs/ctf.spec.toml` is the behavioral contract and `src/`
is still empty.

## Commands

Everything runs in Docker; qed, Lean, and the Python toolchain are not on the host.

- `docker compose build` — build the image (Python, Lean toolchain, qed).
- `docker compose run --rm devarops make verify` — check the spec.
- `docker compose run --rm devarops make tests` — run `tests/`.
- `docker compose run --rm devarops make check` — black, flake8, mypy at 100 columns.
- Container name: `common_task_framework_ci`.

## Spec workflow

- One spec, `specs/ctf.spec.toml`. Behavior is defined there; this file does not
  restate it.
- Every criterion is written now. Unimplemented behavior carries
  `skip = "Not implemented"`.
- Land the test first, then delete the `skip` line. Never weaken a criterion to make
  it pass.
- `make tests` currently runs only `tests/test_repository.py`, which checks that the
  spec parses and every criterion has a description and a verification block.

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
