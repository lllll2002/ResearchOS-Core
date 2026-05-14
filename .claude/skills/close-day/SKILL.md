---
name: close-day
description: End-of-day review. Scans today's vault changes, summarizes completion, logs decisions, archives the daily plan. Trigger on "close day", "wrap up", "end of day", "review today", or /close-day directly. Also trigger proactively if user says "that's enough for today."
argument-hint: "[optional notes]"
allowed-tools: Read, Write, Edit, Bash, Glob
---

# Minimum Set (5 min -- always complete these)

These 3 items guarantee tomorrow's session can recover context quickly, even if nothing else runs:

1. Mark completed tasks as `[x]` in `today.md`; leave incomplete tasks as `[ ]`
2. Add one sentence to the "Daily Notes" block in `today.md`: what was the most important conclusion or progress today
3. Update `AI_active_context.md`: modify task statuses in the "Immediate Blockers" table and write key new findings into the top focus section

**After these 3 items, you may exit.** If time permits, continue with the full flow below.

---

# Full Review Flow (15 min -- when time allows)

The goal is to honestly record "what actually happened today," not to polish progress. Incomplete tasks must be logged so tomorrow's plan can be better.

1. Read `01_Planning/today.md`, extract the planned task list and items marked `[x]`.

2. Scan `02_Research_Projects/`, `03_Theoretical_Work/`, `04_Learning/` for files modified or created today -- use these as objective evidence of actual output.

3. Compare plan vs. actual output:
   - Skip lines prefixed with `[HANDOFF]` -- these are recovery metadata, not checkable tasks
   - Label each real task's status ([DONE] completed / [MISS] incomplete / [PART] partial)
   - If unplanned files were modified, note what extra work was done
   - Calculate completion rate (completed / total, excluding `[HANDOFF]` lines from both counts)

4. Fill in the "Wrap-up" block at the bottom of `today.md`: completion rate, tomorrow's priorities, reasons for incomplete items.

5. Append conclusions with lasting impact to `01_Planning/process_notes.md`:
   - Experiment decisions (e.g., discarding a cell batch, changing parameters)
   - Research direction adjustments
   - Important tool/method discoveries
   - Conclusions from this session worth preserving cross-session
   - Skip pure execution details (information derivable from the code or files themselves)

5.5. **Wiki Auto-Writeback** (knowledge compilation):
   - Read today's new entries appended to `process_notes.md`
   - For each entry tagged "**key decision**", "**core conclusion**", or "**long-term valid**":
     - Determine which project it belongs to (Phase Separation / Biocomputing Review / MEA Chip / other)
     - Open that project's wiki spine (`claims.md` / `index.md` / `validated-tests.md`)
     - If the conclusion changes a claim's status or adds new evidence -> update wiki
     - If the conclusion is a new concept/method/finding -> append to wiki Open Questions or relevant page
   - Do not create new wiki pages -- only update existing ones
   - If no entries are tagged "long-term valid," skip this step

5.6. **Inbox Triage** (read `01_Planning/inbox.md`, route each item):
   - Important conclusions/decisions -> append to `process_notes.md`
   - Experiment ideas -> append to relevant protocol or `EXP-Data_Inventory.md`
   - Literature connections/new findings -> append to `literature_map/06_cross_connections.md`
   - No value or already processed -> delete
   - Clear `inbox.md` body (keep template comment lines intact)

5.7. **Memory Consolidation** (Dream-inspired, L4 maintenance):
   - Read today's new entries in `process_notes.md` (from step 5)
   - For each entry, determine if it contains information that should persist in `memory/`:
     - User workflow preferences or tool usage patterns -> vault-level `memory/` files
     - Project-specific experiment decisions or hardware state -> `<project>/memory/` files
     - Stale or superseded facts already in memory -> flag for update or removal
   - Before writing: check if a relevant memory file already exists (avoid duplicates)
   - Propose changes to the user in the close-day summary (e.g., "Suggest adding X to memory/reference_Y.md")
   - Only write after user confirmation -- no silent memory writes
   - If no entries qualify, skip this step
   - Goal: keep memory files current without requiring the user to explicitly say "remember this"

6.2. **Task Trace Recording** (L4 Operation Patterns):
   - Review today's completed tasks (infer from `[x]` items in today.md and actual file modifications)
   - Apply write/skip rules from `01_Planning/lifecycle_rules.md` section 2
   - Filename format: `{YYYY-MM-DD}_{project}_{short-description}.md`
   - Use the schema in `memory/operations/_TEMPLATE.md`
   - If `memory/operations/` already has >=50 files, delete the oldest before writing

6.3. **Skill Candidate Check** (Auto-Distillation):
   - Apply generation rules from `01_Planning/lifecycle_rules.md` section 3
   - List new candidates in the close-day summary and ask user whether to approve
   - If no matches pass all criteria, skip this step

6.5. **Handoff Card Archival** (L4 Session State):
   - Scan `memory/handoffs/*.md` (exclude archive/)
   - Apply transition rules from `01_Planning/lifecycle_rules.md` section 1
   - For each active card, determine project status from today.md `[x]` items AND file modification evidence:
     - Completed today --> set `completed`, move to `archive/`
     - Progress but not done --> keep `interrupted`, update card fields
     - Not touched --> leave unchanged
   - For projects worked on today with no card and unfinished tasks, write new card (schema in `/handoff` skill)
   - Set trigger field to "close-day"

7. Archive `today.md` as `01_Planning/archive/YYYY-MM-DD.md` (use today's actual date).

8. Ask the user if they have any thoughts or reflections to add to the review log.

---

## Self-Improving Loop (nightly evolution)

9. **Growth Curve Calculation**:
   - Read today's completion rate (computed in step 3), append a row to `06_Growth_Profiles/learning_velocity.md`.
   - If completion rate < 60%, add `[WARN] auto-reduce 20%` annotation to remaining tasks in `01_Planning/weekly_goals.md` with reason.
   - If completion rate > 90%, add `[GOOD] may increase 15%` annotation.

10. **Hybrid Habit Capture**:

   **10-A Deep Review (Claude main model, current session)**:
   - Read `01_Planning/today.md` and `01_Planning/process_notes.md`, combine with today's conversation, generate a "daily habit summary" in this format:
     ```
     DATE: YYYY-MM-DD
     FPGA: <any code style corrections today, one-line description, or "none">
     READING: <literature dimensions pursued today, or "none">
     ENGLISH: <errors or highlights in English conversation today, or "none">
     RESEARCH: <research insights or derivation difficulties, or "none">
     ```
   - Save this summary text to a temporary variable `HABIT_SUMMARY`.
   - Append to the corresponding `06_Growth_Profiles/` files.

   **10-B Lightweight Extraction (local model -> ChromaDB, via Bash)**:
   - Run the following Bash script to send `HABIT_SUMMARY` to the local model for structured extraction, then store in ChromaDB:

   ```bash
   #!/usr/bin/env bash
   # close-day habit capture: local model extraction + ChromaDB storage
   # Before running, assign the HABIT_SUMMARY generated above to the variable below

   HABIT_SUMMARY="<paste 10-A generated summary>"
   TODAY=$(date +%Y-%m-%d)

   # Step 1: Call local Qwen (Ollama) to extract up to 3 structured habits
   # If Ollama is not running, this will fail fast without blocking the main flow
   HABITS=$(curl -s --max-time 30 --noproxy localhost,127.0.0.1 http://localhost:11434/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d "{
       \"model\": \"qwen3:8b\",
       \"messages\": [{
         \"role\": \"user\",
         \"content\": \"/no_think Extract up to 3 long-term personal habits or preferences from the log below. Output each as JSON with fields: content, memory_type (english_errors/fpga_habits/research_insights/general), tags. Output only a JSON array, nothing else.\n\n${HABIT_SUMMARY}\"
       }],
       \"temperature\": 0.1,
       \"options\": {\"num_predict\": 512}
     }" | python3 -c "
   import sys, json
   resp = json.load(sys.stdin)
   print(resp['choices'][0]['message']['content'])
   " 2>/dev/null)

   # Step 2: If local model call failed, skip ChromaDB storage (no error)
   if [ -z "$HABITS" ]; then
     echo "[close-day] Local model unavailable, skipping ChromaDB storage (deep review completed normally)"
     exit 0
   fi

   # Step 3: Parse JSON and store each entry in ChromaDB via MCP
   echo "$HABITS" | python3 - <<'PYEOF'
   import sys, json, subprocess

   habits = json.loads(sys.stdin.read())
   if not isinstance(habits, list):
       habits = [habits]

   for h in habits:
       content = h.get("content", "")
       mtype   = h.get("memory_type", "general")
       tags    = h.get("tags", "")
       if not content:
           continue
       # Store via Claude Code MCP store_memory
       result = subprocess.run(
           ["python3",
            "E:/Obsidian/.claude/mcp-servers/chroma_memory_mcp.py",
            "--store", content,
            "--type", mtype,
            "--tags", tags],
           capture_output=True, text=True
       )
       print(f"[ChromaDB] stored: {content[:60]}...")
   PYEOF
   ```

   > **Note**: The Ollama local model is an optional acceleration layer. If Ollama is not installed, step 10-A's deep review (file writes) already covers all habit recording. ChromaDB storage only enhances semantic retrieval and does not affect the main flow.

11. **Language Upgrade Assessment**:
    - Read `English_Ratio` from `06_Growth_Profiles/english_progression.md`.
    - If no grammar corrections were made in today's English conversations and the exchange was fluent, increase `English_Ratio` by 2% and add a row to the upgrade log table (date, new ratio, trigger reason).
    - If the user made notable corrections, keep the current ratio and note the error type in remarks.
