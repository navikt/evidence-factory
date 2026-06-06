"""Tests for evidence pack assembly: manifest covers exactly the expected files."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Required evidence paths (policy/evidence.rego required set + model/test_set.npz from script)
EXPECTED_PATHS_LOCAL = {
    "eval.json",
    "model/model.joblib",
    "model/train_meta.json",
    "model/test_set.npz",
    "scope/file-scope.json",
    "scope/classify-output.json",
    "governance/intended-purpose.json",
    "governance/human-oversight.json",
    "governance/data-governance.json",
    "governance/risk-notes.json",
    "governance/traceability.json",
}


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run command; raise on failure."""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {r.stderr or r.stdout}")
    return r


def _minimal_build_dir(build_dir: Path, repo_root: Path) -> None:
    """Create minimal build artifacts by running train.py and eval.py."""
    build_dir.mkdir(parents=True, exist_ok=True)
    _run(
        [sys.executable, str(repo_root / "src" / "train.py"), "--out-dir", str(build_dir), "--seed", "42"],
        repo_root,
    )
    _run(
        [
            sys.executable,
            str(repo_root / "src" / "eval.py"),
            "--build-dir",
            str(build_dir),
            "--out",
            str(build_dir / "eval.json"),
        ],
        repo_root,
    )


def _minimal_governance_dir(governance_dir: Path) -> None:
    """Create minimal governance JSON files (content >= 20 bytes for policy)."""
    governance_dir.mkdir(parents=True, exist_ok=True)
    minimal = {"schema_version": "1", "title": "Placeholder", "body": "Minimal content for tests."}
    for name in [
        "intended-purpose.json",
        "human-oversight.json",
        "data-governance.json",
        "risk-notes.json",
        "traceability.json",
    ]:
        (governance_dir / name).write_text(json.dumps(minimal, indent=2), encoding="utf-8")


def _minimal_scope_provenance(scope_file: Path, classification_file: Path) -> None:
    """Create minimal scope registry and classifier output files."""
    scope_file.parent.mkdir(parents=True, exist_ok=True)
    classification_file.parent.mkdir(parents=True, exist_ok=True)
    scope_file.write_text(json.dumps({"schema_version": "1", "scopes": []}, indent=2), encoding="utf-8")
    classification_file.write_text(json.dumps({"schema_version": "1", "scope_matches_by_file": {}}, indent=2), encoding="utf-8")


def test_manifest_covers_expected_files_local(tmp_path: Path) -> None:
    """After running make_evidence_pack, manifest lists exactly the expected local paths."""
    build_dir = tmp_path / "build"
    governance_dir = tmp_path / "governance"
    scope_file = tmp_path / "config" / "file-scope.json"
    classification_file = tmp_path / "classify-output.json"
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    _minimal_build_dir(build_dir, REPO_ROOT)
    _minimal_governance_dir(governance_dir)
    _minimal_scope_provenance(scope_file, classification_file)

    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "make_evidence_pack.py"),
            "--build-dir",
            str(build_dir),
            "--governance-dir",
            str(governance_dir),
            "--scope-file",
            str(scope_file),
            "--scope-classification",
            str(classification_file),
            "--evidence-dir",
            str(evidence_dir),
            "--out-tgz",
            str(evidence_dir / "evidence-pack.tgz"),
        ],
        REPO_ROOT,
    )

    manifest_path = evidence_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    paths_in_manifest = {f["path"] for f in manifest["files"]}
    assert paths_in_manifest == EXPECTED_PATHS_LOCAL, (
        f"Manifest paths differ: expected {EXPECTED_PATHS_LOCAL}, got {paths_in_manifest}"
    )


def test_manifest_excludes_manifest_and_tgz(tmp_path: Path) -> None:
    """Manifest must not include manifest.json or evidence-pack.tgz."""
    build_dir = tmp_path / "build"
    governance_dir = tmp_path / "governance"
    scope_file = tmp_path / "config" / "file-scope.json"
    classification_file = tmp_path / "classify-output.json"
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    _minimal_build_dir(build_dir, REPO_ROOT)
    _minimal_governance_dir(governance_dir)
    _minimal_scope_provenance(scope_file, classification_file)

    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "make_evidence_pack.py"),
            "--build-dir",
            str(build_dir),
            "--governance-dir",
            str(governance_dir),
            "--scope-file",
            str(scope_file),
            "--scope-classification",
            str(classification_file),
            "--evidence-dir",
            str(evidence_dir),
            "--out-tgz",
            str(evidence_dir / "evidence-pack.tgz"),
        ],
        REPO_ROOT,
    )

    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    paths = {f["path"] for f in manifest["files"]}
    assert "manifest.json" not in paths
    assert "evidence-pack.tgz" not in paths


def test_manifest_includes_ci_artifacts_when_present(tmp_path: Path) -> None:
    """When SBOM and Trivy files exist in evidence dir, they appear in the manifest."""
    build_dir = tmp_path / "build"
    governance_dir = tmp_path / "governance"
    scope_file = tmp_path / "config" / "file-scope.json"
    classification_file = tmp_path / "classify-output.json"
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "sbom.spdx.json").write_text('{"spdxVersion": "SPDX-2.2"}', encoding="utf-8")
    (evidence_dir / "trivy.sarif").write_text('{"version": "2.1.0"}', encoding="utf-8")

    _minimal_build_dir(build_dir, REPO_ROOT)
    _minimal_governance_dir(governance_dir)
    _minimal_scope_provenance(scope_file, classification_file)

    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "make_evidence_pack.py"),
            "--build-dir",
            str(build_dir),
            "--governance-dir",
            str(governance_dir),
            "--scope-file",
            str(scope_file),
            "--scope-classification",
            str(classification_file),
            "--evidence-dir",
            str(evidence_dir),
            "--out-tgz",
            str(evidence_dir / "evidence-pack.tgz"),
        ],
        REPO_ROOT,
    )

    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
    paths = {f["path"] for f in manifest["files"]}
    expected = EXPECTED_PATHS_LOCAL | {"sbom.spdx.json", "trivy.sarif"}
    assert paths == expected, f"Expected {expected}, got {paths}"


def test_manifest_hashes_match_file_contents(tmp_path: Path) -> None:
    """SHA256 hashes in the manifest must match the actual file contents."""
    build_dir = tmp_path / "build"
    governance_dir = tmp_path / "governance"
    scope_file = tmp_path / "config" / "file-scope.json"
    classification_file = tmp_path / "classify-output.json"
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    _minimal_build_dir(build_dir, REPO_ROOT)
    _minimal_governance_dir(governance_dir)
    _minimal_scope_provenance(scope_file, classification_file)

    _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "make_evidence_pack.py"),
            "--build-dir",
            str(build_dir),
            "--governance-dir",
            str(governance_dir),
            "--scope-file",
            str(scope_file),
            "--scope-classification",
            str(classification_file),
            "--evidence-dir",
            str(evidence_dir),
            "--out-tgz",
            str(evidence_dir / "evidence-pack.tgz"),
        ],
        REPO_ROOT,
    )

    manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))

    for entry in manifest["files"]:
        file_path = evidence_dir / entry["path"]
        assert file_path.exists(), f"manifest references non-existent file: {entry['path']}"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == entry["sha256"], (
            f"hash mismatch for {entry['path']}: manifest says {entry['sha256']}, file is {actual_hash}"
        )
