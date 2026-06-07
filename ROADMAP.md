# **Common Task Framework (CTF) – System Design & Roadmap**

## 1. **Purpose**
The Common Task Framework evaluates and ranks LLM-based software/data analysis agents by pitting them against each other in structured tasks. It is inspired by BDD testing and uses a multi-LLM pipeline: **Spec → Participant → Referee → Orchestrator → ELO ranking**.

---

## 2. **Core Components**

| Component | Role | Implementation |
|-----------|------|----------------|
| **Spec** | A structured Markdown document describing a task. | Human-written or auto-generated. Contains required sections: `# Specification`, `## Context`, `## Task`, `## Acceptance Criteria`. Optional sections allowed. |
| **Participant LLM** | An LLM that receives the Spec (and later feedback) and produces a solution. | Any LLM, called via API. Exactly two per match, selected from a pool via roulette wheel (probability ∝ ELO). |
| **Referee LLM** | An LLM that evaluates a participant’s output against the Spec. Returns JSON with numeric scores and prose explanations. | At least three per match. Each referee independently produces a `final_score` and per‑aspect scores. |
| **Orchestrator** | A deterministic program that coordinates the flow: validates inputs, sends prompts, aggregates referee scores, manages match outcomes, and communicates with the external ELO API. | No LLM; pure logic (Python/Node/Go). |
| **External ELO API** | A separate service that maintains participant ELO ratings, selects two participants per match (roulette wheel), and updates ratings after each match. | Web service (REST or gRPC). |

---

## 3. **End-to-End Workflow**

### **3.1 Match Setup**
1. The orchestrator sends a **GET /match/pair** request to the external ELO API.
2. The API returns a JSON object with `{ "participant_a": "<id>", "participant_b": "<id>" }` selected by roulette wheel based on current ELO.
3. The orchestrator loads the **Spec Markdown** (could be from a file or database).

### **3.2 First Attempt**
1. **Orchestrator → Participant A & B**: Sends the **plain Spec Markdown** as the prompt.
2. **Participant A & B**: Return a solution (e.g., code in a code fence or plain text).
3. **Orchestrator**: Stores both solutions.

### **3.3 Referee Evaluation**
1. For each participant, the orchestrator sends **the Spec + participant output** to each referee LLM (≥3 referees).
2. Each referee returns a **JSON object** conforming to the strict schema (see §4).
3. Orchestrator **validates each referee JSON** against the schema. Invalid responses are discarded or retried.

### **3.4 Aggregation by Orchestrator**
1. Compute the **median** of all referees' `final_score` for the participant.
2. Compute the **median** of all referees' per‑aspect `score` values.
3. Collect all `why_explanation` strings for each aspect into an array (ordered by referee submission).
4. Collect all `kr_instruction` strings for each aspect into an array (ordered).
5. Build aggregated **feedback JSON** (see §5). This is **sent only to the participant** for their next attempt.

### **3.5 Iterative Improvement (optional)**
1. The orchestrator sends the **aggregated feedback JSON** (plus the original Spec, possibly refined) to each participant.
2. The participant returns a **revised solution**.
3. Steps 3.3 and 3.4 repeat for the revised solution.

### **3.6 Match Outcome & ELO Update**
1. After N attempts (usually 1–3), the orchestrator determines:
   - **Winner**: Participant with higher **median `final_score`** after the final round.
   - **Loser**: The other participant.
2. The orchestrator sends a **POST /match/result** to the external ELO API with:
   ```json
   {
     "winner_id": "<id>",
     "loser_id": "<id>",
     "scores": {
       "winner_final_median": 0.87,
       "loser_final_median": 0.72
     }
   }
   ```
   (Optional: include raw scores for advanced ELO tuning.)
3. The ELO API updates the ratings (e.g., using standard ELO with K‑factor) and responds with `200 OK`.

---

## 4. **JSON Schemas**

### **4.1 Referee Output Schema (per referee)**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RefereeEvaluation",
  "type": "object",
  "required": ["final_score", "aspect_scores"],
  "properties": {
    "final_score": { "type": "number", "minimum": 0, "maximum": 1 },
    "aspect_scores": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["aspect", "score", "why_explanation", "kr_instruction"],
        "properties": {
          "aspect": { "type": "string" },
          "score": { "type": "number", "minimum": 0, "maximum": 1 },
          "why_explanation": { "type": "string" },
          "kr_instruction": { "type": "string" }
        }
      },
      "minItems": 1
    }
  }
}
```
- `score` and `final_score` must be formatted to 2 decimal places (`%.2f`).  
- `why_explanation`: Prose reasoning for the score.  
- `kr_instruction`: Prose recommendation for improvement.

### **4.2 Aggregated Feedback JSON (sent to participant)**
```json
{
  "match_id": "uuid",
  "final_score": 0.78,
  "aspect_scores": [
    {
      "aspect": "functional_correctness",
      "score": 0.83,
      "why_explanations": ["Ref 1: ...", "Ref 2: ..."],
      "kr_instructions": ["Ref 1: ...", "Ref 2: ..."]
    }
  ]
}
```
- `final_score`: median of referee `final_score` values.  
- Per‑aspect `score`: median of referee scores for that aspect.  
- `why_explanations` and `kr_instructions`: arrays of strings, in referee submission order.  
- The participant receives **only this match’s feedback**, not history.

### **4.3 ELO API Exchange Schemas**

**GET /match/pair response:**
```json
{
  "participant_a": "p123",
  "participant_b": "p456"
}
```

**POST /match/result request body:**
```json
{
  "winner_id": "p123",
  "loser_id": "p456",
  "scores": {
    "winner_final_median": 0.87,
    "loser_final_median": 0.72
  }
}
```

**POST /match/result response:** `200 OK` (or error with message).

---

## 5. **Error Handling & Edge Cases**

| Scenario | Orchestrator Action |
|----------|---------------------|
| External ELO API unreachable | Retry up to 3 times with exponential backoff. If still fails, abort match and log error. |
| Only one participant available in pool | Wait for another to be added (or skip match with a warning). |
| Referee JSON fails schema validation | Discard that referee’s response. If fewer than 3 valid responses remain, request another referee. |
| Participant fails to produce output after N retries (e.g., timeout) | Assign a default `final_score` of 0.0 for that attempt. |
| Participant outputs invalid/malformed format (e.g., no code block) | Orchestrator may attempt to parse leniently, or assign 0.0. Define strict parsing rules. |
| Match results are equal (tie) | ELO treats as draw: both get appropriate rating change. Orchestrator sends `winner_id` and `loser_id` equal? Better: include a `tie` boolean. |
| Spec is missing required sections | Reject spec before starting match. Validator in orchestrator. |

---

## 6. **Implementation Roadmap**

### **Phase 1 – Core Orchestrator & Validation**
- [ ] Implement **Spec parser** that extracts `Context`, `Task`, `Acceptance Criteria` from Markdown.
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

### **Phase 5 – Iterative Improvement Loop**
- [ ] Add **feedback JSON assembly** (per‑aspect medians + arrays of explanations).
- [ ] Implement **N‑attempt loop** (default N=2 or configurable).
- [ ] Ensure participant output is stored and re‑evaluated each round.

### **Phase 6 – Monitoring & Observability**
- [ ] Log all matches, referee responses, aggregations.
- [ ] Track ELO evolution over time.
- [ ] Dashboard (optional).

---

## 7. **Key Assumptions**

| Assumption | Note |
|------------|------|
| Referee LLMs can reliably return JSON in the expected format. | If not, use constrained generation (function calls, grammar). |
| Specs are unambiguous enough for both participants and referees. | Human review or automated spec validation should be added. |
| The ELO API is stateless but maintains persistence. | Can be same machine as orchestrator or separate. |
| Participants are LLMs that accept prompts and return text. | No interactive collaboration; they work independently. |
| Referee JSON `score` fields are exactly `%.2f`. | Orchestrator can round if needed. |

---
