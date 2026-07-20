# Framework V1 Phase 4 — Agent Pipeline

- Completed at: `2026-07-20T14:20:27.404Z`
- Scope: package/loop-driven staged generation, digest-bound human decisions, provenance redaction, release bundling, deterministic CI substitute, and live smoke.
- PRD files changed: no.
- External deployment: no.

## Implementation

- Added `DecisionReceipt` creation and validation for brief, blueprint, release, and playtest attribution checkpoints.
- Added a staged V1 agent CLI: `prepare -> approve -> continue -> approve -> continue -> approve -> bundle`.
- Enforced exact loop-package versions, Experimental brief opt-in, stale-receipt rejection, blueprint-before-scenes, and release-before-bundle.
- Kept IDs, structure, assembly, migration, and structural repair deterministic; LLM work is limited to small creative artifacts.
- Exported canonical V1 packs plus a deprecated read-only V0 projection and sanitized provenance.
- Made G5 work for arbitrary content-pack IDs and made static/Worker builders accept an explicit generated pack outside the repository package directory.
- Added a fresh investigation brief, deterministic offline tests, a redacted replay sample, and a redacted live-smoke evidence summary.

## Verification

- `python3 -m py_compile ...`: passed.
- `python3 -m unittest tests.test_framework_v1_agent tests.test_model_output_archive -v`: 10 passed.
- `python3 -m unittest discover -s tests -v`: 102 passed in 25.352 seconds.
- `python3 scripts/validate_pack.py content_packs/missing_phone/v1 --through G5`: G1–G5 passed; all three ending witnesses replayed.
- `python3 scripts/render_readme_diagrams.py`: passed; updated AI pipeline diagram visually inspected.
- Live OpenAI-compatible smoke with `night_train_archive`: reached `awaiting_release_approval`; G1–G5 passed; provider/model metadata retained without credentials; repository/workspace-path and secret-pattern scan passed.
- `git diff --check`: passed before the phase commit.

## Compatibility

- Legacy flag-style generation CLI remains available with a deprecation warning.
- No compatibility interface is removed in V1.0.
