---
name: morning-setup
description: Morning planning. Reads weekly goals, recent progress, and yesterday's archive to generate today's task list in today.md. Trigger on "start today", "morning plan", "good morning", "plan my day", or /morning-setup directly. Also consider triggering if user just asks "what should I do today."
allowed-tools: Read, Write, Edit, Glob
---

# Morning Setup Flow

Good plans come from honest context reads -- weekly goals set direction, yesterday's leftovers set priority, and combining both produces a genuinely useful daily plan.

1. Read `01_Planning/weekly_goals.md`, extract this week's core goals and remaining priorities.

2. Read the latest entries in `01_Planning/process_notes.md` to understand recent decisions and unresolved questions.

3. Check `01_Planning/archive/` for the most recent archive (yesterday's `YYYY-MM-DD.md`), extract incomplete tasks.

3.5. **Handoff Card Recovery** (L4 Session State):
   - Scan `memory/handoffs/*.md` (exclude archive/), list all cards with status: interrupted
   - Insert recovery prompts using the format in `01_Planning/lifecycle_rules.md` section 4:
     ```
     [HANDOFF] {{card.task_id}} -- {{card.task}}
       Next: {{card.next_step}}
       Entry: {{card.primary_file}}
     ```
   - Cards >14 days old get `[STALE]` prefix per lifecycle rules
   - Recovery prompts go before regular `[ ]` tasks (prioritize interrupted work)
   - These are metadata, not checkable tasks -- no `[ ]`/`[x]` syntax
   - When user starts working on a handoff card's project, set card status to `resumed` per lifecycle rules section 1

4. Overwrite `01_Planning/today.md` with a new timeline and task list:
   - Divide into time blocks (morning / afternoon / evening)
   - Label each task with its project (Phase Separation / FPGA / Theory / Literature / Experiment)
   - Carry over yesterday's incomplete tasks, mark their origin, and slot them by priority
   - Top 3 priority tasks go first, clearly visible

5. **System health check**: Read `01_Planning/AI_active_context.md` top section "System Health". If any alerts exist, mention them briefly in the plan. Do NOT spend time fixing -- just flag.

6. **Predictive scheduling rules** (apply automatically):

   **Rule 1: Deadline pressure pre-loading**
   - If any project has a deadline within 14 days (check Critical Deadlines table), push its writing/execution task to Top 1 regardless of other priorities.
   - If deadline < 7 days, mark as CRITICAL and reduce all other tasks to minimum.

   **Rule 2: Idle claim awakening**
   - Scan `AI_active_context.md` Immediate Blockers table. If any blocker has been listed for >7 days without progress, insert a reminder: "Blocker [X] has been stalled for N days -- resolve or explicitly defer?"

   **Rule 3: Context window push**
   - Check yesterday's archive for which project was actively worked on. If the same project has unfinished tasks, put them first (momentum preservation). If a different project was started, don't fight it -- follow the user's actual energy.

   **Rule 4: Completion rate adjustment**
   - Read `06_Growth_Profiles/learning_velocity.md` for recent completion rates.
   - <60% average -> reduce today's plan by 20% (fewer tasks, longer time blocks)
   - >90% average -> allow adding one stretch goal

7. Generate the plan and end with one short sentence. Do not lecture the user -- mornings are for action.
