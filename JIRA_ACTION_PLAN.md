# Jira Update Action Plan

## Current Jira Structure

### Existing Items
- **LED-46**: Zephyr→qTest Adoption Intelligence System (Epic)
- **LED-47**: Phase 1: Identity Resolution & Crosswalk
- **LED-48**: Phase 2: Canonical Data Model
- **LED-49**: Phase 3: Adoption Metrics Engine
- **LED-50**: Phase 4: Training Impact Model
- **LED-51**: Phase 6: Daily Report Generator

### Issues with Current Structure
- These tasks are for adoption intelligence features
- We added this code but it's not our core focus
- Real focus should be on lean metrics and platform automation

## Proposed Jira Updates

### 1. Update LED-46 Epic
**New Title**: LedZephyr Platform Transformation
**Description**: Transform LedZephyr into a lean, platform-automated metrics tool

### 2. Close or Defer LED-47 to LED-51
Mark as "Won't Do" with comment:
"Adoption intelligence features deferred. Focus shifted to core metrics and platform automation."

### 3. Create New Stories Under LED-46

#### LED-52: Remove Unused Code Modules
- Remove adoption_metrics.py
- Remove adoption_report.py
- Remove identity_resolution.py
- Remove training_impact.py
- Remove migrate_specs package if unused
- Update all imports

#### LED-53: Refactor Complex Files
- Split/simplify exporters.py (726 → <300 lines)
- Streamline error_handler.py (533 → <200 lines)
- Simplify validators.py (523 → <200 lines)

#### LED-54: Fix Code Quality Issues
- Resolve ruff linting (161 errors)
- Fix mypy type annotations
- Address bandit security warnings
- Achieve 60% test coverage

#### LED-55: Setup Jira Automation
- Configure smart commits
- Create automation rules
- Set up webhooks for GitHub/GitLab

#### LED-56: Configure Platform Integration
- Connect GitHub/GitLab to Jira
- Set up Rovo AI agents
- Create automation dashboards

## Execution Order

### Sprint 1 (This Week)
1. LED-52: Remove unused code
2. LED-53: Start refactoring complex files

### Sprint 2 (Next Week)
1. LED-53: Complete refactoring
2. LED-54: Fix code quality issues

### Sprint 3 (Following Week)
1. LED-55: Setup Jira automation
2. LED-56: Configure platform integration

## Success Criteria

### Code Metrics
- Lines of code: <3,000 (from 5,780)
- Files: <15 (from 20+)
- Max file size: <300 lines
- Test coverage: 60%+
- Zero linting errors

### Platform Metrics
- All commits auto-linked to Jira
- Automated status transitions working
- Rovo agents configured and running
- Zero manual processes

## Manual Steps Required

Since we can't connect to Jira API right now:

1. **In Jira**:
   - Edit LED-46 epic title and description
   - Close LED-47 to LED-51 as "Won't Do"
   - Create LED-52 to LED-56 as new stories
   - Set sprint assignments

2. **In GitHub/GitLab**:
   - Configure Jira integration in settings
   - Add webhook URLs from Jira
   - Test smart commits

3. **In Confluence**:
   - Update project status page
   - Document new architecture
   - Create Rovo agent specs