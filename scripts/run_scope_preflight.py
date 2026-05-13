"""Run local scope preflight checks with the same gate order as CI.

This script runs:
1) scope classification
2) scope meta-policy gate via Conftest
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> int:
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="HEAD", help="Baseline commit/ref for scope diff (default: HEAD)")
    parser.add_argument("--output-json", default="classify-output.json", help="Path for classifier output JSON")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    classifier = repo_root / "scripts" / "classify_diff_scope.py"
    output_json = Path(args.output_json)

    print("Step 1/2: Running scope classifier...")
    classify_rc = run(
        [
            sys.executable,
            str(classifier),
            "--baseline",
            args.baseline,
            "--output-json",
            str(output_json),
        ],
        cwd=repo_root,
    )
    if classify_rc != 0:
        print(
            "Scope classifier failed. Next step: fix the reported scope issues and rerun this command.",
            file=sys.stderr,
        )
        sys.exit(classify_rc)

    if shutil.which("conftest") is None:
        print(
            "Conftest is not installed or not on PATH. Next step: install Conftest and rerun this command. "
            "CI installs Conftest automatically.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not output_json.exists():
        print(
            f"Classifier output not found at {output_json}. Next step: check classifier output path and rerun.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Step 2/2: Running scope meta-policy gate...")
    gate_rc = run(
        [
            "conftest",
            "test",
            str(output_json),
            "--policy",
            "policy",
            "--namespace",
            "scope_meta",
        ],
        cwd=repo_root,
    )
    if gate_rc != 0:
        print(
            "Scope meta-policy gate failed. Next step: fix the policy findings and rerun this command.",
            file=sys.stderr,
        )
        sys.exit(gate_rc)

    print("Scope preflight passed.")


if __name__ == "__main__":
    main()
