#!/bin/bash
# run_benchmark.sh — всё запускается внутри benchmark контейнера
cd /Volumes/Balances/hippograph-pro
export PATH=/usr/local/bin:/opt/homebrew/bin:$PATH

LOG=/Volumes/Balances/hippograph-pro/benchmark/results/run.log
mkdir -p benchmark/results

echo "[$(date)] Copying files into container..."
docker cp benchmark/baseline_server.py hippograph-benchmark:/app/benchmark/baseline_server.py
docker cp benchmark/run_comparison.py hippograph-benchmark:/app/benchmark/run_comparison.py
docker cp benchmark/results/hippograph_qa.json hippograph-benchmark:/app/benchmark/results/hippograph_qa.json

echo "[$(date)] Running benchmark inside container..."
docker exec hippograph-benchmark bash -c '
  cd /app
  mkdir -p benchmark/results

  # Start BM25
  python3 benchmark/baseline_server.py --mode bm25 --port 5020 > /tmp/bm25.log 2>&1 &
  BM25_PID=$!

  # Start Cosine
  python3 benchmark/baseline_server.py --mode cosine --port 5021 > /tmp/cosine.log 2>&1 &
  COSINE_PID=$!

  echo "Waiting 30s for servers..."
  sleep 30

  curl -sf http://localhost:5020/health && echo " BM25 up" || echo " BM25 FAILED"
  curl -sf http://localhost:5021/health && echo " Cosine up" || echo " Cosine FAILED"

  python3 benchmark/run_comparison.py --qa hippograph --granularity skip

  kill $BM25_PID $COSINE_PID 2>/dev/null
  echo "Done"
' 2>&1 | tee $LOG

echo "[$(date)] Finished. Log: $LOG"
