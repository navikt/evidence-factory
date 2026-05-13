# Evidence Factory: make governance compile.

This repository is a proof-of-concept evidence factory for ML systems: it turns governance requirements into cryptographically verifiable evidence and enforces them with policy-as-code in CI. If the governance requirements aren't met, the build fails. Retroactive falsification is detectable.  

**The evidence produced by this PoC does *not* by itself constitute full legal compliance.**

Verification layers:
1. **Existence:** the documentation files specified in evidence.rego exist and aren't empty. ✓ 
2. **Structure:** the documentation files include the structure for the information required by the AI Act.
3. **Coherence:** the information in the documentation is internally consistent and semantically valid.
4. **Grounded validity:** the documentation's claims about the system are true as the system and the world around it change.    

Currently the system is working at **layer 1** (verification of the existence of the specified files). Layer 2 is next on the docket; 3 and 4 are open research questions. 

**[⇝ Check out the wiki ⇜](../../wiki)** for more about this project's architecture, design principles, regulatory mapping, and open problems.

## Scope
 
This PoC uses a low-risk, decision-support scenario with synthetic data. The ML aspects are deliberately minimal; the governance architecture is the primary exhibit.
 
## Repository layout
 
- `src/` — training + evaluation code
- `scripts/` — evidence assembly utilities
- `governance/` — governance inputs (JSON; bundled + hashed + gated)
- `governance/file-scope.json` — declarative scope map for CI routing + scope policy checks
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
python scripts/make_evidence_pack.py --build-dir build --evidence-dir evidence --out-tgz evidence/evidence-pack.tgz
```

**Policy (local vs CI):** The full Conftest policy requires SBOM and Trivy outputs in the evidence dir. In CI they are produced before the evidence pack is assembled. For a quick local run you can omit them; the policy gate will fail until SBOM/Trivy are present (e.g. run the full pipeline in a VM or rely on CI as source of truth).

## Anonymity and data handling
 This repo must not contain sensitive data: synthetic data only; no secrets, internal URLs, PII, or internal docs. See [AGENTS.md](AGENTS.md) for the full list and enforcement policy.
 
## License
[MIT](LICENSE)
