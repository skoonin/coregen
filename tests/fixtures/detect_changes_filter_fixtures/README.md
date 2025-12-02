# Detect Changes Filter Test Fixtures

This directory contains controlled test data for testing detect-changes filtering functionality.

## Structure

- `base/` - Files representing the base branch state
- `current/` - Files representing the current branch state (with changes)
- `expected_results.json` - Expected results for various filter scenarios

## Test Components

### Workspace: aws
- Context: dev-cluster
  - nginx (active=true, priority=1, required=false)
  - prometheus (active=true, priority=0, required=true)
  - redis (active=false, priority=2, required=false) [DELETED in current]

- Context: prod-cluster
  - nginx (active=true, priority=1, required=true)
  - prometheus (active=true, priority=0, required=true)

### Workspace: local
- Context: dev-env
  - postgres (active=true, priority=2, required=false)
  - redis (active=true, priority=3, required=false) [NEW in current]

- Context: prod-env
  - postgres (active=true, priority=2, required=true)
  - nginx (active=false, priority=1, required=false) [CHANGED in current]

## Expected Changes

1. **DELETED**: aws/dev-cluster/redis (was active=false)
2. **NEW**: local/dev-env/redis
3. **CHANGED**: local/prod-env/nginx (active changed from true to false)
4. **NO CHANGE**: All other components remain the same

## Filter Test Scenarios

1. `component.config.active=true` → Should exclude deleted redis and changed nginx
2. `component.config.active=false` → Should only show changed nginx and deleted redis
3. `component.config.priority=1` → nginx components only
4. `context.environment=dev` → dev-cluster and dev-env components
5. `workspace.name=aws` → aws components only
