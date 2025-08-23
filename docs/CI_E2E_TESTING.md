# CI E2E Testing Configuration

## Overview

This document describes the E2E testing configuration in the CI/CD pipeline for the Chinese Learning Cards Generator application.

## CI Pipeline Structure

### Multi-Tier Testing Strategy

#### 1. Smoke Tests (Pull Requests)

- Trigger: Pull requests to main/master branches
- Scope: Critical functionality tests only on Chromium, plus cross-browser smoke on key scenarios
- Duration: ~3–6 minutes
- Tests:
  - Chromium: tests tagged `@critical`
  - Firefox/WebKit: key scenarios (Interleaved Layout, Complex Custom Color)

#### 2. Full E2E Tests (Push to main/master)

- Trigger: Pushes to main/master branches
- Scope: Complete E2E suite on Chromium; cross-browser smoke on key scenarios
- Duration: ~8–12 minutes
- Browsers: Chromium (full), Firefox/WebKit (smoke)

#### 3. Nightly Scheduled Stress

- Trigger: Scheduled (cron)
- Scope: Chromium full suite + `@stress` cases; Firefox/WebKit run key scenarios
- Purpose: Catch flakiness and regressions under heavier load

## Critical Tests (@critical tag)

The following tests are marked as critical and run on every PR:

### Application Health

- `should load without Streamlit errors @critical`
- `should generate cards and preview without errors @critical`

### Basic Functionality

- `should generate cards from Chinese text input @critical`

### File Operations

- `should successfully upload and process valid CSV file @critical`
- `should export cards to PPTX and verify download @critical`

## CI Configuration Details

### Environment Setup

```yaml
- Ubuntu Latest
- Python 3.11
- Node.js 18
- Playwright with Chromium/Firefox/WebKit (per workflow)
```

### Key Features

- **Dependency Caching**: Both pip and npm dependencies are cached
- **Browser Installation**: Chromium/Firefox/WebKit with system dependencies (per workflow)
- **App Startup**: Streamlit app runs on port 8504
- **Health Check**: Waits for app to be ready before testing
- **Artifact Upload**: Test results and reports on failure

### Test Execution

```bash
# PR Smoke Tests
npm run test:ci -- --project=chromium --grep "@critical"
# Cross-browser smoke (key scenarios)
npm run test:ci -- --project=firefox --grep "Interleaved Layout|Complex Custom Color"
npm run test:ci -- --project=webkit --grep "Interleaved Layout|Complex Custom Color"

# Full Test Suite (Chromium)
npm run test:ci -- --project=chromium
# Nightly Stress (Chromium)
npm run test:ci -- --project=chromium --grep "@stress"
```

## Test Reports and Artifacts

### On Test Failure

- **Test Results**: Screenshots, videos, traces
- **Retention**: 7 days
- **Location**: `tests/playwright-ts/test-results/`

### On All Runs

- **HTML Report**: Comprehensive test report
- **Retention**: 30 days
- **Location**: `tests/playwright-ts/playwright-report/`

## Performance Optimizations

### CI-Specific Settings

- **Single Worker**: `--workers=1` for stability
- **Reduced Parallelism**: Prevents resource conflicts
- **Optimized Timeouts**: Balanced for CI environment
- **Selective Browser**: Chromium only for speed

### Caching Strategy

- **Node Modules**: Cached based on package-lock.json
- **Pip Dependencies**: Cached based on requirements.txt
- **Browser Binaries**: Installed with dependencies

## Monitoring and Maintenance

### Success Metrics

- **PR Smoke Tests**: Should complete in < 5 minutes
- **Full Test Suite**: Should complete in < 10 minutes
- **Pass Rate**: Target 100% on main branch
- **Flakiness**: < 5% retry rate

### Failure Handling

- **Automatic Retries**: 2 retries on CI (configured in playwright.config.ts)
- **Artifact Collection**: Screenshots, videos, traces on failure
- **Detailed Logging**: Console output and test execution logs

## Local Development

### Running CI Tests Locally

```bash
# Simulate PR smoke tests
cd tests/playwright-ts
npm run test:ci -- --grep "@critical"

# Simulate full CI run (Chromium)
npm run test:ci -- --project=chromium
# Cross-browser key scenarios
npm run test:ci -- --project=firefox --grep "Interleaved Layout|Complex Custom Color"
npm run test:ci -- --project=webkit --grep "Interleaved Layout|Complex Custom Color"
# Nightly stress (Chromium)
npm run test:ci -- --project=chromium --grep "@stress"
```

### Adding New Critical Tests

1. Add `@critical` tag to test name
2. Ensure test is stable and fast (< 30 seconds)
3. Test covers core functionality
4. Verify in local CI simulation

## Troubleshooting

### Common Issues

1. **App Startup Timeout**: Increase wait time in CI config
2. **Browser Installation**: Check system dependencies
3. **Test Flakiness**: Review test stability and add retries
4. **Resource Limits**: Reduce parallelism or test scope

### Debug Steps

1. Check CI logs for startup errors
2. Review test artifacts for failure details
3. Run tests locally with same configuration
4. Check browser and dependency versions

## Future Enhancements

### Planned Improvements

- **Cross-Browser Testing**: Firefox and Safari support
- **Performance Benchmarks**: Response time monitoring
- **Visual Regression**: Screenshot comparison tests
- **Accessibility Testing**: WCAG compliance checks

### Scaling Considerations

- **Parallel Execution**: When test suite grows
- **Test Sharding**: For faster execution
- **Matrix Testing**: Multiple environments
- **Conditional Execution**: Based on changed files

---

**Last Updated**: December 2024
**Maintained By**: Development Team
**Related Docs**: [E2E_TESTS_DOCUMENTATION.md](E2E_TESTS_DOCUMENTATION.md), [TEST_COVERAGE_REPORT.md](TEST_COVERAGE_REPORT.md)
