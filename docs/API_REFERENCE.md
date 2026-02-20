# API Reference

## MCP Endpoint

**URL:** `/sse`  
**Methods:** `GET`, `POST`  
**Authentication:** API key via URL parameter or Bearer token

### Authentication

```bash
# URL parameter
curl "http://localhost:5001/sse?api_key=YOUR_KEY" ...

# Bearer token
curl -H "Authorization: Bearer YOUR_KEY" http://localhost:5001/sse ...
```

---

## Tools

### search_memory

Search through notes using blend scoring (semantic similarity + spreading activation) with context window protection.

**Scoring:** `final_score = α × semantic_similarity + (1-α) × spreading_activation` where α=0.7 by default (configurable via BLEND_ALPHA env var).

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| query | string | yes | - | Search query |
| limit | integer | no | 5 | Max results (1-20) |
| max_results | integer | no | 10 | Hard limit on results (prevents context overflow) |
| detail_mode | string | no | "full" | "brief" (first line + metadata) or "full" (complete content) |
| category | string | no | - | Filter by category (e.g., "breakthrough", "technical") |
| time_after | string | no | - | Only notes after this datetime (ISO format) |
| time_before | string | no | - | Only notes before this datetime (ISO format) |
| entity_type | string | no | - | Only notes with entities of this type (e.g., "person", "tech") |

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "search_memory",
    "arguments": {
      "query": "machine learning projects",
      "limit": 5,
      "detail_mode": "brief",
      "category": "technical"
    }
  }
}
```

**Response includes metadata:**
- `total_activated` — total nodes activated by spreading activation
- `returned` — number of results returned
- `estimated_tokens` — approximate token count for context budgeting
- `has_more` — whether more results are available

---

### add_note

Add new note with automatic entity extraction and linking.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| content | string | yes | - | Note content |
| category | string | no | "general" | Category tag |
| importance | string | no | "normal" | "critical", "normal", or "low" — affects search ranking |
| force | boolean | no | false | Force add even if duplicate detected (>95% similarity) |
| emotional_tone | string | no | - | Keywords describing emotional context (e.g., "joy, pride") |
| emotional_intensity | integer | no | 5 | Emotional intensity 0-10 |
| emotional_reflection | string | no | - | Narrative reflection on emotional context |

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "add_note",
    "arguments": {
      "content": "Started working on neural network optimization",
      "category": "project"
    }
  }
}
```

---

### update_note

Update existing note by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| note_id | integer | yes | Note ID |
| content | string | yes | New content |
| category | string | no | New category |

---

### delete_note

Delete note by ID.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| note_id | integer | yes | Note ID |

---

### neural_stats

Get statistics about stored notes, edges, and entities.

**Parameters:** None

**Response:**
```
📊 Neural Memory Graph Statistics

Total nodes: 150
Total edges: 420
Total entities: 85

Nodes by category:
  - general: 80
  - project: 45
  - reference: 25

Edges by type:
  - semantic: 300
  - entity: 120
```

---

### get_graph

Get graph connections for a specific note.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| note_id | integer | yes | Note ID |

---

### set_importance

Set importance level for a note to boost its search ranking.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| note_id | integer | yes | Note ID |
| importance | string | yes | Importance level: 'critical', 'normal', or 'low' |

**Importance Levels:**
- **critical** — 2x activation boost (high-priority information)
- **normal** — 1x activation (default)
- **low** — 0.5x activation (background information)

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "set_importance",
    "arguments": {
      "note_id": 42,
      "importance": "critical"
    }
  }
}
```

**Response:**
```
✅ Note #42 importance set to 'critical' (2.0x activation)
```

---

### find_similar

Find notes similar to given content before adding duplicates.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| content | string | yes | - | Content to check for similarity |
| limit | integer | no | 5 | Max similar notes to return |
| threshold | float | no | 0.7 | Minimum similarity (0-1) |

**Example:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "find_similar",
    "arguments": {
      "content": "Working on neural network optimization",
      "limit": 3,
      "threshold": 0.85
    }
  }
}
```

**Response:**
```
Found 2 similar notes (threshold: 85%):

[#38] similarity: 92%
Started neural net optimization experiments

[#51] similarity: 87%
Optimizing deep learning model performance
```

**Use with add_note:**
The `add_note` tool automatically checks for duplicates:
- **>95% similarity** — Blocks addition, returns existing note
- **>90% similarity** — Warns but allows with `force: true` parameter
- **<90% similarity** — Adds normally

---

## Health Check

**URL:** `/health`  
**Method:** `GET`  
**Authentication:** None required

```bash
curl http://localhost:5001/health
# {"status": "ok", "version": "2.0.0"}
```

## Entity Extraction

### Overview

Notes are automatically analyzed to extract entities (people, organizations, locations, concepts, technologies). Entities create connections between related notes in the knowledge graph.

### Extraction Methods

**regex (default):**
- Fast, no dependencies
- Pattern-based matching
- Detects: tech terms, @mentions, #hashtags, URLs, CamelCase names
- Customizable via `KNOWN_ENTITIES` dictionary

**spacy (recommended):**
- Advanced NER (Named Entity Recognition)
- Detects: PERSON, ORG, GPE (locations), PRODUCT, DATE, etc.
- Requires: `pip install spacy` + `python -m spacy download en_core_web_sm`
- Enable: Set `ENTITY_EXTRACTOR=spacy` in `.env`

### Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| person | People, authors | "Einstein", "Claude", "@username" |
| organization | Companies, institutions | "MIT", "Anthropic", "NASA" |
| location | Places, cities, countries | "Santiago", "California", "Europe" |
| tech | Technologies, frameworks | "Python", "Docker", "React" |
| concept | Abstract ideas | "machine learning", "optimization" |
| product | Products, tools | "Mac Studio", "GPT-4" |
| temporal | Dates, times | "2026", "January", "yesterday" |
| tag | User hashtags | "#research", "#important" |
| url | Web domains | "github.com", "arxiv.org" |

### Example: Entity Extraction with spaCy

**Input Note:**
```
Alice works at TechCorp in Berlin. 
She's developing a knowledge graph using Python and Docker.
```

**Extracted Entities:**
```
- Alice → person
- TechCorp → organization
- Berlin → location
- Python → tech (from KNOWN_ENTITIES)
- Docker → tech (from KNOWN_ENTITIES)
- knowledge → concept
- graph → concept
```

**Graph Connections Created:**
- All notes mentioning "Python" are linked
- All notes about "TechCorp" connect
- Geographic notes about "Berlin" cluster together

