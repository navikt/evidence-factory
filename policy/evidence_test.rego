# Unit tests for policy/evidence.rego. Run with: conftest verify --policy policy

package evidence_test

import data.evidence

# Full manifest (all required + required_ci, governance with bytes >= 20) must not be denied
test_full_manifest_passes if {
	manifest := {
		"files": [
			{"path": "eval.json", "bytes": 100},
			{"path": "model/model.joblib", "bytes": 200},
			{"path": "model/train_meta.json", "bytes": 300},
			{"path": "scope/file-scope.json", "bytes": 100},
			{"path": "scope/classify-output.json", "bytes": 100},
			{"path": "governance/intended-purpose.json", "bytes": 100},
			{"path": "governance/human-oversight.json", "bytes": 100},
			{"path": "governance/data-governance.json", "bytes": 100},
			{"path": "governance/risk-notes.json", "bytes": 100},
			{"path": "governance/traceability.json", "bytes": 100},
			{"path": "sbom.spdx.json", "bytes": 100},
			{"path": "trivy.sarif", "bytes": 100},
		],
	}
	count(evidence.deny) == 0 with input as manifest
}

# Missing a required file must produce the expected deny message
test_missing_required_file_denied if {
	manifest := {
		"files": [
			{"path": "eval.json", "bytes": 100},
			{"path": "model/model.joblib", "bytes": 200},
			{"path": "model/train_meta.json", "bytes": 300},
			{"path": "scope/file-scope.json", "bytes": 100},
			{"path": "scope/classify-output.json", "bytes": 100},
			{"path": "governance/intended-purpose.json", "bytes": 100},
			{"path": "governance/human-oversight.json", "bytes": 100},
			{"path": "governance/data-governance.json", "bytes": 100},
			{"path": "governance/risk-notes.json", "bytes": 100},
			# governance/traceability.json intentionally omitted
			{"path": "sbom.spdx.json", "bytes": 100},
			{"path": "trivy.sarif", "bytes": 100},
		],
	}
	"missing required file: governance/traceability.json" in evidence.deny with input as manifest
}

# Missing a required CI file must produce the expected deny message
test_missing_ci_file_denied if {
	manifest := {
		"files": [
			{"path": "eval.json", "bytes": 100},
			{"path": "model/model.joblib", "bytes": 200},
			{"path": "model/train_meta.json", "bytes": 300},
			{"path": "scope/file-scope.json", "bytes": 100},
			{"path": "scope/classify-output.json", "bytes": 100},
			{"path": "governance/intended-purpose.json", "bytes": 100},
			{"path": "governance/human-oversight.json", "bytes": 100},
			{"path": "governance/data-governance.json", "bytes": 100},
			{"path": "governance/risk-notes.json", "bytes": 100},
			{"path": "governance/traceability.json", "bytes": 100},
			{"path": "sbom.spdx.json", "bytes": 100},
			# trivy.sarif intentionally omitted
		],
	}
	"missing required CI file: trivy.sarif" in evidence.deny with input as manifest
}

# Doc with bytes < 10 must be denied
test_doc_too_small_denied if {
	manifest := {
		"files": [
			{"path": "eval.json", "bytes": 100},
			{"path": "model/model.joblib", "bytes": 200},
			{"path": "model/train_meta.json", "bytes": 300},
			{"path": "scope/file-scope.json", "bytes": 100},
			{"path": "scope/classify-output.json", "bytes": 100},
			{"path": "governance/intended-purpose.json", "bytes": 5},
			{"path": "governance/human-oversight.json", "bytes": 100},
			{"path": "governance/data-governance.json", "bytes": 100},
			{"path": "governance/risk-notes.json", "bytes": 100},
			{"path": "governance/traceability.json", "bytes": 100},
			{"path": "sbom.spdx.json", "bytes": 100},
			{"path": "trivy.sarif", "bytes": 100},
		],
	}
	"doc too small (likely empty): governance/intended-purpose.json" in evidence.deny with input as manifest
}

test_missing_scope_classification_denied if {
	manifest := {
		"files": [
			{"path": "eval.json", "bytes": 100},
			{"path": "model/model.joblib", "bytes": 200},
			{"path": "model/train_meta.json", "bytes": 300},
			{"path": "scope/file-scope.json", "bytes": 100},
			{"path": "governance/intended-purpose.json", "bytes": 100},
			{"path": "governance/human-oversight.json", "bytes": 100},
			{"path": "governance/data-governance.json", "bytes": 100},
			{"path": "governance/risk-notes.json", "bytes": 100},
			{"path": "governance/traceability.json", "bytes": 100},
			{"path": "sbom.spdx.json", "bytes": 100},
			{"path": "trivy.sarif", "bytes": 100},
		],
	}
	"missing required file: scope/classify-output.json" in evidence.deny with input as manifest
}
