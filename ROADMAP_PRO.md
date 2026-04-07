# HippoGraph Pro — Roadmap

*Updated: April 7, 2026*

> Полный консолидированный roadmap. Старый документ с итемами 1-53 архивирован в git history.

---

## ✅ СДЕЛАНО в 2026

| Фича | Дата | Результат |
|------|------|----------|
| BGE-M3 embedding | мар 28 | +3.9pp LOCOMO ✅ |
| bge-reranker-v2-m3 | мар 28 | PCB +43pp ✅ |
| Overlap chunking (D1) | мар 31 | **91.1% LOCOMO** ✅ |
| Temporal edges v2 | мар 14 | 100% node coverage ✅ |
| Lateral inhibition | мар 16 | diversity 3.2→4.8 ✅ |
| CONTRADICTS edges | мар | ✅ |
| EMOTIONAL_RESONANCE edges | мар | 1031 edges ✅ |
| GENERALIZES/INSTANTIATES | мар | 70 edges ✅ |
| SUPERSEDES scan | мар | 449 pairs ✅ |
| Abstract Topic Linking (47) | мар | global_workspace 0.412→0.647 ✅ |
| Consciousness Check (48) | мар | composite 0.707 ✅ |
| Online Consolidation (40) | мар | O(k) at add_note ✅ |
| Concept Merging (46) | мар | 7998 new edges ✅ |
| Keyword Anchors H3 | апр 7 | single-hop 91.5% > D1 ✅ **ЗАДЕПЛОЕН** |
| Session Context MCP v3 | апр 6 | FastMCP + SQLite ✅ |
| Аудит и синхронизация репо | апр 7 | ✅ |

---

## 🔴 ВЫСОКИЙ ПРИОРИТЕТ

### 1. Keyword anchors в sleep_compute.py
Шаг после Memory Consolidation, до temporal/entity edges.
Главный вывод H-серии — автоматизирует H3 поведение.

### 2. Anchor boost эксперимент
Ночной LOCOMO: boost 0.9 vs H3 1.2.
Цель: вернуть open-domain -3pp (трейдофф H3 vs D1).

### 3. M3 Multilingual conceptual search
Cross-lingual retrieval gap. BGE-M3 multilingual, но cosine между языками слабее.
План: language-agnostic tags → cross-lingual expansion → entity routing → multilingual SELF_QUERIES.

---

## 🟠 СРЕДНИЙ ПРИОРИТЕТ

### 4. Local LLM для temporal reasoning (item 15b)
Temporal в LOCOMO = reasoning НЕ retrieval. Потолок retrieval-only ~65%.
Кандидаты: Phi-4-mini (MIT), Qwen2.5-3B.

### 5. Ирония/самоирония в графе
Баланс памяти. LLM-разметка нод → keyword anchor для группы. Ждёт локальной LLM.

### 6. Рабочая память как временной журнал
Session Context MCP: INSERT вместо UPDATE. Каждая сессия = новая нода + TEMPORAL_AFTER.

### 7. M4 Chunk-aware inhibition
Разные веса inhibition внутри/между chunk-кольцами.

### 8. M5 Chunk-aware consolidation
Sleep строит рёбра только между кольцами разных сессий.

### 9. Prospective Memory (item 31)
Планы/намерения: no-decay, статус pending/done/cancelled.

### 10. Research DAG (item 29)
hypothesis → experiment → result → conclusion. Персистентный граф гипотез.

### 11. Git history cleanup
filter-repo для neuralv5_Bqt-... в публичном репо.

---

## 🟡 НИЗКИЙ ПРИОРИТЕТ

- PCB 94.3% — честный потолок (metrics snapshots dominance в SA)
- LNN Router CfC (item 44) — риск не даст pp
- arXiv (item 49) — после v3 breakthrough

---

## ❌ ОТКЛОНЕНО

- M1 серия (NEXT_CHUNK SA) — все 3 варианта: diversity collapse
- M2-B (summary prefix) — не превысил D1
- M2-C = H2 (spaCy sentencizer) — 85.2% < D1
- Dual-Memory skills.db (item 25) — слишком много failure points
- E1/E2/E3 (uroboros архитектура) — circular edges hurt

---

## V3 — НОВАЯ АРХИТЕКТУРА

| # | Задача | Приор |
|---|--------|-------|
| 1 | Живой граф (без batch sleep, онлайн ANN) | 🔴 |
| 2 | MCP/инструменты как ноды в графе | 🟠 |
| 3 | Anchors как отдельный слой (не в SA) | 🟠 |
| 4 | Neuro-symbolic как явный принцип | 🟠 |
| 5 | Гиперболическое пространство (Poincaré ball) | 🟡 |
| 6 | Research DAG в графе | 🟡 |
| 7 | arXiv | ⚪ |

---

## КЛЮЧЕВЫЕ ВЫВОДЫ

- **Temporal = reasoning, не retrieval.** Retrieval-only потолок ~65%. Нужен LLM inference step.
- **Anchor timing критичен:** ПОСЛЕ консолидации, ДО рёбер. H3 (90.8%) > H4 (88.3%).
- **Open-domain трейдофф** H3: -3pp open-domain за +6pp single-hop. В v3 решится anchor sloj.
- **PCB 94.3%** — честный потолок.
- hippograph-pro = `nodes` схема. Адаптировать при портировании из mehen-graph (`engrams`).

---

## ИНФРАСТРУКТУРА (апрель 7, 2026)

| Компонент | Порт | База | Статус |
|-----------|------|------|--------|
| mehen-graph-dev | 5020 | memory_migration.db (H3, 6512 нод) | healthy |
| session-context-mcp | 5030 | working-memory в Neural Memory | healthy |
| nginx-proxy | 80 | grand-beagle-reliably.ngrok-free.app | healthy |
| studio-mcp | 5010 | /Volumes/Balances | healthy |

**API key:** neuralv5_rFh1tbvHO2DGqRqE8LO3stSsxdRa8PqS6v2P6z6cyGc
**Снапшот до H3:** memory_snapshot_20260407_021045_pre_h3.db