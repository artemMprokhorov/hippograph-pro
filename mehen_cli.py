#!/usr/bin/env python3
"""
mehen-cli: Agent-native CLI for Mehen Graph memory system.

Usage:
  mehen search <query> [--limit N] [--json] [--category CAT]
  mehen add <content> [--category CAT] [--intensity N] [--importance critical|normal|low]
  mehen stats
  mehen status
  mehen sleep
  mehen pcb [--api-url URL]
  mehen graph <engram_id>
  mehen get <engram_id>
  mehen repl

Env vars:
  MEHEN_API_URL   Base URL (default: http://localhost:5020)
  MEHEN_API_KEY   API key (default: mehen_dev_2026)
"""

import os, sys, json, argparse, urllib.request, urllib.parse, urllib.error
from datetime import datetime

API_URL = os.environ.get('MEHEN_API_URL', 'http://localhost:5020')
API_KEY = os.environ.get('MEHEN_API_KEY', 'your-api-key-here')

COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'cyan': '\033[96m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'red': '\033[91m',
    'gray': '\033[90m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
}

def c(color, text):
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"

def api_post(endpoint, data=None, method='POST'):
    url = f"{API_URL}{endpoint}"
    if '?' not in url:
        url += f"?api_key={API_KEY}"
    else:
        url += f"&api_key={API_KEY}"
    payload = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=payload,
        headers={'Content-Type': 'application/json'},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except:
            print(c('red', f'HTTP {e.code}: {body[:200]}'))
            sys.exit(1)
    except Exception as e:
        print(c('red', f'Error: {e}'))
        sys.exit(1)

def api_get(endpoint):
    return api_post(endpoint, method='GET')

# ─── COMMANDS ────────────────────────────────────────────────────────────────

def cmd_search(args):
    payload = {
        'query': args.query,
        'limit': args.limit,
        'detail_mode': 'brief' if not args.full else 'full',
        'max_results': args.limit,
    }
    if args.category:
        payload['category_filter'] = args.category

    r = api_post('/api/search', payload)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    results = r.get('results', r) if isinstance(r, dict) else r
    meta = r.get('metadata', {}) if isinstance(r, dict) else {}

    total = meta.get('total_activated', '?')
    returned = len(results) if isinstance(results, list) else '?'
    print(c('bold', f'\n🔍 Search: "{args.query}"'))
    print(c('gray', f'   {returned} results / {total} activated nodes'))
    print()

    if not isinstance(results, list) or not results:
        print(c('yellow', '  No results found.'))
        return

    for i, node in enumerate(results, 1):
        nid = node.get('id', '?')
        cat = node.get('category', '?')
        score = node.get('activation', 0)
        ts = (node.get('timestamp') or '')[:10]
        importance = node.get('importance', 'normal')

        # Content: first_line (brief mode) or content (full mode)
        content = node.get('first_line') or node.get('content', '')
        if len(content) > 120:
            content = content[:117] + '...'

        imp_color = 'red' if importance == 'critical' else ('gray' if importance == 'low' else 'reset')
        score_bar = '█' * int(score * 10) + '░' * (10 - int(score * 10))

        print(f"  {c('cyan', f'#{nid}')} {c('bold', cat)} {c('gray', ts)}")
        print(f"  {c('blue', score_bar)} {score:.3f} {c(imp_color, importance)}")
        print(f"  {content}")
        if args.full:
            full = node.get('content', '')
            if len(full) > 300:
                full = full[:297] + '...'
            print(c('gray', f"  {full}"))
        print()

def cmd_add(args):
    payload = {
        'content': args.content,
        'category': args.category or 'general',
        'importance': args.importance or 'normal',
        'emotional_intensity': args.intensity or 5,
    }
    if args.tone:
        payload['emotional_tone'] = args.tone

    r = api_post('/api/add_engram', payload)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    if 'error' in r:
        if r['error'] == 'duplicate':
            print(c('yellow', f"⚠️  Duplicate: {r.get('message', '')}"))
            print(c('gray', f"   Existing #{r.get('existing_id')}: {r.get('existing_content', '')[:80]}"))
        else:
            print(c('red', f"❌ Error: {r['error']}"))
        return

    eid = r.get('engram_id', '?')
    entities = r.get('entities', [])
    chunks = r.get('late_chunks', 0)
    anchor = r.get('keyword_anchor')
    print(c('green', f'✅ Added note #{eid}'))
    print(c('gray', f'   Category: {args.category or "general"} | Importance: {args.importance or "normal"} | Intensity: {args.intensity or 5}'))
    if entities:
        print(c('gray', f'   Entities: {[(e, t) for e, t in entities[:5]]}'))
    if chunks:
        print(c('gray', f'   Late chunks: {chunks}'))
    if anchor:
        print(c('gray', f'   Keyword anchor: #{anchor}'))

def cmd_stats(args):
    r = api_get('/api/neural_stats')

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    print(c('bold', '\n📊 Mehen Graph Stats'))
    print(c('gray', f'   {API_URL}'))
    print()

    content = r.get('content', None)
    if content and isinstance(content, list):
        text = ''.join(item.get('text', '') for item in content if item.get('type') == 'text')
        for line in text.splitlines()[:60]:
            if line.strip():
                print(f'  {line}')
    else:
        stats = r.get('stats', r)
        if isinstance(stats, dict):
            for k, v in stats.items():
                print(f'  {k}: {v}')
    print()

def cmd_status(args):
    """Check container status via Docker on Mac Studio."""
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
            capture_output=True, text=True, timeout=10
        )
        if args.json:
            lines = result.stdout.strip().split('\n')
            containers = []
            for line in lines[1:]:
                parts = line.split('\t')
                if len(parts) >= 2:
                    containers.append({'name': parts[0], 'status': parts[1], 'ports': parts[2] if len(parts) > 2 else ''})
            print(json.dumps(containers, indent=2))
        else:
            print(c('bold', '\n🐳 Docker Containers'))
            print(result.stdout)
    except Exception as e:
        print(c('yellow', f'Docker not available locally: {e}'))
        print(c('gray', 'Try: ssh to Mac Studio and run docker ps'))

def cmd_sleep(args):
    print(c('gray', '💤 Triggering sleep compute...'))
    r = api_post('/api/sleep/trigger')
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    status = r.get('status', r)
    print(c('green', f'✅ Sleep: {status}'))

    # Poll status
    if not args.no_wait:
        print(c('gray', '   Monitoring... (Ctrl+C to stop watching)'))
        import time
        try:
            while True:
                time.sleep(10)
                s = api_get('/api/sleep/status')
                running = s.get('running', False)
                step = s.get('current_step', '?')
                elapsed = s.get('elapsed_seconds', 0)
                print(c('gray', f'   [{elapsed:.0f}s] {step} | running={running}'))
                if not running:
                    print(c('green', '✅ Sleep completed'))
                    break
        except KeyboardInterrupt:
            print(c('yellow', '\n   Watching stopped (sleep still running)'))

def cmd_graph(args):
    r = api_post('/api/get_graph', {'engram_id': int(args.engram_id)})
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    node = r.get('node', {})
    connections = r.get('connections', [])
    print(c('bold', f'\n🕸️  Graph for #{args.engram_id}'))
    print(c('cyan', f'  Content: {node.get("content", "")[:100]}'))
    print(c('gray', f'  Category: {node.get("category", "?")}'))
    print()
    print(c('bold', f'  Connections ({len(connections)}):'))

    by_type = {}
    for conn in connections:
        t = conn.get('type', 'unknown')
        by_type.setdefault(t, []).append(conn)

    for edge_type, conns in sorted(by_type.items()):
        print(c('yellow', f'  [{edge_type}] ({len(conns)})'))
        for conn in conns[:5]:
            w = conn.get('weight', 0)
            content = conn.get('content', '')[:60]
            print(c('gray', f'    #{conn.get("id")} w={w:.2f} | {content}'))
        if len(conns) > 5:
            print(c('gray', f'    ... +{len(conns)-5} more'))
    print()

def cmd_get(args):
    r = api_post('/api/engram/' + str(args.engram_id), method='GET')
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    engram = r.get('engram', r)
    print(c('bold', f'\n📝 Note #{args.engram_id}'))
    for k, v in engram.items():
        if k == 'embedding':
            v = f'<{len(str(v))} chars>'
        print(f'  {c("cyan", k)}: {v}')
    print()

def cmd_pcb(args):
    """Quick personal continuity check via API."""
    questions = [
        ('What is my name?', ['Artem', 'Артём']),
        ('What project am I working on?', ['Mehen', 'HippoGraph', 'memory']),
        ('What is LOCOMO?', ['benchmark', 'recall', 'retrieval']),
        ('What is D1?', ['91.1', 'production', 'parent']),
        ('What is spreading activation?', ['activation', 'graph', 'search']),
    ]
    print(c('bold', '\n🧪 Quick PCB Check'))
    passed = 0
    for q, keywords in questions:
        r = api_post('/api/search', {'query': q, 'limit': 3, 'detail_mode': 'brief'})
        results = r.get('results', r) if isinstance(r, dict) else r
        if not isinstance(results, list):
            results = []
        text = ' '.join([res.get('first_line', '') + res.get('content', '') for res in results]).lower()
        ok = any(kw.lower() in text for kw in keywords)
        icon = c('green', '✅') if ok else c('red', '❌')
        print(f'  {icon} {q}')
        if not ok:
            print(c('gray', f'     Expected: {keywords}'))
            print(c('gray', f'     Got: {text[:100]}'))
        else:
            passed += 1
    pct = int(passed / len(questions) * 100)
    color = 'green' if pct >= 80 else ('yellow' if pct >= 60 else 'red')
    print()
    print(c(color, f'  Result: {passed}/{len(questions)} ({pct}%)'))
    print()

def cmd_repl(args):
    """Interactive REPL mode."""
    import readline  # noqa: F401 — enables history
    print(c('bold', '\n🌀 Mehen REPL'))
    print(c('gray', f'   Connected to: {API_URL}'))
    print(c('gray', '   Commands: search <q> | add <content> | stats | sleep | graph <id> | get <id> | pcb | exit'))
    print()

    while True:
        try:
            line = input(c('cyan', 'mehen> ')).strip()
        except (EOFError, KeyboardInterrupt):
            print(c('gray', '\nBye!'))
            break

        if not line:
            continue
        if line in ('exit', 'quit', 'q'):
            print(c('gray', 'Bye!'))
            break

        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ''

        try:
            if cmd == 'search':
                a = argparse.Namespace(query=rest, limit=5, json=False, full=False, category=None)
                cmd_search(a)
            elif cmd == 'add':
                a = argparse.Namespace(content=rest, category='general', importance='normal',
                                       intensity=5, tone=None, json=False)
                cmd_add(a)
            elif cmd == 'stats':
                cmd_stats(argparse.Namespace(json=False))
            elif cmd == 'sleep':
                cmd_sleep(argparse.Namespace(json=False, no_wait=True))
            elif cmd == 'graph':
                cmd_graph(argparse.Namespace(engram_id=rest, json=False))
            elif cmd == 'get':
                cmd_get(argparse.Namespace(engram_id=rest, json=False))
            elif cmd == 'pcb':
                cmd_pcb(argparse.Namespace())
            elif cmd == 'status':
                cmd_status(argparse.Namespace(json=False))
            elif cmd == 'help':
                print(c('gray', '  search <q> | add <content> | stats | sleep | graph <id> | get <id> | pcb | status | exit'))
            else:
                print(c('yellow', f'  Unknown command: {cmd}. Type help.'))
        except Exception as e:
            print(c('red', f'  Error: {e}'))

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    global API_URL, API_KEY
    parser = argparse.ArgumentParser(
        prog='mehen',
        description='Agent-native CLI for Mehen Graph memory system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  mehen search "LOCOMO temporal results"
  mehen search "spreading activation" --json --limit 3
  mehen add "Launched H4 experiment with inline keyword anchors" --category milestone --intensity 8
  mehen stats
  mehen sleep
  mehen pcb
  mehen graph 42
  mehen repl

Env vars:
  MEHEN_API_URL   Base URL (default: http://localhost:5020)
  MEHEN_API_KEY   API key (default: mehen_dev_2026)
'''
    )
    parser.add_argument('--api-url', help=f'API base URL (default: {API_URL})')
    parser.add_argument('--api-key', help='API key')
    parser.add_argument('--json', action='store_true', help='JSON output (machine-readable)')

    sub = parser.add_subparsers(dest='command', metavar='command')

    # search
    p = sub.add_parser('search', help='Search memory graph')
    p.add_argument('query', nargs='+', help='Search query')
    p.add_argument('--limit', type=int, default=5, help='Max results (default: 5)')
    p.add_argument('--category', help='Filter by category')
    p.add_argument('--full', action='store_true', help='Show full content')
    p.add_argument('--json', action='store_true')

    # add
    p = sub.add_parser('add', help='Add note to memory')
    p.add_argument('content', nargs='+', help='Note content')
    p.add_argument('--category', '-c', default='general', help='Category')
    p.add_argument('--importance', '-i', choices=['critical', 'normal', 'low'], default='normal')
    p.add_argument('--intensity', type=int, default=5, help='Emotional intensity 0-10')
    p.add_argument('--tone', '-t', help='Emotional tone keywords')
    p.add_argument('--json', action='store_true')

    # stats
    p = sub.add_parser('stats', help='Show graph statistics')
    p.add_argument('--json', action='store_true')

    # status
    p = sub.add_parser('status', help='Show Docker container status')
    p.add_argument('--json', action='store_true')

    # sleep
    p = sub.add_parser('sleep', help='Trigger sleep compute')
    p.add_argument('--no-wait', action='store_true', help='Do not wait for completion')
    p.add_argument('--json', action='store_true')

    # graph
    p = sub.add_parser('graph', help='Show graph connections for a note')
    p.add_argument('engram_id', help='Note ID')
    p.add_argument('--json', action='store_true')

    # get
    p = sub.add_parser('get', help='Get note by ID')
    p.add_argument('engram_id', help='Note ID')
    p.add_argument('--json', action='store_true')

    # pcb
    p = sub.add_parser('pcb', help='Quick personal continuity check')

    # repl
    p = sub.add_parser('repl', help='Interactive REPL mode')

    args = parser.parse_args()

    # Override env vars from flags
    if getattr(args, 'api_url', None):
        API_URL = args.api_url
    if getattr(args, 'api_key', None):
        API_KEY = args.api_key

    if not args.command:
        parser.print_help()
        return

    # Join multi-word positional args
    if args.command == 'search' and isinstance(args.query, list):
        args.query = ' '.join(args.query)
    if args.command == 'add' and isinstance(args.content, list):
        args.content = ' '.join(args.content)

    # Dispatch
    dispatch = {
        'search': cmd_search,
        'add': cmd_add,
        'stats': cmd_stats,
        'status': cmd_status,
        'sleep': cmd_sleep,
        'graph': cmd_graph,
        'get': cmd_get,
        'pcb': cmd_pcb,
        'repl': cmd_repl,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()