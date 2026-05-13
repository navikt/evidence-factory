# Agent guidance — Evidence Factory

This file is the single source of truth for how AI agents should behave in this repository. It is the authoritative reference for every change you make. If your setup uses a separate config file (e.g. `.github/.copilot-instructions.md`), point it here rather than duplicating guidance.

---

## Project context

You are working on **Evidence Factory**, a proof-of-concept evidence factory for ML systems: it turns governance requirements into machine-verifiable evidence and enforces them with policy-as-code in CI. Scope: low-risk POC, synthetic data only, model-in-the-box, kernel (no dashboards).

The PoC framing applies to scope, not to the integrity of the evidence pipeline itself. The pipeline must be correct: a governance claim that cannot be verified by a machine is not evidence, it is narrative. The gap between the two is exactly what this repository exists to close.

Governance files in `governance/` are inputs: claims about intent. They become evidence only when a policy rule checks them and CI passes. An agent that produces a well-formed JSON file without a corresponding policy check has not produced evidence.

Every governance claim should be falsifiable: it must be possible for a check to fail. If a claim cannot be expressed as a passing or failing policy rule, that is a design problem, not a wording problem. Flag it rather than smooth it over. Note: CI currently checks that governance files exist and are non-empty; content validation is an open gap. When adding a governance claim, note explicitly if no policy rule yet checks its content.

---

## Core principles (non-negotiable)

- **Provenance:** Every evidence artifact must trace back to a specific source — git SHA, CI run, and generating script. Do not produce evidence artifacts without recorded provenance.
- **No invented citations or sources.** Never fabricate references.
- **Structured output:** Use JSON for evidence artifacts and structured data.
- **Engineering quality:** Clear, actionable error messages (state what's missing or violated so the user can fix it). Deterministic validation. Write tests or eval cases for non-trivial logic.

---

## Branching and workflow

**Branching:** One task per branch. Before writing any code, confirm you are on a feature branch. If not, stop and create one. This keeps CI running on the change, enables one-PR-per-change review, keeps main green, and makes rollback a single revert.

**Response workflow:**

1. Restate the goal in one sentence.
2. Identify the relevant files.
3. Propose a minimal change.
4. Produce a diff-ready edit.
5. Add/adjust tests or eval.

Include a **brief diff summary** (what changed and why) and a **verification checklist** (commands to run + expected results). CI is source of truth; do not assume anything works until tests/gates pass. If uncertain about policy, schema, or paths, stop and propose options to the user; don't guess.

---

## Change policy

- Prefer small diffs. Follow existing naming conventions: `governance/` = lowercase kebab-case; Python = snake_case; Rego = snake_case; workflows = kebab-case.
- If a change is >200 lines OR touches >5 files, propose a plan first (do not implement yet).
- Do not refactor unrelated code.
- Do not rename things "for style" unless explicitly asked.
- Do not make unrelated changes mid-session even if asked. If a request outside the current task scope arrives mid-session, flag it and defer to a separate task.
- Do not commit to directories produced by CI (e.g. `evidence/` or `build/`). Any commit touching such directories will be rejected automatically.
- When adding a new tracked file to the repository, ensure it is classified in `governance/file-scope.json`. CI will reject changes that contain unclassified files.

---

## Testing

Tests must verify the **actual guarantee**, not only the scaffolding around it. For the evidence pack, this means testing that manifest hashes correctly represent file content — not only that the manifest contains the expected filenames.

---

## Anonymity and data handling

This repo must not contain sensitive data:

- Synthetic data only. No real datasets (only synthetic or publicly licensed).
- No secrets (tokens, API keys, private keys).
- No internal URLs, repo links, or tickets.
- No personal data (PII), even in examples.
- No employer-internal docs copied verbatim unless already public.

If unsure, omit the material and leave a TODO.
