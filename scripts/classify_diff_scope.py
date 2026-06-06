import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pathspec import PathSpec


ZERO_SHA = "0" * 40


class ScopeConfigError(Exception):
    pass


@dataclass
class ScopeSpec:
    scope_id: str
    kind: str
    globs: list[str]
    triggers_governance: bool
    triggers_ml: bool
    generated: bool
    disallow_in_commits: bool
    matcher: PathSpec


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], check=False, capture_output=True, text=True)


def git_stdout(args: list[str]) -> str:
    result = run_git(args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def load_scope_specs(scope_file: Path) -> list[ScopeSpec]:
    if not scope_file.exists():
        raise ScopeConfigError(
            f"Scope file not found: {scope_file}. Next step: add config/file-scope.json "
            "or pass --scope-file with the correct path."
        )
    try:
        raw = json.loads(scope_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScopeConfigError(
            f"Scope file contains invalid JSON: {scope_file}. Next step: fix JSON syntax and try again. "
            f"Details: {exc}"
        ) from exc

    scopes = raw.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        raise ScopeConfigError(
            "Scope file schema is invalid: 'scopes' must be a non-empty array. "
            "Next step: check config/file-scope.json schema and add at least one scope entry."
        )

    compiled: list[ScopeSpec] = []
    seen_ids: set[str] = set()
    for scope in scopes:
        if not isinstance(scope, dict):
            raise ScopeConfigError(
                "Scope file schema is invalid: each scope must be an object. "
                "Next step: fix malformed entries in config/file-scope.json."
            )
        scope_id = scope.get("id")
        kind = scope.get("kind")
        globs = scope.get("globs")
        if not isinstance(scope_id, str) or not scope_id:
            raise ScopeConfigError(
                "Scope file schema is invalid: each scope requires a non-empty string 'id'. "
                "Next step: add an id for each scope in config/file-scope.json."
            )
        if scope_id in seen_ids:
            raise ScopeConfigError(
                f"Scope file schema is invalid: duplicate scope id '{scope_id}'. "
                "Next step: make each scope id unique in config/file-scope.json."
            )
        seen_ids.add(scope_id)
        if not isinstance(kind, str) or not kind:
            raise ScopeConfigError(
                f"Scope '{scope_id}' is missing a non-empty 'kind'. "
                "Next step: set a kind value in config/file-scope.json."
            )
        if not isinstance(globs, list) or not globs or any(not isinstance(g, str) or not g for g in globs):
            raise ScopeConfigError(
                f"Scope '{scope_id}' has invalid 'globs'. Next step: provide a non-empty array of non-empty strings."
            )

        compiled.append(
            ScopeSpec(
                scope_id=scope_id,
                kind=kind,
                globs=globs,
                triggers_governance=bool(scope.get("triggers_governance", False)),
                triggers_ml=bool(scope.get("triggers_ml", False)),
                generated=bool(scope.get("generated", False)),
                disallow_in_commits=bool(scope.get("disallow_in_commits", False)),
                matcher=PathSpec.from_lines("gitwildmatch", globs),
            )
        )

    return compiled


def resolve_baseline(raw_baseline: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    baseline = raw_baseline.strip()
    if not baseline:
        raise RuntimeError(
            "Baseline ref is missing. Next step: set DIFF_BASELINE in the workflow before running the classifier."
        )
    if baseline == ZERO_SHA:
        initial = git_stdout(["rev-list", "--max-parents=0", "HEAD"]).splitlines()
        if not initial:
            raise RuntimeError(
                "Baseline is all zeros and the first commit could not be resolved. "
                "Next step: verify git history is available in this checkout (for CI, use fetch-depth: 0)."
            )
        baseline = initial[0]
        warnings.append(
            "Baseline SHA was all zeros, so the classifier used the repository's first commit as baseline."
        )

    check_commit = run_git(["cat-file", "-e", f"{baseline}^{{commit}}"])
    if check_commit.returncode != 0:
        raise RuntimeError(
            f"Baseline '{baseline}' is not a valid commit. Next step: verify the baseline ref/SHA passed to DIFF_BASELINE."
        )

    is_ancestor = run_git(["merge-base", "--is-ancestor", baseline, "HEAD"])
    if is_ancestor.returncode != 0:
        raise RuntimeError(
            f"Baseline '{baseline}' is not reachable from HEAD. Next step: ensure the checkout has full history "
            "(fetch-depth: 0) and the correct base ref."
        )

    return baseline, warnings


def tracked_files() -> list[str]:
    out = git_stdout(["ls-files"])
    return [line for line in out.splitlines() if line]


def changed_files_against(baseline: str) -> list[str]:
    out = git_stdout(["diff", "--name-only", baseline, "HEAD"])
    return [line for line in out.splitlines() if line]


def classify_paths(paths: list[str], specs: list[ScopeSpec]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for path in paths:
        matches = [scope.scope_id for scope in specs if scope.matcher.match_file(path)]
        result[path] = matches
    return result


def to_scope_json(specs: list[ScopeSpec]) -> list[dict[str, object]]:
    return [
        {
            "id": s.scope_id,
            "kind": s.kind,
            "globs": s.globs,
            "triggers_governance": s.triggers_governance,
            "triggers_ml": s.triggers_ml,
            "generated": s.generated,
            "disallow_in_commits": s.disallow_in_commits,
        }
        for s in specs
    ]


def write_outputs(payload: dict[str, object]) -> None:
    github_output = os.getenv("GITHUB_OUTPUT")
    if not github_output:
        return
    lines = [
        f"triggers_governance={str(payload['triggers_governance']).lower()}",
        f"triggers_ml={str(payload['triggers_ml']).lower()}",
        f"build_evidence={str(payload['build_evidence']).lower()}",
        f"generated_changed={str(payload['generated_changed']).lower()}",
        f"changed_scopes={json.dumps(payload['changed_scopes'])}",
        f"unclassified_files={json.dumps(payload['unclassified_files'])}",
        f"overlap_files={json.dumps(payload['overlap_files'])}",
    ]
    with Path(github_output).open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line)
            f.write("\n")


def output_path_from_env(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    workspace = os.getenv("GITHUB_WORKSPACE")
    if workspace:
        return Path(workspace) / "classify-output.json"
    return Path("classify-output.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope-file", default="config/file-scope.json")
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    try:
        specs = load_scope_specs(Path(args.scope_file))
    except ScopeConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    raw_baseline = args.baseline or os.getenv("DIFF_BASELINE", "")
    try:
        baseline, warnings = resolve_baseline(raw_baseline)
        tracked = tracked_files()
        tracked_set = set(tracked)
        changed = changed_files_against(baseline)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    changed_tracked = sorted(p for p in changed if p in tracked_set)
    tracked_sorted = sorted(tracked)
    tracked_matches = classify_paths(tracked_sorted, specs)
    matches = classify_paths(changed_tracked, specs)

    unclassified = sorted(path for path, ids in matches.items() if len(ids) == 0)
    overlap = sorted(path for path, ids in matches.items() if len(ids) > 1)
    changed_scope_ids = sorted({scope_id for ids in matches.values() for scope_id in ids})

    scope_map = {scope.scope_id: scope for scope in specs}
    triggers_governance = any(scope_map[s].triggers_governance for s in changed_scope_ids)
    triggers_ml = any(scope_map[s].triggers_ml for s in changed_scope_ids)
    build_evidence = triggers_governance or triggers_ml

    generated_changed = any(p.startswith("evidence/") or p.startswith("build/") for p in changed)

    payload = {
        "schema_version": "1",
        "baseline": baseline,
        "warnings": warnings,
        "tracked_files": tracked_sorted,
        "scopes": to_scope_json(specs),
        "scope_matches_by_file": tracked_matches,
        "changed_files": changed_tracked,
        "changed_scopes": changed_scope_ids,
        "triggers_governance": triggers_governance,
        "triggers_ml": triggers_ml,
        "build_evidence": build_evidence,
        "generated_changed": generated_changed,
        "unclassified_files": unclassified,
        "overlap_files": overlap,
    }

    out_path = output_path_from_env(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_outputs(payload)

    violations: list[str] = []
    if unclassified:
        violations.append(
            "Some changed files are not covered by any scope: "
            f"{', '.join(unclassified)}. "
            "Next step: add matching globs in config/file-scope.json."
        )
    if overlap:
        violations.append(
            "Some changed files match more than one scope: "
            f"{', '.join(overlap)}. "
            "Next step: make scope globs mutually exclusive in config/file-scope.json."
        )
    if generated_changed:
        violations.append(
            "Detected changes under generated artifact paths (evidence/ or build/). "
            "Next step: remove those files from the commit and regenerate artifacts only in CI."
        )

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if violations:
        print("ERROR: Scope classification failed.", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Scope classification complete. Wrote {out_path}. "
        f"Changed scopes: {', '.join(changed_scope_ids) if changed_scope_ids else 'none'}.")


if __name__ == "__main__":
    main()