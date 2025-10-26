# SonarCloud 0% Coverage Fix

## Problem

SonarCloud consistently reports **0% code coverage** despite unit tests passing and `coverage.xml` being generated.

## Root Cause

SonarCloud doesn't read coverage from `sonar-project.properties` by default. The coverage report paths must be explicitly passed in the GitHub Actions workflow via `args:`.

## Industry Standard Solution

### The Issue with `sonar-project.properties`

The configuration file specifies:
```properties
sonar.python.coverage.reportPaths=coverage.xml
sonar.coverage.jacoco.xmlReportPaths=coverage.xml
```

However, when using the `sonarsource/sonarcloud-github-action@v3.1`, these properties are **NOT automatically read** from the file unless explicitly specified in the workflow `args:`.

### The Fix

Add explicit coverage report paths to the GitHub Actions workflow:

```yaml
- name: SonarCloud Scan (Pull Request)
  uses: sonarsource/sonarcloud-github-action@v3.1
  with:
    args: >
      -Dsonar.organization=underpass-ai-swe-ai-fleet
      -Dsonar.projectKey=underpass-ai-swe-ai-fleet
      -Dsonar.pullrequest.key=${{ github.event.number }}
      -Dsonar.pullrequest.branch=${{ github.head_ref }}
      -Dsonar.pullrequest.base=${{ github.base_ref }}
      -Dsonar.python.coverage.reportPaths=coverage.xml  # ← CRITICAL
      -Dsonar.scanner.image=sonarsource/sonar-scanner-cli:11.1
```

**Note**: For Python projects, only `sonar.python.coverage.reportPaths` is needed. JaCoCo (`sonar.coverage.jacoco.xmlReportPaths`) is Java-specific.

## Why This Happens

1. **SonarCloud Scanner CLI** expects explicit configuration via command-line arguments
2. The `sonar-project.properties` file is used by the standalone scanner, not by the GitHub Action
3. The GitHub Action builds its own scanner command and only reads from `args:`

## References

- [SonarCloud Test Coverage Guide](https://docs.sonarsource.com/sonarcloud/enriching/test-coverage/overview/)
- [SonarCloud Python Coverage](https://docs.sonarsource.com/sonarcloud/enriching/test-coverage/python-test-coverage/)
- [Community Discussion](https://community.sonarsource.com/t/code-coverage-0-in-sonarcloud/115369)

## Best Practices (Industry Standard)

### 1. Always Pass Coverage Paths Explicitly
```yaml
-Dsonar.python.coverage.reportPaths=coverage.xml
-Dsonar.coverage.jacoco.xmlReportPaths=coverage.xml
```

### 2. Verify Coverage File Exists Before Scan
The workflow should generate `coverage.xml` before SonarCloud runs:
```yaml
- name: Run unit tests with coverage
  run: make test-unit  # This generates coverage.xml

- name: SonarCloud Scan
  uses: sonarsource/sonarcloud-github-action@v3.1
  # ... with coverage report paths
```

### 3. Use Python-Specific Report Path
For Python projects, use:
- `sonar.python.coverage.reportPaths` - Python coverage (pytest-cov XML format)

JaCoCo (`sonar.coverage.jacoco.xmlReportPaths`) is Java-specific and not needed for Python projects.

## Verification

After deploying this fix:
1. Open a PR
2. Check GitHub Actions logs for: `Processing coverage reports`
3. Verify SonarCloud shows actual coverage percentage

## Related Files

- `.github/workflows/ci.yml` - Added coverage report paths
- `sonar-project.properties` - Already configured (kept for documentation)
- `scripts/test/unit.sh` - Generates `coverage.xml`

## Summary

**The Fix**: Add `-Dsonar.python.coverage.reportPaths=coverage.xml` to GitHub Actions workflow.

**Why It Works**: GitHub Action doesn't automatically read `sonar-project.properties` - must pass config via `args:`.

**Industry Standard**: Explicit configuration in CI/CD pipelines (not relying on properties file).

