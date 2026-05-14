# gap-c-glm-block-policy.md — GLM BLOCK Confirmation Policy Decision

**Status: decision pending — no behavior change implemented yet**

## The problem

GLM BLOCK is the highest-priority stop condition and is unconditional.
When GLM issues a BLOCK verdict, the Router must halt the run, report to the user,
and ask: fix and retry, or abandon?

There is no confirmation step between GLM's BLOCK verdict and the Router acting on it.
If GLM issues a BLOCK erroneously — due to an overly conservative review rubric,
a misread artifact, or a false positive — the entire run is terminated with no recourse
short of restarting from scratch.

---

## Policy options

### Option 1 — Keep current hard stop (no change)

GLM BLOCK immediately halts the run. The Router reports the block and asks the user.

**Pros:**
- Simplest implementation — no new protocol state
- Maximally conservative — a wrong BLOCK is recoverable by restarting; a missed BLOCK is not
- Consistent with GLM's role as a gate, not an advisor
- Reduces risk of the Router second-guessing a legitimate security or correctness concern

**Cons:**
- A GLM false positive on a short or low-stakes run wastes the entire run cost
- No way to distinguish "BLOCK on a real constraint violation" from "BLOCK on a hallucination"
- The current GLM rubric has a documented false positive pattern (runner status updates)
  which was already fixed in glm_review.py; future rubric gaps may not be

---

### Option 2 — Router confirmation prompt before acting on BLOCK

When GLM issues a BLOCK, the Router displays the block reason and asks the user to
confirm before terminating. The user can confirm the block, override it, or request
a GLM re-review.

**Pros:**
- Prevents false positives from silently killing valid runs
- Gives the user visibility into *what* was blocked before the run ends
- Consistent with how high-stakes automated actions are handled elsewhere in this OS
  (e.g., init_current_task.py requires --force for overwrite)

**Cons:**
- Adds friction to every legitimate BLOCK
- If the user confirms overrides too easily, the BLOCK stop rule becomes advisory rather than hard
- Requires the Router to buffer the BLOCK verdict, which adds protocol complexity

---

### Option 3 — BLOCK becomes WARN for first occurrence, BLOCK on second

First GLM BLOCK in a run: Router reports it as a warning, allows the run to continue
to the next round. If GLM BLOCKs again on a subsequent round, treat as a hard stop.

**Pros:**
- Handles the case where GLM BLOCKs on an artifact that a later round corrects
- One chance for the protocol to self-correct without user intervention

**Cons:**
- Fundamentally changes GLM's role from a gate to a soft gate
- A genuine BLOCK (e.g., a safety issue) should not be allowed to proceed even once
- Adds stateful logic to the Router (tracking whether a BLOCK has already occurred)
- Most inconsistent with the intent of the existing stop-rule design

---

## Recommended default

**Option 1 (current behavior) with a rubric discipline note.**

Rationale:
- The false positive risk is already addressed at the rubric layer (glm_review.py system prompt).
  The right place to prevent bad BLOCKs is to write a precise review rubric, not to add a
  confirmation gate that the user may click through without reading.
- Option 2 is worth implementing once a pattern of false positives is observed in practice.
  It is not justified by the one false positive case already fixed.
- Option 3 weakens the BLOCK concept and should not be adopted.

**When to revisit:** If two or more GLM false positive BLOCKs occur on separate tasks,
re-evaluate Option 2. Track them in process_notes.md.

---

## What this note does NOT change

- `references/stop-rules.md` §1 (GLM BLOCK remains condition 1, highest priority)
- `glm_review.py` system prompt (rubric already has infrastructure exception)
- Any SKILL.md step

This note records the policy decision and the reasoning behind keeping Option 1 as default.
