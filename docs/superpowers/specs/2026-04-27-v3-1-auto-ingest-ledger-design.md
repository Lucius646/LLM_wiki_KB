# V3.1 Auto Ingest Ledger Design

Date: 2026-04-27
Status: Draft approved for planning
Target version: `v3.1.0`

## Goal

Reduce human operation after v3 by letting `ingest` automatically find raw files that need processing.

V3 made `raw/` the user interface and added multimodal raw file support. V3.1 keeps that model and removes the need to manually specify every file. The user drops materials into `raw/`; the system detects new or changed supported files and ingests only those.

## Non-Goals

- Do not call this v4. This is an incremental v3 feature.
- Do not add topic parameters or raw topic classification.
- Do not add directory/batch option matrices.
- Do not add a hidden database.
- Do not add a daemon, watcher, GUI, MCP, RAG, or semantic maintenance pass.
- Do not change the v3 LLM plan -> compile -> audit -> git commit pipeline.

## User Experience

`ingest` with no arguments becomes the default low-intervention command:

```text
ingest
```

Behavior:

- Scan `raw/` recursively for supported v3 formats.
- Compute a content hash for each supported raw file.
- Skip files already recorded with the same hash.
- Ingest files that are new or whose hash changed.
- Print a compact summary of ingested, skipped, and failed files.

Single-file ingest remains supported:

```text
ingest raw/<file>
```

Single-file ingest should also update the ledger after a successful ingest.

## Ledger

The system maintains a visible machine state file:

```text
wiki/ingest-ledger.json
```

This is not a user-edited knowledge file. It is a git-tracked system record, similar in spirit to `wiki/log.md`, but structured for reliable skip/change detection.

Initial shape:

```json
{
  "version": 1,
  "sources": {
    "raw/notes.txt": {
      "sha256": "abc123",
      "last_ingested_at": "2026-04-27T10:30:00+08:00",
      "commit": "15a400e",
      "article_paths": [
        "wiki/concepts/example.md"
      ]
    }
  }
}
```

Required fields:

- `version`: ledger schema version.
- `sources`: map keyed by raw relative path.
- `sha256`: content hash used to detect changes.
- `last_ingested_at`: ISO timestamp.
- `commit`: git commit created by the successful ingest.
- `article_paths`: wiki paths changed by that ingest.

## Data Flow

For `ingest` with no args:

1. Detect active workspace.
2. Read `wiki/ingest-ledger.json`; if missing, treat as empty.
3. Discover supported raw files using the existing v3 raw extension set.
4. Hash each file.
5. Select files whose raw path is missing from the ledger or whose hash changed.
6. Process each selected file through the existing single-file ingest flow.
7. After each successful file ingest, update the ledger and include it in the managed commit.

The conservative first implementation should process files sequentially. If one file fails, continue or stop can be decided in implementation planning, but the result must report the failure clearly.

## Git And Undo

Each successfully ingested raw file can remain one managed ingest commit. This keeps v2/v3 undo semantics simple: `undo` reverts the latest managed ingest.

The ledger update belongs in the same ingest commit as the wiki changes for that raw file. That keeps rollback coherent: reverting an ingest also reverts the ledger entry for that ingest.

## Error Handling

- Missing ledger: initialize in memory and write after the first successful auto ingest.
- Invalid ledger JSON: fail with a clear message and do not ingest.
- Unsupported raw files: ignore during auto scan, same supported extension list as v3.
- No pending files: print a no-op message and do not create a commit.
- Dirty workspace rules remain the same as v3 unless implementation planning identifies a necessary narrow adjustment for the ledger file.

## Testing

Focused tests should cover:

- `ingest` with no args processes a new supported raw file.
- Re-running `ingest` skips unchanged raw files.
- Modifying raw content causes re-ingest.
- Single-file ingest updates the ledger.
- Invalid ledger JSON blocks ingest with a clear error.
- Unsupported raw files are ignored by auto ingest.
- Ledger updates are included in managed git commits.

## Open Questions For Planning

- Whether auto ingest should continue after one file fails or stop immediately.
- Whether `wiki/ingest-ledger.json` should be created during `init` or lazily on first successful ingest.
- Whether summary output should list all skipped files or only counts.
