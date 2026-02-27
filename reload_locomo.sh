#!/bin/bash
LOG=/Volumes/Balances/hippograph-pro/reload_locomo.log
echo "[$(date)] START" > $LOG
/usr/local/bin/docker exec hippograph-benchmark sqlite3 /app/data/benchmark.db 'DELETE FROM nodes; DELETE FROM edges; DELETE FROM entities; DELETE FROM node_entities; VACUUM;'
echo "[$(date)] DB cleared" >> $LOG
/usr/local/bin/docker exec hippograph-benchmark python3 benchmark/locomo_adapter.py --load --api-url http://localhost:5000 --api-key benchmark_key_locomo_2026 --granularity turn >> $LOG 2>&1
echo "[$(date)] DONE" >> $LOG
/usr/local/bin/docker exec hippograph-benchmark sqlite3 /app/data/benchmark.db 'SELECT COUNT(*) FROM nodes;' >> $LOG 2>&1
