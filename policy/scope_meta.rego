package scope_meta

import rego.v1

matched_ids(path) := ids if {
	mapping := object.get(input, "scope_matches_by_file", {})
	ids := object.get(mapping, path, [])
}

deny contains msg if {
	not is_object(object.get(input, "scope_matches_by_file", null))
	msg := "Scope mapping is missing in classifier output. Next step: run scripts/classify_diff_scope.py before running the scope meta-policy gate."
}

deny contains msg if {
	path := input.tracked_files[_]
	count(matched_ids(path)) == 0
	msg := sprintf(
		"File is not classified by any scope: %s. Next step: add a matching glob in governance/file-scope.json.",
		[path],
	)
}

deny contains msg if {
	path := input.tracked_files[_]
	ids := matched_ids(path)
	count(ids) > 1
	msg := sprintf(
		"File matches multiple scopes: %s -> %v. Next step: make those scope globs mutually exclusive.",
		[path, ids],
	)
}

scope_has_match(scope) if {
	some path in input.tracked_files
	scope.id in matched_ids(path)
}

warn contains msg if {
	scope := input.scopes[_]
	not object.get(scope, "generated", false)
	not scope_has_match(scope)
	msg := sprintf(
		"Scope '%s' currently matches no tracked files. Next step: remove stale globs or add the intended files.",
		[scope.id],
	)
}