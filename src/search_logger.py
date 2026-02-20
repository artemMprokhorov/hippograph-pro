"""
Search Quality Monitoring — query logging + latency tracking.

Logs every search to SQLite: query text, parameters, results count,
latency breakdown (embedding, ANN, spreading, BM25, temporal, rerank, total),
top result scores, and zero-result queries.

Usage:
    from search_logger import SearchLogger
    logger = SearchLogger()
    logger.start()          # begin timing
    logger.mark("embedding") # mark phase completion
    logger.mark("ann")
    ...
    logger.finish(query, results, params)  # save to DB
"""
import sqlite3
import time
import os
import json
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/app/data/memory.db")

# Use same DB as main app, separate table
SCHEMA = """
CREATE TABLE IF NOT EXISTS search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    query TEXT NOT NULL,
    query_cleaned TEXT,
    is_temporal INTEGER DEFAULT 0,
    temporal_direction TEXT,
    
    -- Parameters
    limit_requested INTEGER,
    category_filter TEXT,
    time_after TEXT,
    time_before TEXT,
    entity_type_filter TEXT,
    detail_mode TEXT,
    
    -- Results
    results_count INTEGER,
    total_activated INTEGER,
    top1_score REAL,
    top1_node_id INTEGER,
    top5_scores TEXT,
    
    -- Latency (ms)
    latency_total_ms REAL,
    latency_embedding_ms REAL,
    latency_ann_ms REAL,
    latency_spreading_ms REAL,
    latency_bm25_ms REAL,
    latency_temporal_ms REAL,
    latency_rerank_ms REAL,
    latency_filters_ms REAL,
    
    -- Signals
    blend_alpha REAL,
    blend_beta REAL,
    blend_gamma REAL,
    blend_delta REAL,
    bm25_matches INTEGER,
    temporal_matches INTEGER,
    rerank_enabled INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_search_logs_timestamp ON search_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_search_logs_results ON search_logs(results_count);
"""


class SearchLogger:
    """Tracks search timing and logs results."""
    
    def __init__(self):
        self._marks = {}
        self._start = None
        self._phase_start = None
        self._ensure_schema()
    
    def _ensure_schema(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(SCHEMA)
            conn.close()
        except Exception as e:
            print(f"⚠️ SearchLogger schema init failed: {e}")
    
    def start(self):
        """Begin timing a search."""
        self._marks = {}
        self._start = time.perf_counter()
        self._phase_start = self._start
    
    def mark(self, phase_name):
        """Mark completion of a phase."""
        now = time.perf_counter()
        self._marks[phase_name] = (now - self._phase_start) * 1000  # ms
        self._phase_start = now
    
    def finish(self, query, results, total_activated=0, params=None, signals=None):
        """Log completed search to DB."""
        if self._start is None:
            return
        
        total_ms = (time.perf_counter() - self._start) * 1000
        params = params or {}
        signals = signals or {}
        
        top5_scores = [r.get("activation", 0) for r in results[:5]]
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT INTO search_logs (
                    timestamp, query, query_cleaned, is_temporal, temporal_direction,
                    limit_requested, category_filter, time_after, time_before,
                    entity_type_filter, detail_mode,
                    results_count, total_activated, top1_score, top1_node_id, top5_scores,
                    latency_total_ms, latency_embedding_ms, latency_ann_ms,
                    latency_spreading_ms, latency_bm25_ms, latency_temporal_ms,
                    latency_rerank_ms, latency_filters_ms,
                    blend_alpha, blend_beta, blend_gamma, blend_delta,
                    bm25_matches, temporal_matches, rerank_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.utcnow().isoformat(),
                query,
                params.get("query_cleaned"),
                1 if params.get("is_temporal") else 0,
                params.get("temporal_direction"),
                params.get("limit"),
                params.get("category_filter"),
                params.get("time_after"),
                params.get("time_before"),
                params.get("entity_type_filter"),
                params.get("detail_mode"),
                len(results),
                total_activated,
                top5_scores[0] if top5_scores else None,
                results[0].get("id") if results else None,
                json.dumps(top5_scores),
                round(total_ms, 2),
                round(self._marks.get("embedding", 0), 2),
                round(self._marks.get("ann", 0), 2),
                round(self._marks.get("spreading", 0), 2),
                round(self._marks.get("bm25", 0), 2),
                round(self._marks.get("temporal", 0), 2),
                round(self._marks.get("rerank", 0), 2),
                round(self._marks.get("filters", 0), 2),
                signals.get("alpha"),
                signals.get("beta"),
                signals.get("gamma"),
                signals.get("delta"),
                signals.get("bm25_matches", 0),
                signals.get("temporal_matches", 0),
                1 if signals.get("rerank_enabled") else 0,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ SearchLogger write failed: {e}")
        
        self._start = None


def get_search_stats(hours=24):
    """Get search statistics for the last N hours."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        cutoff = datetime.utcnow().isoformat()[:10]  # Today
        
        stats = {}
        
        # Total searches
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM search_logs WHERE timestamp >= ?", (cutoff,)
        ).fetchone()
        stats["total_searches_today"] = row["cnt"]
        
        # Zero-result searches
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM search_logs WHERE results_count = 0 AND timestamp >= ?", (cutoff,)
        ).fetchone()
        stats["zero_results_today"] = row["cnt"]
        
        # Latency percentiles
        rows = conn.execute(
            "SELECT latency_total_ms FROM search_logs WHERE timestamp >= ? ORDER BY latency_total_ms", (cutoff,)
        ).fetchall()
        if rows:
            latencies = [r["latency_total_ms"] for r in rows]
            n = len(latencies)
            stats["latency_p50"] = round(latencies[n // 2], 1)
            stats["latency_p95"] = round(latencies[int(n * 0.95)], 1)
            stats["latency_p99"] = round(latencies[int(n * 0.99)], 1)
            stats["latency_max"] = round(latencies[-1], 1)
        
        # Average scores
        row = conn.execute("""
            SELECT AVG(top1_score) as avg_top1, AVG(results_count) as avg_results
            FROM search_logs WHERE timestamp >= ? AND results_count > 0
        """, (cutoff,)).fetchone()
        if row["avg_top1"]:
            stats["avg_top1_score"] = round(row["avg_top1"], 4)
            stats["avg_results_count"] = round(row["avg_results"], 1)
        
        # Phase latency breakdown (averages)
        row = conn.execute("""
            SELECT 
                AVG(latency_embedding_ms) as emb,
                AVG(latency_ann_ms) as ann,
                AVG(latency_spreading_ms) as spread,
                AVG(latency_bm25_ms) as bm25,
                AVG(latency_temporal_ms) as temp,
                AVG(latency_rerank_ms) as rerank
            FROM search_logs WHERE timestamp >= ?
        """, (cutoff,)).fetchone()
        if row["emb"] is not None:
            stats["avg_phase_ms"] = {
                "embedding": round(row["emb"], 1),
                "ann": round(row["ann"], 1),
                "spreading": round(row["spread"], 1),
                "bm25": round(row["bm25"], 1),
                "temporal": round(row["temp"], 1),
                "rerank": round(row["rerank"], 1),
            }
        
        # Recent zero-result queries
        rows = conn.execute("""
            SELECT query, timestamp FROM search_logs 
            WHERE results_count = 0 ORDER BY timestamp DESC LIMIT 10
        """).fetchall()
        stats["recent_zero_results"] = [{"query": r["query"], "timestamp": r["timestamp"]} for r in rows]
        
        # All-time totals
        row = conn.execute("SELECT COUNT(*) as cnt FROM search_logs").fetchone()
        stats["total_searches_all_time"] = row["cnt"]
        
        conn.close()
        return stats
    except Exception as e:
        return {"error": str(e)}
