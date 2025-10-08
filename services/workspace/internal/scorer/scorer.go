// Package scorer implements workspace result scoring with rigor profiles
package scorer

import (
	"fmt"
	"os"

	wsv1 "github.com/underpass-ai/swe-ai-fleet/services/workspace/gen/fleet/workspace/v1"
	"gopkg.in/yaml.v3"
)

// RigorProfile defines quality thresholds for a rigor level
type RigorProfile struct {
	Name        string             `yaml:"name"`
	Description string             `yaml:"description"`
	Weights     map[string]float64 `yaml:"weights"`
	Thresholds  Thresholds         `yaml:"thresholds"`
}

// Thresholds defines pass/fail criteria per dimension
type Thresholds struct {
	Build struct {
		OK string `yaml:"ok"` // "required"
	} `yaml:"build"`

	Unit struct {
		OK       string  `yaml:"ok"`
		PassRate float64 `yaml:"pass_rate"`
	} `yaml:"unit"`

	Coverage struct {
		NewCodePct float64 `yaml:"new_code_pct"`
	} `yaml:"coverage"`

	Static struct {
		QualityGate string `yaml:"quality_gate"` // "warn_or_better", "ok"
		MaxCritical int    `yaml:"max_critical"`
		MaxMajor    int    `yaml:"max_major"`
	} `yaml:"static"`

	E2E struct {
		PassRate float64 `yaml:"pass_rate"`
	} `yaml:"e2e"`

	Lint struct {
		MaxErrors int `yaml:"max_errors"`
	} `yaml:"lint"`
}

// GatingThresholds defines when to pass/warn/block
type GatingThresholds struct {
	Pass  int `yaml:"pass"`
	Warn  int `yaml:"warn"`
	Block int `yaml:"block"`
}

// RigorConfig represents the rigor.yaml configuration
type RigorConfig struct {
	Profiles         map[string]RigorProfile `yaml:"profiles"`
	GatingThresholds GatingThresholds        `yaml:"gating_thresholds"`
}

// LoadRigorConfig loads rigor profiles from YAML
func LoadRigorConfig(path string) (*RigorConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read file: %w", err)
	}

	var cfg RigorConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("unmarshal yaml: %w", err)
	}

	return &cfg, nil
}

// ScoreWorkspace computes a weighted score based on rigor level
func ScoreWorkspace(report *wsv1.WorkspaceReport, rigorLevel string, cfg *RigorConfig) (int32, []string, string) {
	profile, ok := cfg.Profiles[rigorLevel]
	if !ok {
		profile = cfg.Profiles["L1"] // Default to L1
	}

	reasons := []string{}
	dimensionScores := make(map[string]float64)

	// 1. Build
	if report.Build != nil && report.Build.Ok {
		dimensionScores["build"] = 100.0
	} else {
		dimensionScores["build"] = 0.0
		reasons = append(reasons, "Build failed")
	}

	// 2. Unit tests
	if report.Unit != nil && report.Unit.Ok {
		total := float64(report.Unit.Passed + report.Unit.Failed)
		passRate := 1.0
		if total > 0 {
			passRate = float64(report.Unit.Passed) / total
		}

		if passRate >= profile.Thresholds.Unit.PassRate {
			dimensionScores["unit"] = 100.0
		} else {
			dimensionScores["unit"] = (passRate / profile.Thresholds.Unit.PassRate) * 100.0
			reasons = append(reasons, fmt.Sprintf("Unit test pass rate %.1f%% below threshold %.1f%%",
				passRate*100, profile.Thresholds.Unit.PassRate*100))
		}
	} else {
		dimensionScores["unit"] = 0.0
		reasons = append(reasons, "Unit tests failed or missing")
	}

	// 3. Coverage
	if report.Unit != nil {
		if float64(report.Unit.Coverage) >= profile.Thresholds.Coverage.NewCodePct {
			dimensionScores["coverage"] = 100.0
		} else {
			dimensionScores["coverage"] = (float64(report.Unit.Coverage) / profile.Thresholds.Coverage.NewCodePct) * 100.0
			reasons = append(reasons, fmt.Sprintf("Coverage %.1f%% below threshold %.1f%%",
				report.Unit.Coverage, profile.Thresholds.Coverage.NewCodePct))
		}
	} else {
		dimensionScores["coverage"] = 0.0
	}

	// 4. Static analysis (SonarQube)
	if report.Static != nil && report.Static.Ok {
		qgOk := false
		switch profile.Thresholds.Static.QualityGate {
		case "warn_or_better":
			qgOk = report.Static.Sonar.QualityGate == "OK" || report.Static.Sonar.QualityGate == "WARN"
		case "ok":
			qgOk = report.Static.Sonar.QualityGate == "OK"
		}

		criticalOk := int(report.Static.Sonar.NewCritical) <= profile.Thresholds.Static.MaxCritical
		majorOk := int(report.Static.Sonar.NewMajor) <= profile.Thresholds.Static.MaxMajor

		if qgOk && criticalOk && majorOk {
			dimensionScores["static"] = 100.0
		} else {
			dimensionScores["static"] = 50.0
			if !qgOk {
				reasons = append(reasons, fmt.Sprintf("SonarQube Quality Gate: %s (expected %s)",
					report.Static.Sonar.QualityGate, profile.Thresholds.Static.QualityGate))
			}
			if !criticalOk {
				reasons = append(reasons, fmt.Sprintf("New critical issues: %d (max %d)",
					report.Static.Sonar.NewCritical, profile.Thresholds.Static.MaxCritical))
			}
			if !majorOk {
				reasons = append(reasons, fmt.Sprintf("New major issues: %d (max %d)",
					report.Static.Sonar.NewMajor, profile.Thresholds.Static.MaxMajor))
			}
		}
	} else {
		dimensionScores["static"] = 0.0
		reasons = append(reasons, "Static analysis failed or missing")
	}

	// 5. E2E tests
	if report.E2E != nil && report.E2E.Ok {
		total := float64(report.E2E.Passed + report.E2E.Failed)
		passRate := 1.0
		if total > 0 {
			passRate = float64(report.E2E.Passed) / total
		}

		if passRate >= profile.Thresholds.E2E.PassRate {
			dimensionScores["e2e"] = 100.0
		} else {
			dimensionScores["e2e"] = (passRate / profile.Thresholds.E2E.PassRate) * 100.0
			reasons = append(reasons, fmt.Sprintf("E2E pass rate %.1f%% below threshold %.1f%%",
				passRate*100, profile.Thresholds.E2E.PassRate*100))
		}
	} else {
		dimensionScores["e2e"] = 0.0
		reasons = append(reasons, "E2E tests failed or missing")
	}

	// 6. Lint (placeholder - not in report struct, assuming 0 errors)
	dimensionScores["lint"] = 100.0

	// Compute weighted total
	totalScore := 0.0
	for dim, score := range dimensionScores {
		weight := profile.Weights[dim]
		totalScore += score * weight
	}

	// Gating decision
	gating := "block"
	if int(totalScore) >= cfg.GatingThresholds.Pass {
		gating = "pass"
	} else if int(totalScore) >= cfg.GatingThresholds.Warn {
		gating = "warn"
	}

	if len(reasons) == 0 {
		reasons = append(reasons, "All checks passed")
	}

	return int32(totalScore), reasons, gating
}
