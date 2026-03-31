#!/usr/bin/env bash
# =============================================================
# Experiment E: Parentless Overlap Chunking — LOCOMO benchmark
# =============================================================
# ПРАВИЛО: один subprocess, не несколько docker exec -d!
# Весь pipeline внутри одного скрипта.
#
# Usage:
#   cd /Volumes/Balances/hippograph-pro
#   bash benchmark/run_exp_e.sh
#
# Результаты: benchmark/results/exp_e_results.json
# =============================================================

set -e

COMPOSE_FILE="docker-compose.exp-e.yml"
CONTAINER="hippograph-exp-e"
API_URL="http://localhost:5005"
API_KEY="exp_e_key_2026"
RESULTS_DIR="benchmark/results"

echo "====================================================="
echo " Experiment E: Parentless Overlap Chunking"
echo " $(date)"
echo "====================================================="

# --- 1. Проверка что прод-контейнер НЕ используется ---
echo "[1/6] Проверка изоляции..."
if docker ps --format '{{.Names}}' | grep -q '^hippograph$'; then
    echo "  ✅ Прод (hippograph) работает отдельно — OK"
else
    echo "  ⚠️  Прод не запущен, но это не блокирует эксперимент"
fi

# --- 2. Поднять exp-e контейнер ---
echo "[2/6] Запуск контейнера $CONTAINER..."
docker compose -f $COMPOSE_FILE down --remove-orphans 2>/dev/null || true
docker compose -f $COMPOSE_FILE up -d --build

# --- 3. Ждём ready ---
echo "[3/6] Ожидание готовности API (до 120 сек)..."
for i in $(seq 1 24); do
    if curl -s --max-time 3 "$API_URL/health" | grep -q 'ok\|healthy\|status'; then
        echo "  ✅ API готов (попытка $i)"
        break
    fi
    if [ $i -eq 24 ]; then
        echo "  ❌ Timeout! Смотри логи:"
        docker logs $CONTAINER --tail 30
        exit 1
    fi
    echo "  ... ожидание ($i/24)"
    sleep 5
done

# Проверяем ANN index — критично!
echo "[3b] Проверка ANN индекса..."
for i in $(seq 1 6); do
    ANN_COUNT=$(docker logs $CONTAINER 2>&1 | grep 'Built ANN index with' | tail -1 | grep -o '[0-9]*' | tail -1 || echo '0')
    if [ "$ANN_COUNT" -gt "0" ] 2>/dev/null; then
        echo "  ✅ ANN index: $ANN_COUNT нод"
        break
    fi
    if [ $i -eq 6 ]; then
        echo "  ⚠️  ANN count unclear, продолжаем (проверь логи вручную)"
    fi
    sleep 5
done

# --- 4. Скачать датасет если нет ---
echo "[4/6] Проверка датасета..."
if [ ! -f "benchmark/locomo10.json" ]; then
    echo "  Скачиваю locomo10.json..."
    python3 benchmark/locomo_adapter.py --download
else
    echo "  ✅ Датасет уже есть"
fi

# --- 5. Загрузка + бенчмарк (один subprocess!) ---
echo "[5/6] Запуск полного pipeline (load + eval)..."
mkdir -p $RESULTS_DIR

python3 benchmark/locomo_adapter.py \
    --all \
    --api-url "$API_URL" \
    --api-key "$API_KEY" \
    --granularity session \
    2>&1 | tee $RESULTS_DIR/exp_e_run.log

# Сохраняем результаты с именем эксперимента
if [ -f "$RESULTS_DIR/locomo_results.json" ]; then
    cp $RESULTS_DIR/locomo_results.json $RESULTS_DIR/exp_e_locomo_results.json
    echo "  ✅ Результаты: $RESULTS_DIR/exp_e_locomo_results.json"
fi

# --- 6. Итог ---
echo "[6/6] Итог Эксперимента E:"
if [ -f "$RESULTS_DIR/exp_e_locomo_results.json" ]; then
    python3 -c "
import json
with open('$RESULTS_DIR/exp_e_locomo_results.json') as f:
    r = json.load(f)
m = r.get('metrics', {})
recall = m.get('recall_at_k', 0) * 100
mrr = m.get('mrr', 0)
total = m.get('total_queries', 0)
print(f'  Recall@5: {recall:.1f}%  MRR: {mrr:.3f}  Queries: {total}')
print(f'  D1 baseline: 91.1%  MRR: 0.830')
delta = recall - 91.1
print(f'  Delta vs D1: {delta:+.1f}pp')
per_cat = m.get('per_category', {})
for cat, v in per_cat.items():
    print(f'    {cat:12s}: {v[\"recall\"]*100:.1f}%  ({v[\"hits\"]}/{v[\"total\"]})')
"
fi

echo ""
echo "====================================================="
echo " Experiment E complete. Container still running."
echo " Logs: docker logs $CONTAINER"
echo " Stop: docker compose -f $COMPOSE_FILE down"
echo "====================================================="