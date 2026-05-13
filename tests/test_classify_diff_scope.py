import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _git(cwd: Path, *args: str) -> None:
    result = _run(["git", *args], cwd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(tmp_path: Path) -> str:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")

    _write(tmp_path / "governance" / "file-scope.json", (REPO_ROOT / "governance" / "file-scope.json").read_text())
    _write(tmp_path / "README.md", "hello\n")
    _write(tmp_path / "src" / "train.py", "print('x')\n")
    _write(tmp_path / "policy" / "evidence.rego", "package evidence\n")
    _write(tmp_path / "tests" / "test_dummy.py", "def test_dummy():\n    assert True\n")

    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "init")
    base = _run(["git", "rev-parse", "HEAD"], tmp_path)
    return base.stdout.strip()


def _run_classifier(tmp_path: Path, baseline: str) -> subprocess.CompletedProcess:
    output = tmp_path / "classify-output.json"
    return _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "classify_diff_scope.py"),
            "--scope-file",
            str(tmp_path / "governance" / "file-scope.json"),
            "--baseline",
            baseline,
            "--output-json",
            str(output),
        ],
        tmp_path,
    )


def test_implementation_change_sets_ml_trigger(tmp_path: Path) -> None:
    base = _init_repo(tmp_path)
    _write(tmp_path / "src" / "train.py", "print('changed')\n")
    _git(tmp_path, "add", "src/train.py")
    _git(tmp_path, "commit", "-m", "change src")

    result = _run_classifier(tmp_path, base)
    assert result.returncode == 0, result.stderr

    payload = json.loads((tmp_path / "classify-output.json").read_text(encoding="utf-8"))
    assert payload["triggers_ml"] is True
    assert payload["triggers_governance"] is False
    assert "implementation" in payload["changed_scopes"]


def test_governance_change_sets_both_triggers(tmp_path: Path) -> None:
    base = _init_repo(tmp_path)
    _write(tmp_path / "governance" / "intended-purpose.json", '{"schema_version":"1"}\n')
    _git(tmp_path, "add", "governance/intended-purpose.json")
    _git(tmp_path, "commit", "-m", "add governance")

    result = _run_classifier(tmp_path, base)
    assert result.returncode == 0, result.stderr

    payload = json.loads((tmp_path / "classify-output.json").read_text(encoding="utf-8"))
    assert payload["triggers_ml"] is True
    assert payload["triggers_governance"] is True
    assert "governance" in payload["changed_scopes"]


def test_generated_change_fails_and_writes_output(tmp_path: Path) -> None:
    base = _init_repo(tmp_path)
    _write(tmp_path / "build" / "x.txt", "x\n")
    _git(tmp_path, "add", "build/x.txt")
    _git(tmp_path, "commit", "-m", "generated")

    result = _run_classifier(tmp_path, base)
    assert result.returncode != 0
    payload = json.loads((tmp_path / "classify-output.json").read_text(encoding="utf-8"))
    assert payload["generated_changed"] is True


def test_unclassified_change_fails_and_writes_output(tmp_path: Path) -> None:
    base = _init_repo(tmp_path)
    _write(tmp_path / "notes.txt", "x\n")
    _git(tmp_path, "add", "notes.txt")
    _git(tmp_path, "commit", "-m", "unclassified")

    result = _run_classifier(tmp_path, base)
    assert result.returncode != 0
    payload = json.loads((tmp_path / "classify-output.json").read_text(encoding="utf-8"))
    assert payload["unclassified_files"] == ["notes.txt"]


def test_missing_scope_file_fails(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    result = _run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "classify_diff_scope.py"),
            "--scope-file",
            str(tmp_path / "governance" / "file-scope.json"),
            "--baseline",
            "HEAD",
            "--output-json",
            str(tmp_path / "classify-output.json"),
        ],
        tmp_path,
    )
    assert result.returncode != 0
    assert "missing scope file" in result.stderr