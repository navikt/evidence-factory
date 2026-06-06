package evidence

import rego.v1

required := {
  "eval.json",
  "model/model.joblib",
  "model/train_meta.json",
  "scope/file-scope.json",
  "scope/classify-output.json",
  "governance/intended-purpose.json",
  "governance/human-oversight.json",
  "governance/data-governance.json",
  "governance/risk-notes.json",
  "governance/traceability.json",
}

# In CI we also require supply-chain artifacts:
required_ci := {
  "sbom.spdx.json",
  "trivy.sarif",
}

files := {f.path | f := input.files[_]}

deny contains msg if {
  some p in required
  not (p in files)
  msg := sprintf("missing required file: %s", [p])
}

deny contains msg if {
  some p in required_ci
  not (p in files)
  msg := sprintf("missing required CI file: %s", [p])
}

deny contains msg if {
  some f in input.files
  startswith(f.path, "governance/")
  f.bytes < 20
  msg := sprintf("doc too small (likely empty): %s", [f.path])
}