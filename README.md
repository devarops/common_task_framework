# common_task_framework

A way to grade artificial-intelligence workers by having them compete on the same job.

## What it does

Two AI assistants receive the same written task. Answers that fail an automatic
correctness check are thrown out, an independent panel of AI judges scores the rest
against the same criteria, and a running rating — like a chess leaderboard — records
who does best over time. Tasks can be programming puzzles with known answers, such as
the pair-summing kata in `examples/tmp/spec_1.md`, or real data work, such as
predicting chick ages from body measurements in `examples/tmp/spec_2.md`.

A match unfolds in four steps:

1. Two assistants are chosen, favouring the higher-rated ones.
2. Both attempt the task from the same instructions.
3. Wrong answers score zero; the others go to the judges.
4. The scores choose a winner and update the ratings.

The next pair then sees the best earlier attempt and the judges' comments on it.

## Usage

The framework is not implemented yet. The repository holds the acceptance criteria in
`specs/ctf.spec.toml` — every unimplemented behavior is marked `Not implemented` —
plus the plans in `TODO.md`.

## Before you start

- Docker with Compose.
- No API key is needed to read the task texts or to build the image.

## Run the project

```sh
docker compose build
docker compose run --rm devarops make verify
```

`make verify` checks the acceptance criteria and reports each one as passing or
skipped. `make tests` runs the test suite and `make check` lints it.
