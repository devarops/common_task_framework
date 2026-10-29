# Backlog

`specs/ctf.spec.toml` is the contract: every criterion is written and carries
`skip = "Not implemented"` until its test exists. This file holds build order and the
design notes that cannot be machine-proven. Behavior is not restated here.

## Build order

| Phase | Criteria to unskip | Status |
|-------|--------------------|--------|
| 1. Core orchestrator and validation | `spec_parser`, `spec_missing_section`, `spec_aspects`, `spec_third_person`, `challenge_layout`, `challenge_solution_import`, `gate_runs_pytest`, `gate_failure`, `gate_pass`, `referee_score_range`, `aggregation_aspect_median`, `aggregation_final_median`, `orchestrator_shell` | ❌ |
| 2. LLM integrations | `match_first_prompt`, `match_code_fence`, `match_no_code_fence`, `participant_text_interface`, `referee_count`, `referee_invalid_json`, `resilience_timeout` | ❌ |
| 3. ELO service | `pairing_roulette`, `outcome_payload`, `outcome_rating`, `resilience_elo`, `resilience_single_participant` | ❌ |
| 4. Orchestrator ↔ ELO integration | `outcome_draw` | ❌ |
| 5. Feedback carryover and match loop | `match_carryover`, `loop_threshold`, `loop_seats`, `aggregation_feedback_order`, `aggregation_gate_failure` | ❌ |
| 6. Monitoring | `post_loop_report` | ❌ |

A phase is done when its criteria pass without `skip`. The phase table is the only
build order; the spec does not record sequencing.

## Design notes

- **Seat carryover** exists so a newly paired participant inherits what the previous
  occupant of that seat learned, even though it did not write the earlier solution.
  Rejected alternative: send only the feedback, which loses the code the feedback
  describes.
- **The hidden gate is the Chinese wall**: tests are never in a participant prompt,
  mirroring kata conventions. That is why a gate failure produces no feedback JSON —
  there is nothing safe to say about code the participant cannot be shown tests for.
- **The ELO service is separate** so ratings survive spec changes and can be shared by
  other consumers. Same machine or another host is an operational choice, not a
  design one.
- **Rating maths is delegated**: the orchestrator sends an outcome, never a rating
  delta, so the service may use ELO or Glicko without changing the orchestrator.
- **Model IDs and API keys** are unspecified. The wrappers need a provider-agnostic
  call shape; the OpenRouter examples in `examples/tmp/` are reference material, not
  a dependency.

## Open questions

- `score` is typed as a JSON number but described as two decimal places. JSON drops
  trailing zeros, so decide whether the rule is about rounding or about a string
  representation.
- Where pooled participants are registered (ELO service or orchestrator config) is
  not decided.
- Spec ambiguity is handled by human review only. Decide whether a machine check can
  catch an Evaluation Criteria section that no test or referee can score.
