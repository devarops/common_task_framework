# **Common Task Framework (CTF) – System Design & Roadmap**

## 1. **Purpose**
The Common Task Framework evaluates and ranks LLM-based software/data analysis agents by pitting them against each other in structured tasks. It uses a multi-LLM pipeline: **Spec → Participant → Orchestrator → Referee → Orchestrator → ELO ranking**.

## 2. **Core Components**

| Component | Role | Implementation |
|-----------|------|----------------|
| **Spec** | A structured Markdown document describing a task. | Human-written or auto-generated. Contains required sections: `# Specification`, `## Context`, `## Task`, `## Evaluation Criteria`. Optional sections allowed. |
| **Participant LLM** | An LLM that receives the Spec (and later feedback) and produces a solution. | Any LLM, called via API. Exactly two per match, selected from a pool via roulette wheel (probability ∝ ELO). |
| **Referee LLM** | An LLM that evaluates a participant’s output against the Spec. Returns JSON with numeric scores and prose feedback. | At least three per match. Each referee independently produces per‑aspect scores. |
| **Orchestrator** | A deterministic program that coordinates the flow: validates inputs, sends prompts, aggregates referee scores, manages match outcomes, and communicates with the external ELO API. | No LLM; pure logic (Python). |
| **External ELO API** | A separate service that maintains participant ELO ratings, selects two participants per match (roulette wheel), and updates ratings after each match. | Web service (REST or gRPC). |

## 3. **End-to-End Workflow**

The orchestrator processes one spec at a time. For each spec, it runs up to N matches, pairing fresh participants each iteration. The loop stops early if either participant reaches the score threshold.

```
i = 0
while max(final_score_a, final_score_b) < threshold and i < N:
    pair participants          # fresh roulette-wheel selection
    run match                  # with seat-based carryover if i > 0
    POST /match/result         # ELO update
    i += 1
```

### **3.1 Parameters**
| Parameter | Description | Default |
|-----------|-------------|--------|
| `N` | Maximum number of matches per spec | 5 |
| `threshold` | Score target that stops the loop early | 0.90 |

### **3.2 Match Loop**

Each iteration of the loop is a self-contained match between two participants.

#### **3.2.1 Pairing**
The orchestrator sends a **GET /match/pair** request to the external ELO API. The API returns a fresh pair selected by roulette wheel based on current ELO:
```json
{
  "participant_a": "<id>",
  "participant_b": "<id>"
}
```

#### **3.2.2 Seat Carryover (i > 0 only)**
The orchestrator maintains a seat for each side (A and B) across iterations. For each seat, it stores the most recent solution and its aggregated feedback. When a new participant occupies a seat, they receive:
- The **previous occupant's solution** from the last match that seat participated in.
- The **aggregated feedback** for that solution.

This gives the new participant context on what worked and what didn't, even though they weren't the one who produced the earlier solution.

#### **3.2.3 Participation**
- **i = 0 (first match on this spec)**: The orchestrator sends the plain Spec Markdown to both participants.
- **i > 0**: The orchestrator sends the Spec Markdown **plus the seat's previous solution and aggregated feedback** to each participant.
- Each participant returns a solution (code in a code fence, plain text, etc.).

#### **3.2.4 Referee Evaluation**
For each participant, the orchestrator sends **the Spec + participant output** to each referee LLM (≥3 referees). Each referee returns a JSON object conforming to the strict schema (see §4). The orchestrator validates each response against the schema; invalid responses are discarded or retried.

#### **3.2.5 Aggregation**
For each participant:
1. Compute the **median** of the referees' per‑aspect `score` values.
2. Compute the `final_score` as the **median** of the median aspect scores.
3. Collect all `rationale` strings for each aspect into an array (ordered by referee submission).
4. Collect all `recommendation` strings for each aspect into an array (ordered).
5. Build aggregated **feedback JSON** (see §4.2).

The orchestrator stores the solution and its aggregated feedback in the participant's seat for potential carryover to the next iteration.

#### **3.2.6 Outcome & ELO Update**
1. The orchestrator determines the match result:
   - **Draw**: `abs`(`final_score_a` - `final_score_b`) < `epsilon`  (default: `epsilon` = 0.05).
   - **A wins**: `final_score_a` > `final_score_b` by more than epsilon.
   - **B wins**: `final_score_b` > `final_score_a` by more than epsilon.
2. The orchestrator sends a **POST /match/result** to the external ELO API:
   ```json
   {
     "participant_a": "<id>",
     "participant_b": "<id>",
     "result": "a" | "b" | "draw"
   }
   ```
3. The ELO API updates the ratings (standard ELO or Glicko) and responds with `200 OK`.

#### **3.2.7 Loop Condition**
After the ELO update, the orchestrator checks:
- If `max(final_score_a, final_score_b) >= threshold` → **exit loop** (spec mastered).
- If `i == N - 1` → **exit loop** (max matches reached; spec not mastered).
- Otherwise → `i += 1` and continue.

### **3.3 Post-Loop**
When the loop exits, the orchestrator reports to the user:
- Which participants reached the threshold (if any).
- The history of matches, solutions, and ELO changes.
- The user may inspect solutions, revise the spec, lower the threshold, or stop.

All matches for previous specs remain in the ELO history, so participants carry their ratings forward to the next spec.

## 4. **JSON Schemas**

### **4.1 Referee Output Schema (per referee)**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RefereeEvaluation",
  "type": "object",
  "required": ["scores"],
  "properties": {
    "scores": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["aspect", "score", "rationale", "recommendation"],
        "properties": {
          "aspect": { "type": "string" },
          "score": { "type": "number", "minimum": 0, "maximum": 1 },
          "rationale": { "type": "string" },
          "recommendation": { "type": "string" }
        }
      },
      "minItems": 1
    }
  }
}
```
- `score` must be formatted to 2 decimal places (`%.2f`).
- `rationale`: Prose explanation justifying the score.
- `recommendation`: Prose suggestion for improvement.

### **4.2 Aggregated Feedback JSON (sent to participant)**
```json
{
  "match_id": "uuid",
  "match_index": 2,
  "final_score": 0.78,
  "scores": [
    {
      "aspect": "functional_correctness",
      "score": 0.83,
      "rationales": ["Ref 1: ...", "Ref 2: ..."],
      "recommendations": ["Ref 1: ...", "Ref 2: ..."]
    }
  ]
}
```
- `final_score`: median of all aspect medians (rounded to 2 decimal places) calculated by the orchestrator.
- Per‑aspect `score`: median of referee scores for that aspect.
- `rationales` and `recommendations`: arrays of strings, in referee submission order.
- The next participant in that seat (A or B) receives this feedback JSON along with the Spec in the next match iteration.

### **4.3 ELO API Exchange Schemas**

**GET /match/pair response:**
```json
{
  "participant_a": "<id>",
  "participant_b": "<id>"
}
```

**POST /match/result request body:**
```json
{
 "participant_a": "<id>",
 "participant_b": "<id>",
 "result": "a" | "b" | "draw"
}
```

**POST /match/result response:** `200 OK` (or error with message).

## 5. **Error Handling & Edge Cases**

| Scenario | Orchestrator Action |
|----------|---------------------|
| External ELO API unreachable | Retry up to 3 times with exponential backoff. If still fails, log error and continue match. |
| Only one participant available in pool | Ask for a new pairing. Retry up to 3 times. If still fails, log the error, ask the single participant to solve the task, and skip the ELO update. |
| Referee JSON fails schema validation | Discard that referee’s response. If fewer than 3 valid responses remain, request another referee. |
| Participant fails to produce output after N retries (e.g., timeout) | Assign a default `final_score` of 0.0 for that match. |
| Participant outputs invalid/malformed format (e.g., no code block) | Orchestrator may attempt to parse leniently, or assign 0.0. Define strict parsing rules. |
| Match results are equal (tie) or `final_score` difference is within a small epsilon (e.g., 0.05) | ELO treats as draw: both get appropriate rating change. Orchestrator sends `"result": "draw"` to ELO API. |
| Spec is missing required sections | Reject spec before starting match. Validator in orchestrator. |

## 6. **Implementation Roadmap**

### **Phase 1 – Core Orchestrator & Validation**
- [ ] Implement **Spec parser** that extracts `Context`, `Task`, `Evaluation Criteria` from Markdown.
- [ ] Implement **referee JSON schema validator** (use `jsonschema` library).
- [ ] Implement **median aggregation** logic.
- [ ] Build **basic orchestrator** able to run a single match with fixed participant IDs.

### **Phase 2 – LLM Integrations**
- [ ] **Participant wrapper**: Call any LLM API, pass Spec, receive output.
- [ ] **Referee wrapper**: Call any LLM API, pass Spec + participant output, parse returned JSON.
- [ ] **Retry logic** for LLM failures.

### **Phase 3 – ELO API**
- [ ] Build **external ELO service** (minimal: FastAPI/Express + SQLite or in‑memory).
- [ ] Implement **roulette‑wheel selection**.
- [ ] Implement **standard ELO update** (K‑factor configurable).
- [ ] Implement `/match/pair` and `/match/result` endpoints.

### **Phase 4 – Orchestrator ↔ ELO API Integration**
- [ ] Add HTTP client calls in orchestrator for pairing and result submission.
- [ ] Handle API errors.

### **Phase 5 – Feedback Carryover & Match Loop**
- [ ] Add **feedback JSON assembly** (per‑aspect medians + arrays of rationales and recommendations).
- [ ] Implement **N‑match loop** (default N=5 or configurable) with seat-based carryover.
- [ ] Ensure participant solution and feedback are stored per seat for carryover to the next match.

### **Phase 6 – Monitoring & Observability**
- [ ] Log all matches, referee responses, aggregations.
- [ ] Track ELO evolution over time.
- [ ] Dashboard (optional).

## 7. **Key Assumptions**

| Assumption | Note |
|------------|------|
| Referee LLMs can reliably return JSON in the expected format. | If not, use constrained generation (function calls, grammar). |
| Specs are unambiguous enough for both participants and referees. | Human review or automated spec validation should be added. |
| The ELO API is stateless but maintains persistence. | Can be same machine as orchestrator or separate. |
| Participants are LLMs that accept prompts and return text. | No interactive collaboration; they work independently. |
| Referee JSON `score` fields are exactly `%.2f`. | Orchestrator can round if needed. |
