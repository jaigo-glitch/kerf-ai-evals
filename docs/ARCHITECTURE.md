# Architecture and threat model

## Components

| Component | Responsibility | Trust level |
|---|---|---|
| FastAPI API | Validation, orchestration, downloads | Trusted application code |
| Model provider | Produces structured answer and SQL | Untrusted output |
| Case registry | Versioned questions and expected evidence | Trusted, reviewed source |
| Business database | Synthetic read-only test fixture | Trusted data |
| Safe SQL executor | Enforces query policy and resource limits | Security boundary |
| Scorer | Compares database rows and answer facts | Trusted evaluation code |
| History database | Stores runs, feedback, issues, releases | Trusted local state |

The synthetic business database and writable history database are deliberately separate files. A generated query is never run against the history database.

## Scoring

- 75 points: the generated query returns the same normalized rows as the expected query.
- 20 points: the human-readable answer contains the case's required facts.
- 5 points: a non-empty explanation is present.
- Passing requires both a result match and a score of at least 85.

This design prevents persuasive prose from passing when the underlying query is wrong.

## Current threats and controls

| Threat | Current control | Remaining risk |
|---|---|---|
| Destructive SQL | lexical blocklist, read-only URI, query-only mode, SQLite authorizer | Parser differentials; production needs database-level least privilege |
| Multi-statement injection | comments and internal semicolons rejected | Very unusual SQLite parsing edge cases |
| Expensive query | VM step limit and output row limit | Some resource usage remains possible before interruption |
| Data exfiltration | allowlisted tables, local synthetic data | Production tenant isolation is not implemented |
| Prompt injection | fixed versioned questions and fixed schema | User-uploaded documents are not supported yet |
| False product claims | fixture/live labels and synthetic-data notices | Public copy still requires human review |

## Production hardening backlog

1. Run query execution in an isolated process or container with CPU and memory limits.
2. Replace SQLite with a dedicated read replica and database account that has explicit `SELECT` grants.
3. Parse SQL into an AST and enforce an allowlist rather than relying partly on lexical checks.
4. Add authentication, tenant isolation, encryption, retention controls, and audit-log integrity.
5. Add adversarial prompt-injection and data-exfiltration cases.
6. Pin live model snapshots after comparison runs establish a release baseline.

