# Evidence Factory: make governance compile.

This repository is a proof-of-concept evidence factory for ML systems: it turns governance requirements into cryptographically verifiable evidence and enforces them with policy-as-code in CI. If the governance requirements aren't met, the build fails. Retroactive falsification is detectable.  

**The evidence produced by this PoC does *not* by itself constitute full legal compliance.**

**[⇝ Check out the wiki ⇜](../../wiki)** for more about this project's architecture, design principles, regulatory mapping, and open problems.

This project uses a four-layer model to label the depth of evidence:

- L1 presence: The evidence exists.
- L2 structure: The evidence is well-formed.
- L3 coherence: The claims are mutually consistent across artifacts (referential consistency, e.g. the model version in the risk assessment matches the model card).
- L4 grounded validity: The evidence stays true of the running system as the system, data, and context change. This is where the factory hands off to runtime monitoring and human review.

Check out [How we label evidence](How-we-label-evidence) for an more in-depth explanation of the L1 - L4 model and verification/grounding/validation. 

Currently the system is working primarily at **layer 1** (verification of the existence of the specified files). Layer 2 is next on the docket; 3 and 4 are open research questions. 

## Scope
 
This PoC uses a low-risk, decision-support scenario with synthetic data. The ML aspects are deliberately minimal; the governance architecture is the primary exhibit.
 
## Repository layout
 
- `src/` — training + evaluation code
- `scripts/` — evidence assembly utilities
- `governance/` — governance inputs (JSON; bundled + hashed + gated)
- `config/file-scope.json` — declarative scope map for CI routing + scope policy checks
- `policy/` — OPA/Rego policies executed by Conftest
- `.github/workflows/` — CI pipelines
- `tests/` — Python tests (pytest) for evidence assembly
- `evidence/` — generated artifacts (never hand-edited; gitignored)
- `build/` — generated model artifacts (gitignored)
## Local quickstart

Use Python 3.13 (CI and pinned deps use 3.13; see `.python-version`).

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate

# Windows:
#   .venv\Scripts\activate
pip install -r requirements.txt

python src/train.py --out-dir build --seed 42
python src/eval.py --build-dir build --out build/eval.json
python scripts/classify_diff_scope.py --baseline HEAD --output-json classify-output.json
python scripts/make_evidence_pack.py --build-dir build --evidence-dir evidence --scope-classification classify-output.json --out-tgz evidence/evidence-pack.tgz
```

**Policy (local vs CI):** The full Conftest policy requires SBOM and Trivy outputs in the evidence dir. In CI they are produced before the evidence pack is assembled. For a quick local run you can omit them; the policy gate will fail until SBOM/Trivy are present (e.g. run the full pipeline in a VM or rely on CI as source of truth).

## Local scope preflight

Before opening a PR, run the same early scope gate order used in CI:

```bash
python scripts/run_scope_preflight.py --baseline HEAD
```

This runs:
1. `scripts/classify_diff_scope.py`
2. `conftest test classify-output.json --policy policy --namespace scope_meta`

If `conftest` is not installed locally, the script exits with a clear next step.
 
## License
[MIT](LICENSE)
