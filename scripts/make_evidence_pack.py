import argparse, hashlib, json, os, shutil, tarfile
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-dir", default="build")
    ap.add_argument("--governance-dir", default="governance")
    ap.add_argument("--scope-file", default="config/file-scope.json")
    ap.add_argument("--scope-classification", default="classify-output.json")
    ap.add_argument("--evidence-dir", default="evidence")
    ap.add_argument("--out-tgz", default="evidence/evidence-pack.tgz")
    ap.add_argument("--git-sha", default=None, help="Git commit SHA (e.g. from CI); omitted if not set")
    ap.add_argument("--ci-run-url", default=None, help="URL of the CI run that produced this pack; omitted if not set")
    args = ap.parse_args()

    build_dir = Path(args.build_dir)
    governance_dir = Path(args.governance_dir)
    scope_file = Path(args.scope_file)
    scope_classification = Path(args.scope_classification)
    evidence_dir = Path(args.evidence_dir)

    # Only remove what this script owns; leave e.g. sbom.spdx.json / trivy.sarif from CI
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if (evidence_dir / "model").exists():
        shutil.rmtree(evidence_dir / "model")
    if (evidence_dir / "governance").exists():
        shutil.rmtree(evidence_dir / "governance")
    if (evidence_dir / "scope").exists():
        shutil.rmtree(evidence_dir / "scope")
    if (evidence_dir / "eval.json").exists():
        (evidence_dir / "eval.json").unlink()

    # copy model artifacts
    (evidence_dir / "model").mkdir(parents=True)
    shutil.copy2(build_dir / "model.joblib", evidence_dir / "model" / "model.joblib")
    shutil.copy2(build_dir / "train_meta.json", evidence_dir / "model" / "train_meta.json")
    shutil.copy2(build_dir / "test_set.npz", evidence_dir / "model" / "test_set.npz")

    # copy eval
    shutil.copy2(build_dir / "eval.json", evidence_dir / "eval.json")

    # copy governance (these are your governance artifacts)
    shutil.copytree(governance_dir, evidence_dir / "governance")

    # copy scope provenance inputs so they are hashed into the signed manifest
    (evidence_dir / "scope").mkdir(parents=True)
    shutil.copy2(scope_file, evidence_dir / "scope" / "file-scope.json")
    shutil.copy2(scope_classification, evidence_dir / "scope" / "classify-output.json")

    # NOTE: SBOM and Trivy outputs are expected to already exist in evidence_dir root
    # when running in CI. Locally you can skip them; CI will add them.

    # build manifest over everything currently in evidence_dir (excluding manifest itself and tgz)
    files = []
    for p in sorted(evidence_dir.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(evidence_dir).as_posix()
        if rel in {"manifest.json", "evidence-pack.tgz"}:
            continue
        files.append({
            "path": rel,
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
        })

    manifest = {
        "schema_version": "1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    if args.git_sha is not None:
        manifest["git_sha"] = args.git_sha
    if args.ci_run_url is not None:
        manifest["ci_run_url"] = args.ci_run_url

    with (evidence_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    # tar it
    out_tgz = Path(args.out_tgz)
    out_tgz.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out_tgz, "w:gz") as tf:
        tf.add(evidence_dir, arcname="evidence")

    print(f"Wrote {out_tgz}")


if __name__ == "__main__":
    main()