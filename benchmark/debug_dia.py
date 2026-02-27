import json, urllib.request

with open('benchmark/locomo10.json') as f:
    data = json.load(f)

conv = data[0]
URL = 'http://localhost:5021'
KEY = 'benchmark_key_locomo_2026'

# Reset
req = urllib.request.Request(f'{URL}/api/reset?api_key={KEY}', method='DELETE')
urllib.request.urlopen(req, timeout=5)

# Load first 20 turns
dia_map = {}
turns = []
for k, v in sorted(conv['conversation'].items()):
    if k.startswith('session_') and not k.endswith('_date_time') and isinstance(v, list):
        turns.extend(v)

for turn in turns[:20]:
    payload = json.dumps({'content': f"{turn['speaker']}: {turn['text']}", 'category': 'locomo'}).encode()
    req = urllib.request.Request(f'{URL}/api/add_note?api_key={KEY}', data=payload, headers={'Content-Type': 'application/json'})
    r = json.loads(urllib.request.urlopen(req, timeout=10).read())
    dia_map[turn['dia_id']] = r.get('id')
    print(turn['dia_id'], '->', r.get('id'))

# Test first QA
qa = conv['qa'][0]
print()
print('Q:', qa['question'])
evid = [e for ev in qa['evidence'] for e in (ev if isinstance(ev, list) else [ev])]
evid_ids = {dia_map[e] for e in evid if e in dia_map}
print('evidence:', evid, '-> ids:', evid_ids)

payload = json.dumps({'query': qa['question'], 'limit': 5}).encode()
req = urllib.request.Request(f'{URL}/api/search?api_key={KEY}', data=payload, headers={'Content-Type': 'application/json'})
results = json.loads(urllib.request.urlopen(req, timeout=15).read())['results']
retrieved = [r['id'] for r in results]
print('retrieved:', retrieved)
print('HIT:', any(i in evid_ids for i in retrieved))
