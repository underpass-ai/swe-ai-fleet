package tools

import "testing"

func TestDefaultCapabilities_Metadata(t *testing.T) {
	capabilities := DefaultCapabilities()
	if len(capabilities) == 0 {
		t.Fatal("expected default capabilities")
	}

	seen := map[string]bool{}
	pathPolicyRequired := map[string]bool{
		"fs.list":               true,
		"fs.read_file":          true,
		"fs.write_file":         true,
		"fs.search":             true,
		"git.diff":              true,
		"security.scan_secrets": true,
	}
	for _, capability := range capabilities {
		if capability.Name == "" {
			t.Fatal("capability name must not be empty")
		}
		if seen[capability.Name] {
			t.Fatalf("duplicate capability name: %s", capability.Name)
		}
		seen[capability.Name] = true
		if capability.Observability.TraceName == "" || capability.Observability.SpanName == "" {
			t.Fatalf("missing observability names for %s", capability.Name)
		}
		if len(capability.InputSchema) == 0 || len(capability.OutputSchema) == 0 {
			t.Fatalf("missing schemas for %s", capability.Name)
		}
		if pathPolicyRequired[capability.Name] && len(capability.Policy.PathFields) == 0 {
			t.Fatalf("missing explicit path policy fields for %s", capability.Name)
		}
	}

	if !seen["fs.write_file"] ||
		!seen["conn.list_profiles"] ||
		!seen["conn.describe_profile"] ||
		!seen["nats.request"] ||
		!seen["nats.subscribe_pull"] ||
		!seen["kafka.consume"] ||
		!seen["kafka.topic_metadata"] ||
		!seen["rabbit.consume"] ||
		!seen["rabbit.queue_info"] ||
		!seen["redis.get"] ||
		!seen["redis.mget"] ||
		!seen["redis.scan"] ||
		!seen["redis.ttl"] ||
		!seen["redis.exists"] ||
		!seen["repo.detect_project_type"] ||
		!seen["repo.detect_toolchain"] ||
		!seen["repo.validate"] ||
		!seen["repo.build"] ||
		!seen["repo.test"] ||
		!seen["repo.run_tests"] ||
		!seen["repo.coverage_report"] ||
		!seen["repo.static_analysis"] ||
		!seen["repo.package"] ||
		!seen["security.scan_secrets"] ||
		!seen["ci.run_pipeline"] ||
		!seen["go.mod.tidy"] ||
		!seen["go.build"] ||
		!seen["go.test"] ||
		!seen["rust.build"] ||
		!seen["node.typecheck"] ||
		!seen["python.validate"] ||
		!seen["c.build"] {
		t.Fatalf("expected critical capabilities missing: %#v", seen)
	}
}
