package scope_meta_test

import data.scope_meta

test_scope_meta_passes_with_unique_classification if {
	input_doc := {
		"tracked_files": [
			"README.md",
			"src/train.py",
			"policy/evidence.rego",
			"governance/file-scope.json",
		],
		"scopes": [
			{"id": "governance", "globs": ["governance/**/*.json"]},
			{"id": "policy", "globs": ["policy/**/*.rego"]},
			{"id": "implementation", "globs": ["src/**/*.py"]},
			{"id": "project", "globs": ["README.md"]},
		],
	}
	count(scope_meta.deny) == 0 with input as input_doc
}

test_unclassified_file_denied if {
	input_doc := {
		"tracked_files": ["README.md", "misc.txt"],
		"scopes": [
			{"id": "project", "globs": ["README.md"]},
		],
	}
	"unclassified tracked file: misc.txt" in scope_meta.deny with input as input_doc
}

test_overlapping_file_denied if {
	input_doc := {
		"tracked_files": ["README.md"],
		"scopes": [
			{"id": "a", "globs": ["README.md"]},
			{"id": "b", "globs": ["README.*"]},
		],
	}
	some msg in scope_meta.deny with input as input_doc
	startswith(msg, "overlapping scope match for README.md:")
}

test_stale_scope_warns if {
	input_doc := {
		"tracked_files": ["README.md"],
		"scopes": [
			{"id": "project", "globs": ["README.md"]},
			{"id": "stale", "globs": ["never/**"]},
		],
	}
	"scope globs match zero tracked files: stale" in scope_meta.warn with input as input_doc
}