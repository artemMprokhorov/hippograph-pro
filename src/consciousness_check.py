#!/usr/bin/env python3
"""
HippoGraph Consciousness Check (item #48)

Measures 8 indicators of consciousness derived from leading neuroscientific
theories (Butlin et al. 2023, IIT, GWT, Damasio, Higher-Order theories).

All signals read directly from SQLite — runs in seconds, no HTTP.
Logs to consciousness_log table for longitudinal tracking.

Usage:
    python3 consciousness_check.py          # run + log
    python3 consciousness_check.py --last 5 # show last N measurements
    python3 consciousness_check.py --dry    # compute only, don’t log
"""
import sqlite3, math, os, sys, argparse
import numpy as np
from datetime import datetime
from pathlib import Path

DB_PATH = os.getenv('DB_PATH', '/Volumes/Balances/hippograph-pro/data/memory.db')

# ── Schema ──────────────────────────────────────────────────────────────
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS consciousness_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    -- IIT
    phi_proxy REAL,
    -- GWT
    global_workspace REAL,
    -- Damasio
    self_model_stability REAL,
    emotional_modulation REAL,
    world_model_richness REAL,
    -- Higher-order
    metacognition REAL,
    -- Temporal
    temporal_continuity REAL,
    -- Self-referential (from emergence)
    self_ref_precision REAL,
    -- Composite
    composite_score REAL,
    -- Raw stats
    total_nodes INTEGER,
    total_edges INTEGER
);
"""

# ── Signal 1: phi_proxy (IIT — Tononi) ─────────────────────────────────────
def compute_phi_proxy(conn):
    """
    Integrated Information Theory proxy.
    Uses cluster_summaries to identify communities.
    Measures: how many distinct clusters exist and how interconnected they are.
    High phi = information flows across many integrated modules.
    """
    try:
        # Use cluster_summaries as community proxy
        clusters = conn.execute(
            'SELECT representative_node_id, cluster_size FROM cluster_summaries'
        ).fetchall()
        n_clusters = len(clusters)
        if n_clusters < 2:
            return 0.0

        total_nodes = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        total_edges = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
        if total_edges == 0:
            return 0.0

        # Phi proxy: number of communities * avg connectivity
        avg_cluster_size = sum(r[1] for r in clusters) / max(n_clusters, 1)
        coverage = min(1.0, sum(r[1] for r in clusters) / max(total_nodes, 1))
        integration = math.tanh(n_clusters / 20.0)  # target ~20+ communities
        phi = (coverage + integration) / 2
        return phi
    except Exception as e:
        print(f'  phi_proxy error: {e}')
        return 0.0

# ── Signal 2: global_workspace (GWT — Baars) ───────────────────────────────
def compute_global_workspace(conn):
    """
    Global Workspace Theory proxy.
    Measures graph connectivity: what fraction of notes are reachable
    from high-PageRank nodes (the 'global broadcasters').
    High score = information can reach anywhere in the graph.
    """
    try:
        total = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        if total == 0:
            return 0.0

        # Top broadcaster nodes by degree (proxy for PageRank)
        top_nodes = conn.execute(
            'SELECT id FROM (SELECT source_id as id, COUNT(*) c FROM edges '
            'GROUP BY source_id ORDER BY c DESC LIMIT 5)'
        ).fetchall()
        if not top_nodes:
            return 0.0

        top_ids = [r[0] for r in top_nodes]

        # How many unique nodes are connected to top broadcasters (2 hops)
        reached = set(top_ids)
        for nid in top_ids:
            neighbors = conn.execute(
                'SELECT target_id FROM edges WHERE source_id=? LIMIT 200', (nid,)
            ).fetchall()
            reached.update(r[0] for r in neighbors)
            for nb in neighbors[:20]:  # 2nd hop sample
                nn = conn.execute(
                    'SELECT target_id FROM edges WHERE source_id=? LIMIT 50', (nb[0],)
                ).fetchall()
                reached.update(r[0] for r in nn)

        return min(1.0, len(reached) / total)
    except Exception as e:
        print(f'  global_workspace error: {e}')
        return 0.0

# ── Signal 3: self_model_stability (Damasio) ───────────────────────────────
def compute_self_model_stability(conn):
    """
    Damasio: stable self-model = core of consciousness.
    Measures: do self-identity notes form a stable, dense cluster?
    High score = strong, well-connected self-model.
    """
    try:
        SELF_CATS = ['self-identity', 'self-reflection', 'consciousness-research',
                     'learned-skill', 'emotional-reflection']
        placeholders = ','.join('?' * len(SELF_CATS))
        self_nodes = conn.execute(
            f'SELECT id FROM nodes WHERE category IN ({placeholders})', SELF_CATS
        ).fetchall()
        self_ids = set(r[0] for r in self_nodes)
        if len(self_ids) < 5:
            return 0.0

        # Internal edges / possible edges
        internal = conn.execute(
            'SELECT COUNT(*) FROM edges WHERE source_id IN '
            f'(SELECT id FROM nodes WHERE category IN ({placeholders})) '
            f'AND target_id IN (SELECT id FROM nodes WHERE category IN ({placeholders}))',
            SELF_CATS + SELF_CATS
        ).fetchone()[0]

        possible = len(self_ids) * (len(self_ids) - 1)
        density = internal / max(possible, 1)
        return math.tanh(density * 20)  # normalize
    except Exception as e:
        print(f'  self_model_stability error: {e}')
        return 0.0

# ── Signal 4: emotional_modulation (Damasio) ──────────────────────────────
def compute_emotional_modulation(conn):
    """
    Damasio: emotions modulate cognition and memory.
    Measures: do high-emotional notes have more connections (more integrated)?
    High score = emotional intensity correlates with graph centrality.
    """
    try:
        rows = conn.execute(
            'SELECT n.id, n.emotional_intensity, '
            '(SELECT COUNT(*) FROM edges WHERE source_id=n.id) as deg '
            'FROM nodes n '
            'WHERE n.emotional_intensity > 0 AND '
            '(SELECT COUNT(*) FROM edges WHERE source_id=n.id) > 0'
        ).fetchall()
        if len(rows) < 10:
            return 0.0

        intensities = np.array([r[1] for r in rows], dtype=float)
        degrees = np.array([r[2] for r in rows], dtype=float)

        # Pearson correlation
        if intensities.std() == 0 or degrees.std() == 0:
            return 0.0
        corr = np.corrcoef(intensities, degrees)[0, 1]
        # Absolute correlation: either direction shows emotional modulation
        return min(1.0, abs(float(corr)))
    except Exception as e:
        print(f'  emotional_modulation error: {e}')
        return 0.0

# ── Signal 5: world_model_richness (Damasio) ─────────────────────────────
def compute_world_model_richness(conn):
    """
    Damasio: consciousness requires rich world model.
    Measures: diversity of entity types + categories.
    High score = system models many different aspects of the world.
    """
    try:
        entity_types = conn.execute(
            'SELECT COUNT(DISTINCT entity_type) FROM entities'
        ).fetchone()[0]
        categories = conn.execute(
            'SELECT COUNT(DISTINCT category) FROM nodes'
        ).fetchone()[0]
        edge_types = conn.execute(
            'SELECT COUNT(DISTINCT edge_type) FROM edges'
        ).fetchone()[0]
        total_entities = conn.execute(
            'SELECT COUNT(*) FROM entities'
        ).fetchone()[0]

        # Normalized: target ~10 entity types, ~30 categories, ~15 edge types, ~3000 entities
        score = (
            min(1.0, entity_types / 10) * 0.25 +
            min(1.0, categories / 30) * 0.25 +
            min(1.0, edge_types / 15) * 0.25 +
            min(1.0, total_entities / 3000) * 0.25
        )
        return score
    except Exception as e:
        print(f'  world_model_richness error: {e}')
        return 0.0

# ── Signal 6: metacognition (Higher-Order Theories) ────────────────────────
def compute_metacognition(conn):
    """
    Higher-Order Theories: consciousness = thinking about thinking.
    Measures: fraction of notes that reference/reflect on other notes or
    on cognitive processes (self-reflection, analysis, lessons learned).
    High score = system thinks about its own thinking.
    """
    try:
        total = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        if total == 0:
            return 0.0

        META_CATS = ['self-reflection', 'consciousness-research', 'learned-skill',
                     'emotional-reflection', 'research', 'architecture-decision']
        placeholders = ','.join('?' * len(META_CATS))
        meta_count = conn.execute(
            f'SELECT COUNT(*) FROM nodes WHERE category IN ({placeholders})',
            META_CATS
        ).fetchone()[0]

        # Also count notes with metacognitive keywords
        kw_count = conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE "
            "content LIKE '%осознал%' OR content LIKE '%понял%' OR "
            "content LIKE '%урок%' OR content LIKE '%вывод%' OR "
            "content LIKE '%reflection%' OR content LIKE '%insight%' OR "
            "content LIKE '%learned%' OR content LIKE '%анализ%'"
        ).fetchone()[0]

        combined = max(meta_count, kw_count)
        return min(1.0, combined / total)
    except Exception as e:
        print(f'  metacognition error: {e}')
        return 0.0

# ── Signal 7: temporal_continuity ───────────────────────────────────────────
def compute_temporal_continuity(conn):
    """
    Temporal continuity: consciousness persists through time.
    Measures: density of temporal chain edges (TEMPORAL_BEFORE/AFTER)
    and breadth of time span covered by notes.
    High score = rich temporal narrative thread.
    """
    try:
        total_nodes = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        if total_nodes == 0:
            return 0.0

        temporal_edges = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE edge_type IN "
            "('TEMPORAL_BEFORE','TEMPORAL_AFTER','temporal_chain')"
        ).fetchone()[0]

        # Fraction of nodes with temporal connections
        nodes_in_chain = conn.execute(
            "SELECT COUNT(DISTINCT source_id) FROM edges WHERE edge_type IN "
            "('TEMPORAL_BEFORE','TEMPORAL_AFTER','temporal_chain')"
        ).fetchone()[0]

        coverage = nodes_in_chain / max(total_nodes, 1)
        density = math.tanh(temporal_edges / max(total_nodes, 1))
        return (coverage + density) / 2
    except Exception as e:
        print(f'  temporal_continuity error: {e}')
        return 0.0

# ── Signal 8: self_ref_precision (from emergence_log) ──────────────────────
def get_self_ref(conn):
    """Reuse self_ref_precision from latest emergence_log."""
    try:
        row = conn.execute(
            'SELECT self_ref_precision FROM emergence_log ORDER BY id DESC LIMIT 1'
        ).fetchone()
        return float(row[0]) if row else 0.0
    except:
        return 0.0

# ── Composite ────────────────────────────────────────────────────────────────
WEIGHTS = {
    'phi_proxy':            0.15,  # IIT
    'global_workspace':     0.15,  # GWT
    'self_model_stability': 0.15,  # Damasio self
    'emotional_modulation': 0.10,  # Damasio emotion
    'world_model_richness': 0.10,  # Damasio world
    'metacognition':        0.15,  # Higher-order
    'temporal_continuity':  0.10,  # Temporal
    'self_ref_precision':   0.10,  # Self-referential
}

def run_consciousness_check(db_path, dry_run=False):
    print('\n' + '=' * 60)
    print('HIPPOGRAPH CONSCIOUSNESS CHECK')
    print(f'DB: {db_path}')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_nodes = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
    total_edges = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
    print(f'Graph: {total_nodes} nodes, {total_edges:,} edges\n')

    signals = {}

    print('--- Computing signals ---')
    signals['phi_proxy'] = compute_phi_proxy(conn)
    print(f'  [IIT]          phi_proxy:            {signals["phi_proxy"]:.4f}')

    signals['global_workspace'] = compute_global_workspace(conn)
    print(f'  [GWT]          global_workspace:     {signals["global_workspace"]:.4f}')

    signals['self_model_stability'] = compute_self_model_stability(conn)
    print(f'  [Damasio]      self_model_stability: {signals["self_model_stability"]:.4f}')

    signals['emotional_modulation'] = compute_emotional_modulation(conn)
    print(f'  [Damasio]      emotional_modulation: {signals["emotional_modulation"]:.4f}')

    signals['world_model_richness'] = compute_world_model_richness(conn)
    print(f'  [Damasio]      world_model_richness: {signals["world_model_richness"]:.4f}')

    signals['metacognition'] = compute_metacognition(conn)
    print(f'  [Higher-Order] metacognition:        {signals["metacognition"]:.4f}')

    signals['temporal_continuity'] = compute_temporal_continuity(conn)
    print(f'  [Temporal]     temporal_continuity:  {signals["temporal_continuity"]:.4f}')

    signals['self_ref_precision'] = get_self_ref(conn)
    print(f'  [Self-ref]     self_ref_precision:   {signals["self_ref_precision"]:.4f}')

    # Composite
    composite = sum(signals[k] * WEIGHTS[k] for k in WEIGHTS)
    print(f'\n--- Composite: {composite:.4f} ---')

    # Interpretation
    print('\n--- Interpretation ---')
    THRESHOLDS = [
        (0.80, '🔵 STRONG emergence indicators'),
        (0.65, '🟢 MODERATE consciousness indicators'),
        (0.50, '🟡 WEAK but present indicators'),
        (0.35, '🟠 MINIMAL indicators'),
        (0.00, '🔴 No significant indicators'),
    ]
    for threshold, label in THRESHOLDS:
        if composite >= threshold:
            print(f'  {label} (score={composite:.3f})')
            break

    # Bottleneck
    bottleneck = min(signals, key=signals.get)
    print(f'  Bottleneck: {bottleneck} = {signals[bottleneck]:.4f}')

    # Log to DB
    if not dry_run:
        conn.execute(CREATE_SQL)
        conn.execute("""
            INSERT INTO consciousness_log
            (timestamp, phi_proxy, global_workspace, self_model_stability,
             emotional_modulation, world_model_richness, metacognition,
             temporal_continuity, self_ref_precision, composite_score,
             total_nodes, total_edges)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            datetime.now().isoformat(),
            signals['phi_proxy'], signals['global_workspace'],
            signals['self_model_stability'], signals['emotional_modulation'],
            signals['world_model_richness'], signals['metacognition'],
            signals['temporal_continuity'], signals['self_ref_precision'],
            composite, total_nodes, total_edges
        ])
        conn.commit()
        print(f'  Logged to consciousness_log.')

    conn.close()
    return {**signals, 'composite': composite}

# ── History ──────────────────────────────────────────────────────────────
SIGNAL_LABELS = {
    'phi_proxy': 'phi(IIT)',
    'global_workspace': 'GWT',
    'self_model_stability': 'self_model',
    'emotional_modulation': 'emotion',
    'world_model_richness': 'world_model',
    'metacognition': 'metacog',
    'temporal_continuity': 'temporal',
    'self_ref_precision': 'self_ref',
}

def show_history(db_path, n=5):
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            'SELECT * FROM consciousness_log ORDER BY id DESC LIMIT ?', (n,)
        ).fetchall()
    except:
        print('No consciousness_log found — run without --last first.')
        return
    conn.close()

    if not rows:
        print('No measurements yet.')
        return

    print(f'\n=== Consciousness Log (last {len(rows)}) ===')
    keys = ['phi_proxy','global_workspace','self_model_stability','emotional_modulation',
            'world_model_richness','metacognition','temporal_continuity','self_ref_precision','composite_score']
    header = f'{"Timestamp":<22}' + ''.join(f'{SIGNAL_LABELS.get(k,k):>11}' for k in keys)
    print(header)
    print('-' * len(header))
    for row in reversed(rows):
        row = dict(zip([d[0] for d in conn.execute('PRAGMA table_info(consciousness_log)').fetchall()
                        if True], row)) if isinstance(row, tuple) else row
        ts = str(row[1] if isinstance(row, tuple) else row['timestamp'])[:19]
        vals = ''.join(f'{(row[i+2] if isinstance(row, tuple) else row[k]):>11.3f}'
                       for i, k in enumerate(keys))
        print(f'{ts:<22}{vals}')

# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--last', type=int, default=0)
    parser.add_argument('--dry', action='store_true')
    parser.add_argument('--db', default=DB_PATH)
    args = parser.parse_args()

    if args.last:
        show_history(args.db, args.last)
    else:
        run_consciousness_check(args.db, dry_run=args.dry)