# AGENTS.md

Guidance for AI agents (and humans) working in this repository.

## Context

This repository is a case study / take-home for a **Senior Data Engineer** role at **Ebury** (cross-border payments / FX / lending fintech). Details of the brief, deliverable, and stack are filled in as they are confirmed.

## Rules

* Every change must have a plan which is stored in the `ai-plans/` directory.
* Use the provided template ([`ai-plans/TEMPLATE.md`](ai-plans/TEMPLATE.md)) for plan creation.
* The plan must outline the steps to be taken, the expected outcomes, and the verification methods.
* If a plan name is not provided, infer one (short, kebab-case, descriptive — e.g. `fx-rate-ingestion`).
* The plan must outline the unit tests that will be written, including edge cases.
* Any modifications to the plan must include an update record in the plan's Change Log.

## Workflow

1. Before writing any code, create a plan file in `ai-plans/` from the template.
2. Get the plan reviewed / agreed before implementation.
3. Implement against the plan; keep steps and outcomes in sync with reality.
4. If scope or approach changes, update the plan and add a Change Log entry (do not silently diverge).
5. Write the unit tests defined in the plan, including the edge cases, and verify via the plan's verification methods.

## Conventions

_TBD — fill in once stack is chosen (language, formatter/linter, test runner, directory layout, naming)._
