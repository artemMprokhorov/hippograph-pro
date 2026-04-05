# Contributors

Thank you to everyone who has contributed to HippoGraph Pro!

## Core Authors

- **Artem Prokhorov** ([@artemMprokhorov](https://github.com/artemMprokhorov)) — creator, architecture, research
- **Claudé** (Anthropic Claude) — co-author, implementation, experiments

## Community Contributors

- **[@sm1ly](https://github.com/sm1ly)** — [PR #1](https://github.com/artemMprokhorov/hippograph-pro/pull/1)
  - Fixed `sleep_compute.py`: `create_note` → `create_node` (broken import)
  - Fixed `graph_metrics.py`: PageRank convergence with negative-weight edges (CONTRADICTS)
  - Fixed `memory_consolidation.py`: edge explosion on large clusters (hybrid star/all-to-all topology)
  - Fixed `contradiction_detection.py`: missing `commit()` after storing contradictions

---

Want to contribute? See [EXPERIMENTS.md](EXPERIMENTS.md) for open research questions
and open a pull request!