---
name: multimodel-team-reviewer
description: >
  Review-grade multi-model literature workflow for E:\Obsidian. Use this skill when the task is a
  formal review, related work section, thesis literature review, evidence audit, or any publication-facing
  synthesis where corpus completeness, screening, DOI traceability, and evidence matrices matter.
  Trigger phrases: /multimodel-team-reviewer, use review team mode, review-grade team mode,
  publication-grade literature audit, formal review mode.
  This skill is separate from `multimodel-team`. Do not use ordinary team mode as a substitute for
  review-grade corpus construction.
---

# multimodel-team-reviewer

Separate opt-in skill for publication-grade literature work.

This skill is distinct from `multimodel-team`:

- `multimodel-team` = round-based discussion and bounded literature deliberation
- `multimodel-team-reviewer` = corpus construction + screening + evidence audit + multimodel review

Claude remains the Router. No model may self-delegate, initiate a new round, or bypass evidence artifacts.

Before proceeding, read:

- `E:/Obsidian/memory/multimodel_team_review_protocol.md`
- `E:/Obsidian/memory/multimodel_team_review_task_template.md`
- `E:/Obsidian/memory/team_role_charter.md`

---

## Step 0 - Mode Decision

Use this skill only if at least one of the following is true:

- the user wants a formal review article
- the user wants a publication-facing related work section
- the user asks for comprehensive or fair coverage
- the user asks whether all key papers have been screened
- the task requires DOI map, screening log, evidence matrix, or section-to-paper traceability

If none of the above are true, stop and use `multimodel-team` instead.

---

## Step 1 - Preflight

Run:

```bash
python "E:/Obsidian/scripts/multimodel_preflight.py"
python "E:/Obsidian/scripts/init_current_task.py" --title "placeholder" --check
```

If `current_task` is already active, do not proceed silently. Tell the user and ask whether to archive or force.

---

## Step 2 - Proposal Card

Present a proposal before execution:

```text
== multimodel-team-reviewer proposal ==

Task: <one-sentence review description>

Phase 1 - Corpus and evidence construction:
  0. review-setup              -> review_scope.md
  1. corpus-build              -> corpus_master.csv
  2. doi-validate              -> doi_map.md, metadata_issues.md
  3. screening                 -> screening_log.md
  4. fulltext-priority-pass    -> fulltext_priority_list.md
  5. evidence-artifact-build   -> evidence_matrix.md, section_to_paper_map.md, gap_map.md

Phase 2 - Multimodel review:
  Round 1: Qwen      -> structure framing / coverage flags -> 20_reasoning_r1.md
  Round 2: DeepSeek  -> adversarial evidence stress-test   -> 20_reasoning_r2.md
  Round 3: GLM       -> publication gate                   -> 40_review.md
  Round 4: Codex     -> repair / scaffold                  -> 30_implementation.md
  Synthesis: Claude/Opus -> final review summary           -> 50_summary.md

Hard rules:
  - No DeepSeek or GLM review before corpus artifacts exist
  - Core claims require DOI traceability whenever possible
  - Thin-evidence sections must be labeled explicitly
  - Full-text priority applies to anchor and contradictory papers

Confirm this review workflow, or adjust.
```

Wait for explicit confirmation.

---

## Step 3 - Initialize

After confirmation:

```bash
python "E:/Obsidian/scripts/init_current_task.py" --title "<task-title>" [--force if approved]
```

Write the full task description into `00_request.md`.

Also create or prepare the following target artifacts:

- `review_scope.md`
- `corpus_master.csv`
- `doi_map.md`
- `metadata_issues.md`
- `screening_log.md`
- `fulltext_priority_list.md`
- `evidence_matrix.md`
- `section_to_paper_map.md`
- `gap_map.md`

Use the field definitions in `E:/Obsidian/memory/multimodel_team_review_task_template.md`.

---

## Step 4 - Phase 1: Corpus and Evidence Layer

This phase is mandatory.

### 4.1 Review setup

Define:

- review question
- scope boundaries
- date window
- inclusion criteria
- exclusion criteria
- expected deliverable

Write to `review_scope.md`.

### 4.2 Corpus build

Build the candidate set from:

- ScholarAIO
- existing vault paper lists
- user-provided paper lists
- known anchor papers
- citation chaining if needed

Write normalized records to `corpus_master.csv`.

### 4.3 DOI and metadata validation

Classify papers as:

- DOI confirmed
- preprint only
- metadata incomplete
- duplicate
- excluded

Write to `doi_map.md` and `metadata_issues.md`.

### 4.4 Screening

Perform at minimum:

- title screening
- abstract screening
- full-text priority tagging

Every exclusion must have a reason in `screening_log.md`.

### 4.5 Full-text priority pass

Prioritize full-text review for:

- anchor papers
- papers supporting core claims
- contradictory papers
- methods-defining papers
- novelty or consensus claims

Write to `fulltext_priority_list.md`.

### 4.6 Evidence artifact build

Build:

- `evidence_matrix.md`
- `section_to_paper_map.md`
- `gap_map.md`

Do not start Phase 2 until these artifacts exist and are non-trivial.

---

## Step 5 - Phase 1 Exit Check

Before any multimodel round, verify that all required artifacts exist:

- `review_scope.md`
- `corpus_master.csv`
- `doi_map.md`
- `screening_log.md`
- `fulltext_priority_list.md`
- `evidence_matrix.md`
- `section_to_paper_map.md`
- `gap_map.md`

If any are missing, stop and repair Phase 1 first.

---

## Step 6 - Phase 2: Multimodel Review

### Round 1 - Qwen

Task:

- frame the review structure from the evidence artifacts
- identify category imbalance
- identify thin sections
- avoid claiming completeness beyond the corpus

Output:

- `20_reasoning_r1.md`

### Round 2 - DeepSeek

Task:

- attack unsupported synthesis
- identify evidence hierarchy errors
- challenge overclaim
- identify sections that must be downgraded to gaps

Output:

- `20_reasoning_r2.md`

### Round 3 - GLM

Task:

- issue PASS / CONDITIONAL / BLOCK
- audit DOI compliance
- audit claim-to-evidence traceability
- reject speculative claims presented as established findings

Output:

- `40_review.md`

### Round 4 - Codex

Task:

- repair matrices and maps
- scaffold section drafts
- preserve unresolved gaps explicitly

Output:

- `30_implementation.md`

### Synthesis

Claude or Opus synthesizes:

- what is established
- what is weakly supported
- what remains a gap
- whether the review is publication-ready

Write:

- `50_summary.md`

---

## Step 7 - Hard Boundaries

- Do not collapse this skill back into ordinary `multimodel-team`
- Do not skip corpus construction because "the models can infer it"
- Do not treat multi-model disagreement as evidence coverage
- Do not let GLM review before the evidence layer is built
- Do not let a thin section silently remain as if it were a real synthesis

---

## Step 8 - Completion Report

Use this final block:

```text
== multimodel-team-reviewer completed ==

Phase 1 artifacts:
  - review_scope.md
  - corpus_master.csv
  - doi_map.md
  - screening_log.md
  - fulltext_priority_list.md
  - evidence_matrix.md
  - section_to_paper_map.md
  - gap_map.md

Phase 2 artifacts:
  - 20_reasoning_r1.md
  - 20_reasoning_r2.md
  - 40_review.md
  - 30_implementation.md
  - 50_summary.md

Review status:
  - corpus coverage: <strong / adequate / thin / uncertain>
  - DOI traceability: <strong / mixed / weak>
  - publication readiness: <PASS / CONDITIONAL / BLOCK>
```

---

## Reference

This skill depends on:

- `E:/Obsidian/memory/multimodel_team_review_protocol.md`
- `E:/Obsidian/memory/multimodel_team_review_task_template.md`
- `E:/Obsidian/memory/team_role_charter.md`
