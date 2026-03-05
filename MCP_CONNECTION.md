# MCP Connection Guide

## Connection Setup

**URL format:**
```
https://your-domain.com/sse2?api_key=YOUR_API_KEY
```

**API Key location:** Server-side `.env` file only — never committed to git.

```bash
# Generate a new key
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Key rotation:**
1. Update `.env` on server
2. `docker-compose down && docker-compose up -d`
3. Update connection URL in Claude.ai settings

**Test connection:**
```bash
curl -s "https://your-domain.com/sse2?api_key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/list"}'
```

See [SECURITY.md](SECURITY.md) for key management best practices.

---

## Available MCP Tools (18)

### Memory — Read

| Tool | Description |
|------|-------------|
| `search_memory` | Search notes using spreading activation (semantic + graph + BM25 blend). Returns top-k results with relevance scores. |
| `find_similar` | Find notes similar to given content by cosine similarity. Useful before adding to check for duplicates. |
| `get_graph` | Get all graph connections for a specific note ID (semantic links, entity links, temporal chains). |
| `neural_stats` | System statistics: node count, edge count, entities, community structure, top PageRank nodes. |
| `search_stats` | Search quality metrics: latency percentiles, zero-result queries, phase breakdown. |

### Memory — Write

| Tool | Description |
|------|-------------|
| `add_note` | Add a new note. Auto-extracts entities (GLiNER), creates semantic + entity links, checks for duplicates. |
| `update_note` | Update existing note content by ID. Saves previous version to history (up to 5). |
| `delete_note` | Delete a note by ID. Removes all associated edges. |
| `set_importance` | Set note importance: `critical` (2× retrieval boost), `normal`, or `low` (0.5×). |

### Memory — History

| Tool | Description |
|------|-------------|
| `get_note_history` | Get version history for a note (up to 5 versions with timestamps). |
| `restore_note_version` | Restore a note to a specific previous version. |

### Graph Maintenance

| Tool | Description |
|------|-------------|
| `sleep_compute` | Run background graph maintenance: stale edge decay, PageRank recalculation, consolidation, duplicate scan. Use `dry_run=true` to preview without changes. |

### Entity Management

| Tool | Description |
|------|-------------|
| `list_entity_candidates` | List entity merge candidates — case variants like `git`/`Git`/`GIT` grouped by normalized name. Read-only. |
| `merge_entities` | Merge two entity nodes: transfer all links from `remove_id` to `keep_id`, then delete `remove_id`. Irreversible. |

### Anchor Policies

| Tool | Description |
|------|-------------|
| `list_anchor_policies` | Show system-defined (hardcoded, immutable) and user-defined protected categories. Protected notes are exempt from stale edge decay and kept at critical importance. |
| `add_anchor_policy` | Add a custom category to anchor protection. Persists across restarts. |
| `remove_anchor_policy` | Remove a user-defined anchor policy. Cannot remove system baseline categories. |

### Skills

| Tool | Description |
|------|-------------|
| `ingest_skill` | Ingest a skill into memory with security scanning. First call returns preview + scan results. Call again with `confirmed=True` to add. All skills stored as `category=skill, importance=low`. |

---

## Tool Usage Notes

**`search_memory` parameters:**
- `query` (required) — search text
- `limit` — number of results (default 5, max 20)
- `category` — filter by category
- `detail_mode` — `full` (default) or `brief` (first line only)
- `time_after` / `time_before` — ISO datetime filters

**`add_note` parameters:**
- `content` (required)
- `category` — defaults to `general`
- `importance` — `critical`, `normal` (default), `low`
- `emotional_tone`, `emotional_intensity`, `emotional_reflection` — optional emotional metadata
- `force` — bypass duplicate check

**`ingest_skill` flow:**
```
1. ingest_skill(content="...", source="github.com/...")  → shows preview + security scan
2. ingest_skill(content="...", source="...", confirmed=True)  → adds to memory
```
Skills with `CRITICAL` or `HIGH` risk are blocked by default. Use `confirmed=True` only after careful manual review.

**`sleep_compute` — when to run:**
Runs automatically every 50 notes (light sleep) and every 200 notes (deep sleep). Manual trigger useful after bulk imports or entity merges.

---

## Security
- Use HTTPS only
- Never share or commit API keys
- Rotate keys if accidentally exposed (see Key Rotation above)