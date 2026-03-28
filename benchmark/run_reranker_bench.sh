#!/bin/bash
echo '=== BASELINE prod ===' > /tmp/reranker_bench.log
python3 bm25_api_bench.py http://localhost:5001 >> /tmp/reranker_bench.log 2>&1
echo '' >> /tmp/reranker_bench.log
echo '=== EXP bge-reranker-v2-m3 ===' >> /tmp/reranker_bench.log
python3 bm25_api_bench.py http://localhost:5007 >> /tmp/reranker_bench.log 2>&1
echo 'DONE' >> /tmp/reranker_bench.log