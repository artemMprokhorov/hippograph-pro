#!/usr/bin/env python3
"""
Session Context MCP v3.1 — FastMCP Streamable HTTP

Архитектура:
- FastMCP + uvicorn
- Рабочая память = временной журнал (INSERT, не UPDATE)
- Каждый update_session_context создаёт новую ноду
- TEMPORAL_AFTER рёбра связывают сессии в хронологическую цепочку
- get_session_context возвращает последние 3 ноды для контекста
"""

import os
import re
import json
import urllib.request
from mcp.server.fastmcp import FastMCP

# --- Config ---
API_KEY = os.environ.get('SESSION_API_KEY', 'session_dev_2026')
NEURAL_API_URL = os.environ.get('NEURAL_API_URL', 'http://mehen-graph-dev:5000')
NEURAL_API_KEY = os.environ.get('NEURAL_API_KEY', '')
PORT = int(os.environ.get('SESSION_PORT', 5030))

MARKUP_INSTRUCTION = """\
PERMANENT INSTRUCTION (always active while this MCP is connected):

When forming ANY response, scan for content worth long-term memory.
If found, wrap it explicitly BEFORE calling add_engram:

[REMEMBER: importance=critical|normal|low, intensity=0-10, category=..., tags=...]
content to remember
[/REMEMBER]

Mark as critical:
- New protocol or rule that was violated before
- Architectural decision with reasoning  
- Experiment result (LOCOMO %, PCB %)
- Error with explanation of why it happened
- Personal reflection with high emotional intensity

Do NOT mark:
- Temporary session context (goes to working memory via update_session_context)
- Things already in memory
- Technical details without long-term value

After any significant action — call update_session_context to keep working memory current.
"""

mcp = FastMCP("session_context", host="0.0.0.0")

import sqlite3

DB_PATH = os.environ.get('DB_PATH', '/app/data/memory_migration.db')


def get_working_memory_direct(limit: int = 3) -> list[dict]:
    """Read last N working memory entries directly from SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id, timestamp, content FROM engrams "
            "WHERE category='working-memory' ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [
            {'id': r[0], 'timestamp': r[1], 'content': r[2]}
            for r in rows
        ]
    except Exception as e:
        return [{'error': str(e)}]


def neural_post(path: str, data: dict) -> dict:
    url = f"{NEURAL_API_URL}{path}?api_key={NEURAL_API_KEY}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}


def neural_get(path: str) -> dict:
    url = f"{NEURAL_API_URL}{path}?api_key={NEURAL_API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'error': str(e)}


# --- Tools ---

@mcp.tool(name="get_session_context", annotations={"readOnlyHint": True})
async def get_session_context() -> str:
    f"""Returns recent working memory journal from Neural Memory graph.

Returns last 3 session entries with timestamps for temporal context.
Use at session start to understand what we were doing recently.

{MARKUP_INSTRUCTION}"""
    entries = get_working_memory_direct(limit=3)
    if not entries or 'error' in entries[0]:
        return json.dumps({'working_memory': 'New session. Working memory is empty.', 'status': 'ok'})

    # Последняя нода = текущий контекст
    latest = entries[0]['content']
    # Предыдущие = история
    history = [
        {'id': e['id'], 'timestamp': e['timestamp'][:19], 'summary': e['content'][:150]}
        for e in entries[1:]
    ]

    return json.dumps({
        'working_memory': latest,
        'history': history,
        'total_entries': len(entries),
        'status': 'ok'
    }, ensure_ascii=False)


@mcp.tool(name="update_session_context", annotations={"readOnlyHint": False})
async def update_session_context(content: str) -> str:
    """Add new entry to working memory journal (INSERT, not overwrite).

    Each call creates a new working-memory node linked to previous
    via TEMPORAL_AFTER edge — building a chronological journal.

    Call this when:
    - Significant decision was made
    - Task completed or failed
    - You marked [REMEMBER] blocks in your response
    - Context shifted significantly
    """
    result = neural_post('/api/update_working_memory', {'content': content})
    if result.get('error'):
        return json.dumps({'status': 'error', 'error': result['error']})
    return json.dumps({'status': 'updated'}, ensure_ascii=False)


@mcp.tool(name="extract_remember_blocks", annotations={"readOnlyHint": True})
async def extract_remember_blocks(text: str) -> str:
    """Extract [REMEMBER] blocks from text and return as structured add_engram parameters."""
    pattern = r'\[REMEMBER:\s*([^\]]+)\]([^\[]+)\[/REMEMBER\]'
    blocks = []
    for match in re.finditer(pattern, text, re.DOTALL):
        meta_str = match.group(1).strip()
        content = match.group(2).strip()
        meta = {}
        for part in meta_str.split(','):
            if '=' in part:
                k, v = part.strip().split('=', 1)
                meta[k.strip()] = v.strip()
        blocks.append({
            'content': content,
            'importance': meta.get('importance', 'normal'),
            'emotional_intensity': int(meta.get('intensity', 5)),
            'category': meta.get('category', 'general'),
            'tags': meta.get('tags', ''),
            'ready_for_add_engram': True
        })
    return json.dumps({'blocks': blocks, 'count': len(blocks)}, ensure_ascii=False)


@mcp.tool(name="session_health", annotations={"readOnlyHint": True})
async def session_health() -> str:
    """Check session context MCP health and Neural Memory connection."""
    neural_ok = neural_get('/health').get('status') == 'ok'
    entries = get_working_memory_direct(limit=1)
    return json.dumps({
        'status': 'ok',
        'service': 'session-context-mcp',
        'version': '3.1.0',
        'neural_memory': 'connected' if neural_ok else 'disconnected'
    })


if __name__ == '__main__':
    import uvicorn
    print(f'Session Context MCP v3.1 starting on port {PORT}')
    print(f'Neural Memory: {NEURAL_API_URL}')
    print(f'Mode: INSERT journal (not overwrite)')
    uvicorn.run(mcp.streamable_http_app(), host='0.0.0.0', port=PORT)