# Graph Features Guide

## Overview

Neural Memory v2 uses a **graph-based architecture** to automatically discover and maintain relationships between your notes. This goes beyond simple keyword matching to understand semantic connections.

---

## Core Concepts

### 1. Nodes (Notes)
Each note becomes a node in the knowledge graph with:
- **Content** — The actual note text
- **Embedding** — 384-dimensional semantic vector
- **Category** — Organizational label
- **Access tracking** — Usage patterns

### 2. Edges (Connections)
Relationships between notes with:
- **Weight** — Connection strength (0.0-1.0)
- **Type** — Connection reason (semantic, entity-based)
- **Bidirectional** — A→B and B→A both tracked

### 3. Entities (Extracted Concepts)
Automatically identified from note content:
- **People** — Names mentioned in notes
- **Concepts** — Technical terms, ideas
- **Projects** — Specific project names
- **Technology** — Tools, frameworks, languages

---

## How It Works

### Adding a Note

```
1. Note created
   ↓
2. Generate semantic embedding (384D vector)
   ↓
3. Extract entities (people, concepts, tech)
   ↓
4. Find similar notes (cosine similarity > threshold)
   ↓
5. Find notes sharing entities
   ↓
6. Create weighted edges for connections
```

### Searching

**Traditional Keyword Search:**
```
Query: "docker container"
Matches: Notes containing exact words
```

**Semantic Graph Search (v2):**
```
Query: "docker container"
   ↓
1. Generate query embedding
   ↓
2. Find similar note embeddings (vector similarity)
   ↓
3. Apply spreading activation along graph edges
   ↓
4. Blend scoring: final = α×semantic + (1-α)×activation
   ↓
5. Apply importance boost + temporal decay
   ↓
Results: Related concepts like "kubernetes pod", "container orchestration"
```

---

## Spreading Activation Algorithm

A technique borrowed from cognitive science to model associative memory.

### How It Works

1. **Initial activation** — Query matches set activation=1.0
2. **Spread to neighbors** — Connected notes receive proportional activation
3. **Decay** — Activation decreases with distance
4. **Threshold** — Weak activations filtered out

### Example

```
Query: "Python debugging"
   ↓
Direct matches (activation=1.0):
  - "Using pdb for Python debugging"
   
Connected via entities (activation=0.7):
  - "Python logging best practices" (shares entity: Python)
  - "VSCode debugger configuration" (shares entity: debugging)
   
Second-degree connections (activation=0.4):
  - "FastAPI error handling" (connected via Python)
```

### Benefits

- Discovers **related but not obvious** connections
- Finds notes through **association chains**
- Mimics how **human memory** works (one thought triggers related thoughts)

---

## Blend Scoring

Spreading activation alone suffers from **hub dominance** — notes with many entity connections accumulate activation regardless of query relevance. Blend scoring solves this by combining semantic similarity with graph activation.

### Formula

```
final_score = α × semantic_similarity + (1-α) × spreading_activation
```

- **α = 0.7** (default) — 70% weight on semantic meaning, 30% on graph connections
- Both components normalized to 0-1 range before blending
- Configurable via `BLEND_ALPHA` environment variable

### Why It Works

```
Query: "spaCy NER entity extraction"

Without blend (pure spreading activation):
  ❌ Top results: generic milestone notes with many connections
  ❌ Actual NER note buried at position #8

With blend (α=0.7):
  ✅ Top-1: SKILL LEARNED entity-extraction (high semantic match)
  ✅ Top-5: All NER-related notes
```

### Tuning α

| Value | Behavior | Best for |
|-------|----------|----------|
| 1.0 | Pure semantic search | Precise factual queries |
| 0.7 | Semantic-heavy blend (default) | General use, balanced relevance |
| 0.5 | Equal blend | Exploratory, discover connections |
| 0.3 | Activation-heavy | Associative recall, brainstorming |
| 0.0 | Pure spreading activation | Graph exploration |

### Entity-Count Penalty

Notes with many entities (>20) tend to be generic summaries that connect to everything. A linear penalty suppresses them:

```
if entity_count > 20:
    score *= 20.0 / entity_count
```

| Entities | Penalty | Effect |
|----------|---------|--------|
| ≤20 | None | Normal scoring |
| 25 | ×0.80 | Mild suppression |
| 30 | ×0.67 | Moderate |
| 42 | ×0.48 | Strong suppression |

---

## Entity Extraction

### What Gets Extracted

**People:**
```
"Discussed API design with Sarah"
→ Entity: Sarah (type: person)
```

**Technical Terms:**
```
"Implemented Redis caching for sessions"
→ Entities: Redis (tech), caching (concept), sessions (concept)
```

**Projects:**
```
"Fixed bug in ProjectAlpha dashboard"
→ Entity: ProjectAlpha (project)
```

### Entity-Based Connections

Notes sharing entities get automatic connections:

```
Note A: "Meeting with John about Q4 roadmap"
Note B: "John suggested using microservices"

→ Edge created (weight based on entity importance)
```

---

## Graph Metrics

### Available Statistics

- **Node count** — Total notes in graph
- **Edge count** — Total connections
- **Entity count** — Unique entities extracted
- **Average connections** — Mean edges per node
- **Clustering coefficient** — How interconnected the graph is

### Using Metrics

```python
# Via MCP tool
neural_stats()

# Returns:
{
  "nodes": 150,
  "edges": 420,
  "entities": 85,
  "avg_connections": 2.8,
  "categories": {"work": 80, "personal": 70}
}
```

---

## Practical Applications

### 1. Project Context Retention

```
Add notes about:
- Architecture decisions
- Why certain approaches were chosen
- What was tried and didn't work

Result: AI assistant remembers full context across sessions
```

### 2. Research Knowledge Base

```
Add notes about:
- Paper summaries
- Key findings
- Methodology notes

Result: Discover related research through semantic connections
```

### 3. Learning Journal

```
Add notes about:
- Concepts learned
- Questions that arose
- "Aha!" moments

Result: See how ideas connect and build on each other
```

---

## Configuration

### Similarity Threshold
Controls when semantic edges are created:

```python
# .env
SIMILARITY_THRESHOLD=0.6  # 0.0-1.0

# Higher = fewer, stronger connections
# Lower = more, weaker connections
```

### Entity Extraction
Enable/disable automatic extraction:

```python
# .env
ENABLE_ENTITY_EXTRACTION=true
ENTITY_MIN_CONFIDENCE=0.7
```

---

## Performance Considerations

### Embedding Generation
- Takes ~50-100ms per note
- Cached after first generation
- Recomputed only when content changes

### Graph Operations
- Edge creation: O(n) where n = existing notes
- Search with spreading activation: O(k) where k = result size
- Scales well to 10,000+ notes

### Memory Usage
- Base: ~2GB (embedding model)
- Per 1000 notes: ~50MB (embeddings + graph)
- Total for 10k notes: ~2.5GB RAM

---

## Limitations

### What It's Not

- **Not a full graph database** — SQLite backend, not Neo4j
- **Not real-time collaborative** — Single-user design
- **Not a search engine** — Personal knowledge management focus

### Known Issues

- Very short notes (<10 words) may not extract meaningful entities
- Entities in non-English text may not be recognized
- Graph can get dense with 50,000+ notes (performance degradation)

---

## Future Enhancements

Potential improvements for future versions:

- ~~Graph visualization dashboard~~ ✅ Implemented (D3.js interactive viewer)
- Community detection (topic clusters)
- Temporal edges (time-based connections)
- Multi-language entity extraction
- Export to graph formats (GraphML, GEXF)
- Entity-count penalty for hub suppression

---

## Technical Details

### Database Schema

```sql
-- Nodes table
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    content TEXT,
    category TEXT,
    timestamp TEXT,
    embedding BLOB,
    last_accessed TEXT,
    access_count INTEGER
);

-- Edges table
CREATE TABLE edges (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    weight REAL,
    edge_type TEXT,
    created_at TEXT
);

-- Entities table
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    entity_type TEXT
);

-- Linking table
CREATE TABLE node_entities (
    node_id INTEGER,
    entity_id INTEGER,
    PRIMARY KEY (node_id, entity_id)
);
```

### Algorithms

**Cosine Similarity:**
```python
similarity = dot(embedding_a, embedding_b) / (norm(a) * norm(b))
```

**Spreading Activation:**
```python
for edge in node.edges:
    neighbor.activation += node.activation * edge.weight * decay_factor
```

**Blend Scoring:**
```python
# Normalize activations to 0-1 range
max_act = max(activations.values())
normalized = {k: v/max_act for k, v in activations.items()}

# Blend with semantic similarity
alpha = float(os.getenv("BLEND_ALPHA", "0.7"))
final_score = alpha * semantic_sim + (1 - alpha) * normalized_activation
```

---

For implementation details, see source code in `src/graph_engine.py`.
