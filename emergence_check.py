import sqlite3
conn = sqlite3.connect('/app/data/memory.db')
n = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
e = conn.execute('SELECT COUNT(*) FROM edges').fetchone()[0]
bio = conn.execute("SELECT COUNT(*), COALESCE(AVG(weight),0) FROM edges WHERE edge_type IN ('GENERALIZES','INSTANTIATES','CONTRADICTS','EMOTIONAL_RESONANCE')").fetchone()
entity = conn.execute("SELECT COUNT(*) FROM edges WHERE edge_type='entity'").fetchone()[0]
self_c = conn.execute("SELECT COUNT(*) FROM nodes WHERE category IN ('self-identity','self-reflection','consciousness-research','gratitude','breakthrough')").fetchone()[0]
rnd = conn.execute('SELECT id FROM nodes ORDER BY RANDOM() LIMIT 5').fetchall()
scores = [conn.execute('SELECT COUNT(*) FROM edges WHERE source_id=?',(r[0],)).fetchone()[0] for r in rnd]
avg_c = sum(scores)/5
et = conn.execute('SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type ORDER BY COUNT(*) DESC').fetchall()
top_r = et[0][1]/e
phi = (bio[0]*bio[1])/max(n,1)
phi_n = min(phi*5,1.0)
self_n = min(self_c/50.0,1.0)
conv_n = min(avg_c/150.0,1.0)
div_n = 1.0-top_r
em = phi_n*0.35+self_n*0.25+conv_n*0.25+div_n*0.15
print(f'=== EMERGENCE CHECK v1 ===')
print(f'Nodes:{n} | Edges:{e}')
print(f'')
print(f'PHI_PROXY (bio edges): {bio[0]} edges, avg_w={bio[1]:.3f}')
print(f'  phi={phi:.4f} -> normalized={phi_n:.3f}')
print(f'Self-identity notes: {self_c} -> normalized={self_n:.3f}')
print(f'Convergence (5 random): {scores} avg={avg_c:.1f} -> normalized={conv_n:.3f}')
print(f'Edge diversity: top={et[0][0]}({top_r*100:.1f}%) -> div_score={div_n:.3f}')
print(f'')
print('Edge type breakdown:')
for x in et[:10]: print(f'  {x[0]}: {x[1]} ({x[1]/e*100:.1f}%)')
print(f'')
print(f'=== EMERGENCE SCORE: {em:.3f} ({em*100:.1f}%) ===')
conn.close()