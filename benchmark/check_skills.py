import sqlite3
conn = sqlite3.connect('/path/to/hippograph-pro/data/memory.db')

mastered = conn.execute("SELECT id, category FROM nodes WHERE content LIKE 'SKILL MASTERED%'").fetchall()
print(f'SKILL MASTERED: {len(mastered)}')
for r in mastered:
    print(f'  #{r[0]} {r[1]}')

learned = conn.execute("SELECT id, category FROM nodes WHERE content LIKE 'SKILL LEARNED%'").fetchall()
print(f'\nSKILL LEARNED: {len(learned)}')
cats = {}
for r in learned:
    cats[r[1]] = cats.get(r[1], 0) + 1
for cat, cnt in sorted(cats.items()):
    print(f'  {cat}: {cnt}')

ls = conn.execute("SELECT COUNT(*) FROM nodes WHERE category='learned-skill'").fetchone()[0]
print(f'\nCategory learned-skill total: {ls}')

other = conn.execute("SELECT id, category, substr(content,1,60) FROM nodes WHERE category='learned-skill' AND content NOT LIKE 'SKILL%'").fetchall()
if other:
    print(f'\nlearned-skill no SKILL*: {len(other)}')
    for r in other:
        print(f'  #{r[0]} | {r[2]}')

conn.close()