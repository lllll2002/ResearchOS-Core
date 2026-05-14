# team-mode.md — Design Rationale

## What team mode is

`multimodel-team` is a round-based deliberation protocol where Claude acts as a Router
and sequentially calls models to build on each other's outputs.

It is NOT a chat room. Models do not speak to each other directly.
Every output is mediated by Claude, which reads it and decides what happens next.

## How it differs from multimodel-coo

| Dimension | multimodel-coo | multimodel-team |
|---|---|---|
| Structure | Fixed linear pipeline (A→B→C→D) | Dynamic round sequence, Router-driven |
| Next speaker | Predetermined by mode (-1/-2/-3/-4) | Decided by Claude after each round |
| Rounds | One pass through the chain | 1–3 rounds, each building on the last |
| Use case | Execution, planning, bounded review | Debate, stress-test, adversarial analysis |
| Default? | Yes — default daily workflow | No — explicit opt-in only |

## When team mode is appropriate

Use `multimodel-team` only when all three conditions are true:

1. **The answer is not predetermined.** If you already know which model should do what,
   use `multimodel-coo` instead.

2. **Prior round outputs should change what happens next.** If the next speaker is fixed
   regardless of output, use a linear pipeline.

3. **The task benefits from multiple perspectives in sequence.** Examples:
   - Hypothesis: Qwen proposes, DeepSeek attacks the assumptions, Claude synthesizes
   - Architecture: DeepSeek reasons, GLM reviews for risk, Qwen proposes alternatives
   - Implementation plan: Qwen plans, GLM reviews, DeepSeek stress-tests edge cases

## What team mode is NOT for

- Ordinary planning tasks → use multimodel-coo -1 or -3
- Code execution with review gates → use multimodel-coo -2
- Simple reasoning → use multimodel-coo -3
- Anything where a linear pipeline suffices

## Opt-in requirement

Team mode only activates when the user explicitly requests it via a trigger phrase.
Claude must not route any task into team mode without user intent.
If Claude thinks team mode would be valuable, it should say so and wait for confirmation.
