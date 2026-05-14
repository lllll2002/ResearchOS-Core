# round-protocol.md — Round Mechanics

## Round structure

Each round has exactly five steps. All five must complete for the round to be valid.

```
1. ASSIGN   — Router (Claude) selects the speaker and states the reason
2. PROMPT   — Router writes the round-specific prompt, referencing prior artifacts
3. EXECUTE  — Designated model runs and produces output
4. ARTIFACT — Output is written to the designated stage file
5. REVIEW   — Router reads the artifact and makes a routing decision
```

If step 4 fails (no artifact written, empty file, or model error), the round is invalid.
Claude must stop, report the failure, and ask the user whether to retry or abandon.

## Round numbering

Rounds are numbered from 1. The round limit counts only completed valid rounds.
A failed round that is retried does not count toward the limit.

## Round limit

Default: 3 rounds maximum.
The user may reduce this in the proposal (e.g. "max 2 rounds").
The limit may not be raised above 3 without explicit user instruction in the session.

When the limit is reached, Claude must:
1. Note "Round limit reached" in the completion report
2. Proceed immediately to synthesis with whatever artifacts exist
3. Not propose additional rounds

## Router reasoning (required)

Before each round, Claude must state (in a single sentence or less):
- Why this speaker was chosen over others
- What question or gap this round is meant to address

This is logged in the round header of the stage file and in the event record.

## Artifact naming

Primary artifact path per speaker:

| Speaker  | Primary artifact             | Round-suffix variant         |
|----------|------------------------------|------------------------------|
| Qwen     | 20_reasoning.md              | 20_reasoning_r{N}.md         |
| DeepSeek | 20_reasoning.md              | 20_reasoning_r{N}.md         |
| GLM      | 40_review.md                 | 40_review_r{N}.md            |
| Codex    | 30_implementation.md         | 30_implementation_r{N}.md    |

If a speaker runs in multiple rounds, use the round-suffix variant.
Before synthesis, copy the final round's artifact as the canonical file (without suffix).

## Round header format

Each artifact must begin with:

```
# [Round N] <SpeakerModel> — <date>
Router reasoning: <why this speaker, what this round addresses>
Prior artifact(s) read: <list or "none">
```

This makes the artifact self-documenting and traceable.

## What counts as a valid artifact

- File exists and is non-empty
- Contains the round header (see above)
- Contains substantive content (not just "I have reviewed..." with no content)
- Written directly to disk — not copied from console output

## Between rounds

After each valid round, Router:
1. Reads the artifact
2. Determines: Does the next round speaker change based on what was produced?
3. States the routing decision to the user before proceeding
4. Waits if the user has set interactive mode (default: continue unless user interjects)
