package scope_meta

import rego.v1

matches_scope(path, scope) if {
	some pattern in scope.globs
	glob.match(pattern, ["/"], path)
}

matched_ids(path) := ids if {
	ids := [scope.id | scope := input.scopes[_]; matches_scope(path, scope)]
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
	matches_scope(path, scope)
}

warn contains msg if {
	scope := input.scopes[_]
	not scope_has_match(scope)
	msg := sprintf(
		"Scope '%s' currently matches no tracked files. Next step: remove stale globs or add the intended files.",
		[scope.id],
	)
}