# E2E Test Coverage

## Remaining Coverage Gaps

- `--name-only` for detect-changes command (deferred)

## `get` Command

| Pattern                         | Options                                               | Expected Result                  |
| ------------------------------- | ----------------------------------------------------- | -------------------------------- |
| `w/*`                           | `--name-only`                                         | List of workspace names          |
| `w/*`                           | `--output json`                                       | JSON with all entities           |
| `w/*`                           | `--output yaml`                                       | YAML with all entities           |
| `w/*`                           | `--output table`                                      | Table with borders               |
| `w/*`                           | `--output matrix`                                     | GitHub Actions matrix format     |
| `w/*`                           | `--format-type flat`                                  | Arrays for each entity type      |
| `w/*`                           | `--format-type nested`                                | Hierarchical structure           |
| `w/*`                           | `--format-type grouped`                               | Default grouped format           |
| `w/*`                           | `--format-type flat --name-only`                      | Arrays of names only             |
| `w/*`                           | `--type component`                                    | Only components returned         |
| `w/*`                           | `--type context`                                      | Only contexts returned           |
| `w/*`                           | `--type workspace`                                    | Only workspaces returned         |
| `c/*`                           | `--type workspace`                                    | Error: invalid combination       |
| `cm/*`                          | `--type workspace`                                    | Error: invalid combination       |
| `cm/*`                          | `--filter component.config.active=true`               | Only active components           |
| `cm/*`                          | `--filter component.config.for_commit=true`           | Only for_commit components      |
| `cm/*`                          | `--filter component.config.required=false`            | Only optional components         |
| `w/*`                           | `--filter context.environment=dev`                    | Only dev resources               |
| `w/*`                           | auto-append `/**`                                     | Workspace pattern completion     |
| `c/*`                           | auto-append `/**`                                     | Context pattern completion       |
| `*`                             | `--from-json '[...]'`                                 | Process JSON input               |
| `*`                             | `--json-file input.json`                              | Process JSON file                |
| `cm/prom*`                      | wildcard pattern                                      | Components starting with 'prom'  |
| `c/*-dev`                       | wildcard suffix                                       | Contexts ending with -dev        |
| `c/aws-*-dev`                   | multiple wildcards                                    | Contexts matching pattern        |
| `d/contexts/*`                  | directory pattern                                     | Match by directory               |
| `d/workspaces/*/contexts/*-dev` | directory + wildcard                                  | Combined patterns                |
| `p/workspaces/aws`              | path pattern                                          | Exact path match                 |
| `w/nonexistent`                 | all output formats                                    | Empty results handled gracefully |
| `cm/*`                          | `--include-inactive`                                  | Include inactive components      |
| `w/*`                           | `--include-inactive --filter context.environment=dev` | Combined with filters            |
| `w/*`                           | multiple filters                                      | Complex filter combinations      |

## `generate` Command

| Pattern                 | Options                             | Expected Result                |
| ----------------------- | ----------------------------------- | ------------------------------ |
| `cm/prometheus`         | `--dry-run`                         | Preview only, no files created |
| `cm/prometheus`         | `--output-dir /path`                | Files created in specified dir |
| `cm/*`                  | `--file-action skip`                | Existing files skipped         |
| `cm/*`                  | `--file-action overwrite`           | Existing files replaced        |
| `cm/*`                  | `--file-action archive`             | Existing files backed up       |
| `cm/*`                  | `--dry-run --verbose`               | Detailed preview output        |
| `cm/*`                  | multiple components                 | Batch generation               |
| `context/*/component/*` | old syntax                          | Legacy pattern support         |
| `cm/*`                  | `--filter context.environment=prod` | Generate only prod components  |

## `detect-changes` Command

| Pattern | Options                            | Expected Result              |
| ------- | ---------------------------------- | ---------------------------- | --- |
| `cm/*`  | `--base-ref HEAD~1`                | Changes since last commit    |
| `cm/*`  | ~~`--affected-files list.txt`~~    | NOT IMPLEMENTED - removed    |
| `cm/*`  | `--output json`                    | JSON format output           |
| `cm/*`  | `--output yaml`                    | YAML format output           |
| `cm/*`  | `--output matrix`                  | GitHub Actions matrix        |
| `cm/*`  | `--filter context.environment=dev` | Only dev changes             |
| `cm/*`  | ~~`--rules-file rules.yaml`~~      | NOT IMPLEMENTED - removed    |
| `cm/*`  | default (no args)                  | Basic change detection       |
| `cm/*`  | `--name-only`                      | Component names only         | ⏳  |

## `check-pattern` Command

| Pattern   | Options                                 | Expected Result            |
| --------- | --------------------------------------- | -------------------------- |
| `w/aws`   | none                                    | Pattern analysis table     |
| `c/*dev*` | `--analyze`                             | Detailed pattern breakdown |
| `cm/*`    | `--filter component.config.active=true` | Filtered pattern analysis  |
| `w/*`     | `--output json`                         | Error: table only          |
| `w/*/**`  | recursive patterns                      | Deep pattern matching      |

## `config` Command

| Subcommand        | Options              | Expected Result            |
| ----------------- | -------------------- | -------------------------- |
| `view raw`        | none                 | Raw configuration          |
| `view resolved`   | none                 | Resolved configuration     |
| `view enhanced`   | none                 | Enhanced configuration     |
| `view raw`        | `--output json`      | Raw config as JSON         |
| `view resolved`   | `--output json`      | Resolved config as JSON    |
| `view enhanced`   | `--output json`      | Enhanced config as JSON    |
| `schema`          | none                 | Configuration schema       |
| `schema`          | `--output yaml`      | Schema as YAML             |
| `schema`          | `--output json`      | Schema as JSON             |
| `schema settings` | none                 | Settings schema only       |
| `schema all`      | none                 | Complete schema            |
| `init`            | none                 | Create default config      |
| `init`            | `--force`            | Overwrite existing config  |
| `generate`        | none                 | Create default config file |
| `generate`        | `--name custom.yaml` | Create with custom name    |
| `generate`        | `--force`            | Overwrite existing file    |

## Global Options (All Commands)

| Option                       | Expected Result          |
| ---------------------------- | ------------------------ |
| `--verbose`                  | Debug output to stderr   |
| `--quiet`                    | Minimal output           |
| `--dry-run`                  | Preview mode, no changes |
| `--no-color`                 | No ANSI color codes      |
| `--output format`            | Override default format  |
| `--file-action`              | File handling mode       |
| env: `CG_OUTPUT_FORMAT=json` | Default to JSON          |
| env: `CG_VERBOSE=true`       | Verbose by default       |
| env: `CG_NO_COLOR=true`      | No color by default      |
| env: `CG_DRY_RUN=true`       | Dry run by default       |

## Error Handling Tests

| Scenario                                               | Expected Result           |
| ------------------------------------------------------ | ------------------------- |
| Invalid command syntax                                 | Usage error message       |
| Conflicting options (`--from-json` with pattern)       | Conflict error            |
| Invalid output format                                  | Format error              |
| Invalid filter syntax                                  | Filter syntax error       |
| Invalid pattern prefix                                 | Pattern error             |
| File not found                                         | Not found error           |
| Permission denied                                      | Permission error          |
| Malformed JSON input                                   | Parse error               |
| Type mismatches (e.g., `cm/*` with `--type workspace`) | Invalid combination error |

## Cross-Platform Tests

| Scenario            | Expected Result           |
| ------------------- | ------------------------- |
| Platform detection  | Correct OS identification |
| Spaces in paths     | Handle paths with spaces  |
| Unicode characters  | Support non-ASCII chars   |
| Long path names     | Windows MAX_PATH handling |
| Relative paths      | Correct path resolution   |
| Locale handling     | macOS-specific settings   |
| Terminal dimensions | Adapt to terminal size    |
| JSON Unicode output | Proper encoding           |

## Performance Tests

| Scenario                  | Expected Result       |
| ------------------------- | --------------------- |
| 100+ components           | Sub-second discovery  |
| Large templates           | Efficient generation  |
| Many file changes         | Fast change detection |
| Deep directory nesting    | Good performance      |
| Wide directory structures | Handle many siblings  |

## Installation Tests

| Scenario             | Expected Result        |
| -------------------- | ---------------------- |
| Makefile exists      | Build system present   |
| pyproject.toml valid | Package config correct |
| requirements.txt     | Dependencies listed    |
| Make install         | Installation works     |
| Pip compatibility    | Package installable    |
| Editable install     | Development mode       |
| Version command      | Shows version          |

## Workflow Tests

| Scenario                   | Expected Result          |
| -------------------------- | ------------------------ |
| Config → Init → View       | Complete config workflow |
| Generate → Init            | Config creation flow     |
| Init → Generate components | Full user journey        |
| Config migration           | Update with --force      |
