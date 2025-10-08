// Package scorer implements DoR/INVEST scoring logic
package scorer

import (
	"fmt"
	"strings"

	coachv1 "github.com/underpass-ai/swe-ai-fleet/services/storycoach/gen/fleet/storycoach/v1"
)

// ScoreStory evaluates a story against INVEST + DoR criteria
func ScoreStory(title, description string, ac []string) (int32, []*coachv1.Finding) {
	score := int32(0)
	findings := []*coachv1.Finding{}

	// 1. Acceptance Criteria (40 points)
	if len(ac) > 0 {
		hasGherkin := false
		for _, criterion := range ac {
			lower := strings.ToLower(criterion)
			if strings.Contains(lower, "given") || strings.Contains(lower, "when") || strings.Contains(lower, "then") {
				hasGherkin = true
				break
			}
		}

		if hasGherkin {
			score += 40
		} else {
			score += 20 // Partial credit for having AC
			findings = append(findings, &coachv1.Finding{
				Code:    "AC_NO_GHERKIN",
				Message: "AC should use Given/When/Then format",
				Weight:  20,
			})
		}
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "AC_MISSING",
			Message: "Add Given/When/Then acceptance criteria",
			Weight:  40,
		})
	}

	// 2. INVEST: Independent (10 points)
	// Check for dependency markers
	descLower := strings.ToLower(description)
	if !strings.Contains(descLower, "depends on") && !strings.Contains(descLower, "blocked by") {
		score += 10
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "NOT_INDEPENDENT",
			Message: "Story has dependencies; consider decoupling",
			Weight:  10,
		})
	}

	// 3. INVEST: Valuable (10 points)
	// Check for user value statement
	titleLower := strings.ToLower(title)
	if strings.Contains(titleLower, "as a") || strings.Contains(descLower, "so that") {
		score += 10
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "VALUE_UNCLEAR",
			Message: "Title should express user value (As a <user>, I want <capability> so that <value>)",
			Weight:  10,
		})
	}

	// 4. INVEST: Estimable (5 points)
	// Check for ambiguous terms
	ambiguous := []string{"tbd", "todo", "maybe", "probably", "lots of", "several"}
	hasAmbiguous := false
	for _, term := range ambiguous {
		if strings.Contains(descLower, term) {
			hasAmbiguous = true
			break
		}
	}

	if !hasAmbiguous {
		score += 5
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "AMBIGUOUS",
			Message: "Remove ambiguous terms (TBD, TODO, maybe, etc.)",
			Weight:  5,
		})
	}

	// 5. INVEST: Small (20 points)
	// Simple heuristic: description length
	if len(description) > 0 && len(description) < 600 {
		score += 20
	} else if len(description) >= 600 {
		findings = append(findings, &coachv1.Finding{
			Code:    "TOO_LARGE",
			Message: "Story is too large; consider splitting into smaller stories",
			Weight:  20,
		})
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "DESC_MISSING",
			Message: "Add a description",
			Weight:  20,
		})
	}

	// 6. INVEST: Testable (10 points)
	// Check if AC is testable (has observable outcomes)
	testable := false
	for _, criterion := range ac {
		if strings.Contains(strings.ToLower(criterion), "then") {
			testable = true
			break
		}
	}

	if testable {
		score += 10
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "NOT_TESTABLE",
			Message: "AC should specify observable outcomes (Then...)",
			Weight:  10,
		})
	}

	// 7. Clarity (5 points)
	if len(title) > 10 && len(title) < 100 {
		score += 5
	} else {
		findings = append(findings, &coachv1.Finding{
			Code:    "TITLE_LENGTH",
			Message: "Title should be concise but descriptive (10-100 chars)",
			Weight:  5,
		})
	}

	// Cap at 100
	if score > 100 {
		score = 100
	}

	return score, findings
}

// RefineStory suggests improvements
func RefineStory(title, description string, ac []string) (string, string, []string) {
	refinedTitle := strings.TrimSpace(title)
	refinedDesc := strings.TrimSpace(description)
	refinedAC := ac

	// Fix title: ensure it expresses value
	if !strings.Contains(strings.ToLower(refinedTitle), "as a") {
		refinedTitle = "As a <user>, I want " + refinedTitle + " so that <value>"
	}

	// Fix description: remove ambiguous terms
	ambiguous := []string{"tbd", "todo", "maybe", "probably"}
	for _, term := range ambiguous {
		refinedDesc = strings.ReplaceAll(strings.ToLower(refinedDesc), term, "[CLARIFY]")
	}

	// Fix AC: provide Gherkin template if empty
	if len(refinedAC) == 0 {
		refinedAC = []string{
			"Given <precondition>\nWhen <action>\nThen <observable outcome>",
		}
	}

	return refinedTitle, refinedDesc, refinedAC
}

// SuggestStory generates a story template from a goal
func SuggestStory(goal string) (string, string, []string) {
	title := fmt.Sprintf("As a user, I want %s so that I can achieve my goal", goal)
	description := fmt.Sprintf("This story implements: %s\n\nDetails:\n- [Add details here]\n\nDependencies:\n- [List dependencies or mark N/A]", goal)
	ac := []string{
		"Scenario: Basic usage\n  Given a user is authenticated\n  When they " + goal + "\n  Then they see confirmation",
	}

	return title, description, ac
}


