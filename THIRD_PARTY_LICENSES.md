# Third-Party Licenses

HippoGraph Pro uses the following open-source components. All are compatible with commercial use under the terms noted below.

---

## Core Dependencies

### FastAPI
- **License:** MIT
- **URL:** https://github.com/tiangolo/fastapi
- **Commercial use:** ✅ Permitted

### SQLite
- **License:** Public Domain
- **URL:** https://www.sqlite.org
- **Commercial use:** ✅ Permitted (no restrictions)

### FAISS
- **License:** MIT
- **URL:** https://github.com/facebookresearch/faiss
- **Commercial use:** ✅ Permitted

### NetworkX
- **License:** BSD-3-Clause
- **URL:** https://github.com/networkx/networkx
- **Commercial use:** ✅ Permitted

### spaCy
- **License:** MIT
- **URL:** https://github.com/explosion/spaCy
- **Commercial use:** ✅ Permitted

### sentence-transformers
- **License:** Apache 2.0
- **URL:** https://github.com/UKPLab/sentence-transformers
- **Commercial use:** ✅ Permitted

### rank-bm25
- **License:** Apache 2.0
- **URL:** https://github.com/dorianbrown/rank_bm25
- **Commercial use:** ✅ Permitted

### D3.js
- **License:** ISC
- **URL:** https://github.com/d3/d3
- **Commercial use:** ✅ Permitted

### Docker
- **License:** Apache 2.0
- **URL:** https://github.com/docker/docker-ce
- **Commercial use:** ✅ Permitted

---

## ML Models

### GLiNER (gliner_multi-v2.1)
- **Code license:** Apache 2.0
- **URL:** https://github.com/urchade/GLiNER
- **Commercial use:** ✅ Code permitted
- **⚠️ Note:** Model weights for v2.1 were trained on a Mistral-generated dataset. Mistral's terms allow derivative model training for commercial use. However, if you require strict IP clarity, use spaCy fallback (`ENTITY_EXTRACTOR=spacy` in `.env`).

### sentence-transformers models (paraphrase-multilingual-MiniLM-L12-v2, ms-marco-MiniLM-L-6-v2)
- **License:** Apache 2.0
- **URL:** https://huggingface.co/sentence-transformers
- **Commercial use:** ✅ Permitted

---

## License Compliance Notes

- All code dependencies are permissive (MIT, Apache 2.0, BSD-3, ISC, Public Domain).
- The only area requiring attention is the GLiNER model weights (training data provenance). For production commercial deployments where strict IP clarity is required, configure `ENTITY_EXTRACTOR=spacy` in `.env`.
- HippoGraph Pro itself is dual-licensed: MIT for open-source/personal use, commercial license required for business use. See [LICENSE](LICENSE).

---

*Last reviewed: February 2026*
