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
	"File is not classified by any scope: misc.txt. Next step: add a matching glob in governance/file-scope.json." in scope_meta.deny with input as input_doc
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
	startswith(msg, "File matches multiple scopes: README.md ->")
}

test_stale_scope_warns if {
	input_doc := {
		"tracked_files": ["README.md"],
		"scopes": [
			{"id": "project", "globs": ["README.md"]},
			{"id": "stale", "globs": ["never/**"]},
		],
	}
	"Scope 'stale' currently matches no tracked files. Next step: remove stale globs or add the intended files." in scope_meta.warn with input as input_doc
}