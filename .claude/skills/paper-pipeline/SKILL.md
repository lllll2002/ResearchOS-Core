---
name: paper-pipeline
description: >
  Orchestrate multi-section paper writing with progress tracking, quality gates,
  citation verification, and independent review. Wraps paper-writing, citation-check,
  writing-polish, and multimodel-team into a structured pipeline with REFINE/PIVOT
  decision loops. Use when writing a full paper section-by-section, when the user says
  "write the next section", "continue writing", "paper progress", "what's left in the paper",
  or runs /paper-pipeline. Do NOT use for single ad-hoc section drafts — those go to /paper-writing.
---

# Paper Pipeline

Orchestrator for multi-section academic paper writing. This skill **never writes prose itself** — it delegates drafting to `/paper-writing`, verification to `/citation-check`, polish to `/writing-polish`, and review to `/multimodel-team`. Its job is sequencing, gating, and progress tracking.

---

## Step 0 — Locate Manuscript and Initialize

1. Find the active manuscript. Look for `manuscript.md` in the current project's `paper/` directory. Read its YAML frontmatter for:
   - `outline_source` — path to the outline file
   - `target_journal`, `deadline`, `word_count_target`
   - `framework` — section architecture name

2. If `paper/PROGRESS.md` **exists**, read it. Skip to Step 1.

3. If `paper/PROGRESS.md` **does not exist**, initialize it:
   - Read the outline file to extract all sections and subsections
   - Read `manuscript.md` to detect already-written sections (non-empty, non-placeholder content)
   - Build the Section Status table (see PROGRESS.md Spec below)
   - Mark already-written sections as `DRAFTED` with approximate word counts
   - Set `Next Action` to the first `TODO` section
   - Write `PROGRESS.md`

4. Show the current status dashboard:
   ```
   == Paper Pipeline: <title> ==
   Phase: Drafting | Deadline: <date> (<N> days)
   Progress: <done>/<total> sections | <words>/<target> words
   Pace needed: <N> words/day
   Next action: §X.Y <section name>
   ```

---

## Step 1 — Determine Next Section

- If the user specified a section (e.g., "write §2.1"): validate it exists in the outline, use it.
- If the user said "continue" / "write next" / no section specified: read `Next Action` from `PROGRESS.md`.
- Show the section briefing:
  ```
  Next: §X.Y <name> (~<N> words)
  Argument: <from outline>
  Key refs: <from outline>
  Depends on: §X.Y-1 (<status>)
  ```
- Wait for user confirmation before proceeding.

---

## Step 2 — Draft Section

Load context for the `/paper-writing` delegation:

1. **Outline context**: Read the outline file's entry for this section — argument, key refs, subsections, word budget.
2. **Prior sections**: Read all already-written sections from `manuscript.md` for continuity.
3. **Workspace papers**: Search the project's ScholarAIO workspace for key refs:
   ```bash
   scholaraio ws search <ws> "<section keywords>"
   ```
4. **Delegate to `/paper-writing`**: Pass section spec, workspace name, outline argument, key refs, and continuity context. The skill drafts the section.
5. **Insert result** into `manuscript.md` at the corresponding `<!-- WRITE HERE -->` placeholder.
6. **Append** to the Writing Log table at the bottom of `manuscript.md`.

---

## Step 3 — Quality Gates

Run five automatic checks on the newly drafted section. Present results as a gate report.

### Gate 1: Word Count
- Count words in the new section.
- Compare against the word budget from the outline.
- **PASS** if within -30% to +20% of budget.
- **WARN** otherwise, with specific count and budget.

### Gate 2: Structure
- Check that the section contains the structural elements specified in the outline:
  - Are the key refs cited? (search for author names in the text)
  - Do expected subsections (e.g., 2.1.1, 2.1.2) exist?
  - Does the section's argument match the outline's `Argument:` field?
- **PASS** if all elements present.
- **WARN** with specific missing elements.

### Gate 3: Citation Density
- Count citation patterns: `(Author, Year)`, `(Author et al., Year)`, `[N]`, `\cite{}`.
- Count paragraphs (blocks separated by blank lines).
- Compute citations per paragraph.
- **PASS** if >= 1.5 citations/paragraph for body sections.
- **WARN** if below threshold or if any `[CITATION NEEDED]` placeholder exists.

### Gate 4: AI Pattern Scan
- Scan for common AI-generated phrases:
  - "it is worth noting", "it is important to note"
  - "has garnered significant attention", "in recent years"
  - "a plethora of", "a myriad of"
  - "paving the way", "shedding light on"
  - "plays a crucial/pivotal/vital role"
  - "the landscape of", "the realm of"
  - "has emerged as a promising"
  - "delve into", "delves into"
  - "underscores the importance"
- **PASS** if zero matches.
- **WARN** with count and locations.

### Gate 5: Continuity
- If a previous section exists in `manuscript.md`, check:
  - Does the new section's opening sentence reference or connect to the previous section's topic?
  - Are there terms used without introduction?
- **PASS** if logical flow detected.
- **WARN** if opening seems disconnected.

### Gate Report Format
```
== Quality Gate Report: §X.Y <name> ==
[PASS] Word count: <N> (budget: ~<M>, <+/-P%>)
[WARN] Structure: Missing key ref — Karpowicz 2025
[PASS] Citation density: 3.2/paragraph
[PASS] No AI patterns detected
[PASS] Continuity: connects to §X.Y-1

Decision point: PROCEED to citation check, or REVISE?
```

**REVISE loop**: If the user chooses REVISE, go back to Step 2 with gate feedback appended to the drafting context ("Previous draft had these issues: ..."). The gate report informs the revision.

---

## Step 4 — Citation Verification

Delegate to `/citation-check`:

1. Extract all citations from the newly written section.
2. Verify each against ScholarAIO local database.
3. Present the citation report with statuses: VERIFIED / METADATA MISMATCH / NOT IN LIBRARY / SUSPICIOUS.

**Decision point**: If issues found, ask "FIX citations or PROCEED with warnings?"
- FIX: Search ScholarAIO for correct papers, propose replacements, user approves, update text.
- PROCEED: Log warnings in PROGRESS.md Notes column.

---

## Step 5 — Update Progress

1. **Update `PROGRESS.md`**:
   - Section status: `TODO` -> `DRAFTED` (or `GATE_PASSED` / `CITED` depending on how far the pipeline ran)
   - Word count for this section
   - Quality Gate and Citation Check columns: `PASS` / `WARN(<N>)` / `--`
   - Recalculate dashboard metrics (total words, sections complete, pace needed)
   - Set `Next Action` to the next `TODO` section in order

2. **Show updated dashboard**:
   ```
   == Progress: <done>/<total> sections ==
   Words: <current> / <target> (<P%>)
   Days remaining: <N>
   Pace needed: <M> words/day
   Next: §X.Y <name>
   ```

---

## Step 6 — Section-Group Review (at boundaries)

**When to trigger**: After ALL subsections of a top-level section are `DRAFTED` or better (e.g., §2.1 through §2.5 + Box 2 + Table 2 are all done).

1. Detect completion: scan PROGRESS.md for the top-level section group.
2. If complete, offer review:
   ```
   Section 2 complete (~2500 words, 5 subsections + 1 Box + 1 Table).
   Trigger independent review? [yes / skip / later]
   ```
3. **If yes**: Invoke `/multimodel-team` with a 2-round configuration:
   - **Round 1 (Qwen)**: Structure and coverage analysis. Does the section achieve the argument stated in the outline? Are there gaps, redundancies, or unsupported claims?
   - **Round 2 (DeepSeek)**: Adversarial critique. Are there overclaims? Missing counterarguments? Logical fallacies? Does the evidence actually support what the text says?
   - GLM gate review only if Round 1 or 2 flag serious structural issues.
4. Save review output to `paper/reviews/section-N-review.md`.
5. Present review summary. **Decision point**: ACCEPT or REVISE.
   - ACCEPT: Update status to `REVIEWED`.
   - REVISE: Log the revision reason in Decision Log, go back to Step 2 for affected subsection(s) with review feedback.
6. **If skip**: Continue to next section group.
7. **If later**: Mark `REVIEW_PENDING` in PROGRESS.md, continue.

---

## Step 7 — Polish (user-triggered or pre-deadline)

Triggered by explicit user request ("polish §2") or as final step before submission.

1. Delegate to `/writing-polish` with target journal style.
2. Replace section text in `manuscript.md`.
3. Update PROGRESS.md status to `POLISHED` -> `DONE`.

---

## Command Routing

| User says | Steps executed |
|-----------|---------------|
| `/paper-pipeline` or "paper status" or "where am I" | Step 0 only (show dashboard) |
| "write §X.Y" or "write next" or "continue writing" | Steps 0-5 (full single-section pipeline) |
| "gate check §X.Y" | Steps 3 only (quality gates on existing draft) |
| "citation check §X.Y" | Step 4 only |
| "review §N" or "review Section N" | Step 6 only |
| "polish §X.Y" or "polish Section N" | Step 7 only |

---

## PROGRESS.md Spec

```markdown
---
manuscript: <relative path to manuscript.md>
outline: <relative path to outline file>
target_journal: <journal name>
deadline: <YYYY-MM-DD>
word_target: <number>
created: <YYYY-MM-DD>
last_updated: <YYYY-MM-DD>
---

# Paper Progress Tracker

## Dashboard

| Metric | Value |
|--------|-------|
| Phase | Drafting / Reviewing / Polishing |
| Sections complete | N / M |
| Words written | ~N |
| Words remaining | ~N |
| Days to deadline | N |
| Words/day needed | ~N |

## Section Status

| Section | Status | Words | Gate | Cited | Review | Notes |
|---------|--------|-------|------|-------|--------|-------|
| §1.1 ... | DRAFTED | ~380 | -- | -- | -- | |
| §1.2 ... | TODO | 0 | -- | -- | -- | |
...

## Status Legend

TODO -> DRAFTED -> GATE_PASSED -> CITED -> REVIEWED -> POLISHED -> DONE

## Decision Log

| Date | Section | Decision | Rationale |
|------|---------|----------|-----------|
| ... | ... | ... | ... |

## Next Action

<description of next section to write>
```

---

## Quality Thresholds

| Check | PASS | WARN |
|-------|------|------|
| Word count | -30% to +20% of budget | Outside range |
| Key refs | All key refs cited | Any missing |
| Citation density | >= 1.5 / paragraph | Below threshold |
| AI patterns | 0 matches | Any match |
| Continuity | Opening connects to prior | Disconnected |

---

## Generality

This skill works for any paper that has:
1. A `manuscript.md` with YAML frontmatter including `outline_source`
2. An outline file with section arguments and key refs
3. A ScholarAIO workspace with relevant papers

PROGRESS.md is auto-initialized from the outline — not hardcoded to any specific paper.
