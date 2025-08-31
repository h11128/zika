# Manual Testing Procedures for Compatibility

## Overview

This document outlines manual testing procedures for compatibility testing across browser versions, Streamlit versions, and data formats. These procedures complement automated testing and ensure real-world compatibility.

## Browser Compatibility Testing

### Supported Browsers and Versions

| Browser | Versions | Compatibility Level | Market Share | Notes |
|---------|----------|-------------------|--------------|-------|
| Chrome | 120.0+ | Full | 65% | Primary target |
| Chrome | 119.0-110.0 | Full/Partial | 30% | Good support |
| Chrome | 100.0-109.0 | Minimal | 5% | Basic functionality |
| Firefox | 121.0+ | Full | 8% | Good support |
| Firefox | 115.0-120.0 | Partial | 8% | Some limitations |
| Firefox | 102.0-114.0 | Minimal | 2% | Basic functionality |
| Safari | 17.0+ | Full | 10% | Good support |
| Safari | 16.0 | Partial | 5% | Some limitations |
| Safari | 15.0 | Minimal | 2% | Basic functionality |
| Edge | 120.0+ | Full | 5% | Good support |
| Edge | 110.0-119.0 | Partial | 5% | Some limitations |

### Manual Browser Testing Checklist

#### Pre-Testing Setup
- [ ] Clear browser cache and cookies
- [ ] Disable browser extensions
- [ ] Set browser to default zoom level (100%)
- [ ] Ensure JavaScript is enabled
- [ ] Check browser developer tools for console errors

#### Core Functionality Tests

**1. Application Loading**
- [ ] Application loads without errors
- [ ] All UI components render correctly
- [ ] No JavaScript console errors
- [ ] Loading indicators work properly
- [ ] Page title displays correctly

**2. Data Input and Validation**
- [ ] Chinese character input works correctly
- [ ] Pinyin input with tone marks works
- [ ] English text input works
- [ ] Input validation messages display
- [ ] Character limits are enforced
- [ ] Special characters (emojis, punctuation) work

**3. Local Storage Functionality**
- [ ] Data saves to localStorage
- [ ] Data persists after page refresh
- [ ] Data loads correctly on return visit
- [ ] Storage quota warnings appear when appropriate
- [ ] Data can be cleared/reset

**4. Export Functionality**
- [ ] PDF export works and downloads
- [ ] PowerPoint export works and downloads
- [ ] CSV export works and downloads
- [ ] Export preview displays correctly
- [ ] Export progress indicators work

**5. UI Responsiveness**
- [ ] Layout adapts to different window sizes
- [ ] Mobile viewport works (if applicable)
- [ ] Touch interactions work on touch devices
- [ ] Keyboard navigation works
- [ ] Focus indicators are visible

#### Browser-Specific Tests

**Chrome-Specific**
- [ ] Chrome's autofill doesn't interfere
- [ ] Chrome DevTools work correctly
- [ ] Chrome's download manager handles exports
- [ ] Chrome's security warnings (if any) are appropriate

**Firefox-Specific**
- [ ] Firefox's privacy settings don't block functionality
- [ ] Firefox's download behavior works
- [ ] Firefox's developer tools work
- [ ] Firefox's reader mode doesn't interfere

**Safari-Specific**
- [ ] Safari's Intelligent Tracking Prevention doesn't break functionality
- [ ] Safari's download behavior works
- [ ] Safari's Web Inspector works
- [ ] Safari's private browsing mode works

**Edge-Specific**
- [ ] Edge's tracking prevention doesn't interfere
- [ ] Edge's download manager works
- [ ] Edge's developer tools work
- [ ] Edge's compatibility mode (if enabled) works

### Browser Testing Report Template

```
Browser: [Browser Name] [Version]
OS: [Operating System] [Version]
Date: [Test Date]
Tester: [Tester Name]

Core Functionality:
- Application Loading: [Pass/Fail/Issues]
- Data Input: [Pass/Fail/Issues]
- Local Storage: [Pass/Fail/Issues]
- Export Functions: [Pass/Fail/Issues]
- UI Responsiveness: [Pass/Fail/Issues]

Browser-Specific Tests:
- [Specific Test 1]: [Pass/Fail/Issues]
- [Specific Test 2]: [Pass/Fail/Issues]

Issues Found:
1. [Issue Description]
   - Severity: [Critical/High/Medium/Low]
   - Steps to Reproduce: [Steps]
   - Expected Behavior: [Description]
   - Actual Behavior: [Description]

Overall Compatibility: [Full/Partial/Minimal/Unsupported]
Recommended Action: [Ship/Fix Issues/Not Supported]
```

## Streamlit Version Compatibility Testing

### Supported Streamlit Versions

| Version | Python Req | Compatibility | Known Issues |
|---------|------------|---------------|--------------|
| 1.29.0+ | >=3.8 | Full | None |
| 1.28.0 | >=3.8 | Full | None |
| 1.27.0 | >=3.8 | Full | None |
| 1.26.0 | >=3.8 | Partial | Session state issues |
| 1.25.0 | >=3.8 | Partial | Cache invalidation bugs |
| 1.20.0 | >=3.7 | Minimal | Limited component support |
| 1.15.0 | >=3.7 | Minimal | No session state |

### Manual Streamlit Testing Checklist

#### Environment Setup
- [ ] Create virtual environment for each Streamlit version
- [ ] Install specific Streamlit version
- [ ] Install all required dependencies
- [ ] Verify Python version compatibility
- [ ] Check for dependency conflicts

#### Core Streamlit Features

**1. Session State (Streamlit 1.18.0+)**
- [ ] Session state variables persist across reruns
- [ ] Session state works with user interactions
- [ ] Session state clears appropriately
- [ ] Multiple session state variables work together
- [ ] Session state works with callbacks

**2. Caching**
- [ ] `@st.cache_data` works correctly (1.18.0+)
- [ ] `@st.cache` works correctly (older versions)
- [ ] Cache invalidation works
- [ ] Cache persistence works
- [ ] Cache size limits are respected

**3. Component Rendering**
- [ ] All Streamlit components render correctly
- [ ] Custom components work (if any)
- [ ] Component interactions work
- [ ] Component state management works
- [ ] Component performance is acceptable

**4. File Operations**
- [ ] File uploads work correctly
- [ ] File downloads work correctly
- [ ] File processing works
- [ ] File size limits are enforced
- [ ] File type validation works

#### Version-Specific Tests

**Streamlit 1.29.0+**
- [ ] Latest features work correctly
- [ ] Performance improvements are evident
- [ ] New components work
- [ ] Backward compatibility maintained

**Streamlit 1.25.0-1.28.0**
- [ ] Known cache invalidation bugs are handled
- [ ] Memory leak issues are mitigated
- [ ] Session state issues are worked around

**Streamlit 1.15.0-1.24.0**
- [ ] Limited session state functionality works
- [ ] Alternative state management works
- [ ] Performance limitations are acceptable
- [ ] Feature limitations are documented

### Streamlit Testing Report Template

```
Streamlit Version: [Version]
Python Version: [Version]
OS: [Operating System]
Date: [Test Date]
Tester: [Tester Name]

Environment Setup:
- Installation: [Success/Issues]
- Dependencies: [Success/Issues]
- Conflicts: [None/List Issues]

Core Features:
- Session State: [Pass/Fail/N/A/Issues]
- Caching: [Pass/Fail/Issues]
- Component Rendering: [Pass/Fail/Issues]
- File Operations: [Pass/Fail/Issues]

Performance:
- App Startup Time: [Seconds]
- Page Load Time: [Seconds]
- Memory Usage: [MB]
- CPU Usage: [%]

Known Issues Verification:
- [Issue 1]: [Confirmed/Fixed/Not Applicable]
- [Issue 2]: [Confirmed/Fixed/Not Applicable]

Overall Compatibility: [Full/Partial/Minimal/Unsupported]
Recommended Action: [Support/Limited Support/Not Supported]
```

## Data Format Migration Testing

### Migration Scenarios

#### Real User Data Testing

**1. Small Datasets (1-10 cards)**
- [ ] Empty dataset migration
- [ ] Single card migration
- [ ] Multiple cards migration
- [ ] Special characters preservation
- [ ] Unicode handling

**2. Medium Datasets (10-100 cards)**
- [ ] Performance within acceptable limits
- [ ] Data integrity maintained
- [ ] Memory usage reasonable
- [ ] Progress indicators work

**3. Large Datasets (100+ cards)**
- [ ] Performance benchmarks met
- [ ] Memory efficiency maintained
- [ ] Batch processing works
- [ ] Error handling robust

**4. Edge Cases**
- [ ] Corrupted data handling
- [ ] Missing fields handling
- [ ] Invalid characters handling
- [ ] Empty fields handling
- [ ] Null values handling

#### Migration Path Testing

**Legacy → V1**
- [ ] Format version added correctly
- [ ] Card structure preserved
- [ ] No data loss
- [ ] Validation passes

**Legacy → V2 (Multi-step)**
- [ ] Metadata added correctly
- [ ] Timestamps generated
- [ ] Migration source tracked
- [ ] All intermediate steps successful

**Legacy → V3 (Multi-step)**
- [ ] UUIDs generated for all cards
- [ ] Version numbers assigned
- [ ] Export history initialized
- [ ] Full feature compatibility

**V1 → V2**
- [ ] Metadata enhancement works
- [ ] Existing data preserved
- [ ] Migration tracking works

**V1 → V3 (Multi-step)**
- [ ] Card enhancement works
- [ ] UUID generation works
- [ ] All features available

**V2 → V3**
- [ ] Card enhancement works
- [ ] Export history added
- [ ] Metadata preserved

### Rollback Testing Procedures

#### Rollback Scenarios

**1. Successful Migration Rollback**
- [ ] Backup data is created
- [ ] Rollback restores original data exactly
- [ ] No data corruption
- [ ] Performance acceptable

**2. Failed Migration Rollback**
- [ ] Partial migration is rolled back
- [ ] System returns to stable state
- [ ] Error messages are clear
- [ ] User data is protected

**3. Large Dataset Rollback**
- [ ] Performance within limits
- [ ] Memory usage reasonable
- [ ] Progress indicators work
- [ ] Integrity verification passes

#### Rollback Verification

- [ ] Original data structure restored
- [ ] All original content preserved
- [ ] No additional fields remain
- [ ] Application functions normally
- [ ] User can continue working

### Data Migration Testing Report Template

```
Migration Type: [Legacy→V1/V1→V2/etc.]
Dataset Size: [Number of cards]
Data Characteristics: [Normal/Special chars/Corrupted/etc.]
Date: [Test Date]
Tester: [Tester Name]

Migration Results:
- Success: [Yes/No]
- Duration: [Seconds]
- Data Integrity: [Pass/Fail]
- Performance: [Acceptable/Slow/Fast]

Rollback Testing:
- Rollback Success: [Yes/No]
- Data Restoration: [Complete/Partial/Failed]
- Performance: [Acceptable/Slow/Fast]

Issues Found:
1. [Issue Description]
   - Impact: [Critical/High/Medium/Low]
   - Data Loss: [Yes/No]
   - Workaround: [Available/None]

Verification Steps:
- [ ] Original data compared with migrated data
- [ ] All fields present and correct
- [ ] Special characters preserved
- [ ] Performance benchmarks met
- [ ] Rollback tested and verified

Overall Assessment: [Pass/Fail]
Recommendation: [Deploy/Fix Issues/More Testing]
```

## Testing Environment Setup

### Browser Testing Environment

1. **Physical Devices**
   - Windows 10/11 PC
   - macOS (latest 2 versions)
   - Linux Ubuntu (latest LTS)

2. **Virtual Machines**
   - Windows 10 VM for older browser versions
   - macOS VM for Safari testing
   - Linux VMs for Firefox testing

3. **Browser Installation**
   - Install multiple browser versions
   - Use portable browser versions when possible
   - Document browser configurations

### Streamlit Testing Environment

1. **Python Environments**
   - Use pyenv or conda for version management
   - Create separate environments for each Streamlit version
   - Document dependency versions

2. **Testing Scripts**
   - Automated environment setup scripts
   - Dependency installation scripts
   - Testing execution scripts

### Data Testing Environment

1. **Test Data Sets**
   - Small, medium, large datasets
   - Special character datasets
   - Corrupted data samples
   - Real user data (anonymized)

2. **Backup and Recovery**
   - Automated backup before testing
   - Recovery procedures documented
   - Test data version control

## Reporting and Documentation

### Test Execution Tracking

- Use test management tools (e.g., TestRail, Jira)
- Document all test executions
- Track defects and resolutions
- Maintain compatibility matrix

### Compatibility Matrix Updates

- Update matrix after each testing cycle
- Document version support changes
- Communicate changes to stakeholders
- Plan deprecation timelines

### User Communication

- Publish compatibility requirements
- Provide migration guides
- Document known issues
- Offer support channels

---

**Last Updated**: January 2024  
**Next Review**: April 2024  
**Document Version**: 1.0
