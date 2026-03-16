#!/usr/bin/env python3
"""
Enhanced Entity Extractor for Neural Memory Graph
Supports regex and spaCy backends with confidence scores and noise filtering.
Multilingual: English (en_core_web_sm) + any other language (xx_ent_wiki_sm)
"""
import re
import os
from typing import List, Tuple, Dict

EXTRACTOR_TYPE = os.getenv("ENTITY_EXTRACTOR", "regex")
# Priority chain: gliner (best) → spacy → regex

# Entity filtering configuration
MIN_ENTITY_LENGTH = 2  # Skip single-character entities

# Generic stopwords to filter out (too common/meaningless)
GENERIC_STOPWORDS = {
    # English ordinals and sequence words
    "first", "second", "third", "fourth", "fifth", "last", "next", "previous",
    # English number words
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    # English generic nouns
    "thing", "stuff", "issue", "problem", "solution", "way", "time", "day",
    # English temporal generics
    "today", "yesterday", "tomorrow", "now", "then",
    # English demonstratives
    "this", "that", "these", "those",# Russian ordinals and sequence words
    "первый", "второй", "третий", "четвёртый", "пятый", "последний", "следующий", "предыдущий",
    # Russian number words
    "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять",
    # Russian generic nouns
    "вещь", "штука", "проблема", "решение", "способ", "время", "день", "дело",
    # Russian temporal generics
    "сегодня", "вчера", "завтра", "сейчас", "тогда", "потом",
    # Russian demonstratives and pronouns
    "это", "этот", "эта", "эти", "тот", "та", "те", "того",
    # Russian particles and conjunctions that spaCy misclassifies
    "что", "как", "где", "когда", "потому", "поэтому", "также", "тоже",
    "или", "либо", "если", "хотя", "пока", "уже", "ещё", "еще",
    # Common Russian phrases misclassified as entities
    "не", "но", "да", "нет", "вот", "так", "все", "всё", "мне", "мой", "моя", "моё",
    # Russian multi-word stopwords
    "моё имя", "мое имя", "на самом деле", "в том числе", "в первую очередь",
}# Expanded known entities with tech stack, concepts, and tools
KNOWN_ENTITIES = {
    # Programming languages
    "python": ("Python", "tech"),
    "javascript": ("JavaScript", "tech"),
    "typescript": ("TypeScript", "tech"),
    "rust": ("Rust", "tech"),
    "java": ("Java", "tech"),
    "cpp": ("C++", "tech"),
    "c++": ("C++", "tech"),
    "go lang": ("Go", "tech"),
    "golang": ("Go", "tech"),
    "ruby": ("Ruby", "tech"),
    "php": ("PHP", "tech"),
    "swift": ("Swift", "tech"),
    "kotlin": ("Kotlin", "tech"),
    # Frameworks & Libraries
    "docker": ("Docker", "tech"),
    "kubernetes": ("Kubernetes", "tech"),
    "flask": ("Flask", "tech"),
    "fastapi": ("FastAPI", "tech"),
    "django": ("Django", "tech"),
    "react": ("React", "tech"),
    "vue": ("Vue", "tech"),
    "angular": ("Angular", "tech"),
    "pytorch": ("PyTorch", "tech"),
    "tensorflow": ("TensorFlow", "tech"),
    "transformers": ("Transformers", "tech"),
    "huggingface": ("Hugging Face", "tech"),
    "faiss": ("FAISS", "tech"),"numpy": ("NumPy", "tech"),
    "pandas": ("Pandas", "tech"),
    "spacy": ("spaCy", "tech"),
    # Databases & Storage
    "sqlite": ("SQLite", "tech"),
    "postgresql": ("PostgreSQL", "tech"),
    "postgres": ("PostgreSQL", "tech"),
    "mysql": ("MySQL", "tech"),
    "mongodb": ("MongoDB", "tech"),
    "redis": ("Redis", "tech"),
    # Protocols & Standards
    "mcp": ("MCP", "tech"),
    "http": ("HTTP", "tech"),
    "rest": ("REST", "tech"),
    "graphql": ("GraphQL", "tech"),
    "grpc": ("gRPC", "tech"),
    # AI/ML Concepts
    "llm": ("LLM", "concept"),
    "ann": ("ANN", "tech"),
    "embedding": ("embedding", "concept"),
    "embeddings": ("embeddings", "concept"),
    "transformer": ("transformer", "concept"),
    "attention": ("attention", "concept"),
    "rag": ("RAG", "concept"),
    "neural network": ("neural network", "concept"),
    # Memory/Graph Concepts
    "memory": ("memory", "concept"),
    "graph": ("graph", "concept"),
    "knowledge": ("knowledge", "concept"),
    "semantic": ("semantic", "concept"),"activation": ("activation", "concept"),
    "spreading activation": ("spreading activation", "concept"),
    "entity": ("entity", "concept"),
    "consciousness": ("consciousness", "concept"),
    # Tools & Services
    "github": ("GitHub", "tech"),
    "gitlab": ("GitLab", "tech"),
    "vscode": ("VS Code", "tech"),
    "vim": ("Vim", "tech"),
    "ngrok": ("ngrok", "tech"),
    "claude": ("Claude", "tech"),
    "openai": ("OpenAI", "organization"),
    "anthropic": ("Anthropic", "organization"),
    # Project-specific
    "hippograph": ("HippoGraph", "project"),
    "scotiabank": ("Scotiabank", "organization"),
    "santiago": ("Santiago", "location"),
    "chile": ("Chile", "location"),
}


# Synonym normalization: map abbreviations and variants to canonical forms
# Applied during BOTH ingestion (normalize_entity) and search (normalize_query)
SYNONYMS = {
    # ML/AI abbreviations
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "dl": "deep learning",
    "rl": "reinforcement learning",
    "rag": "retrieval augmented generation",# Infrastructure
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "hf": "hugging face",
    "pg": "postgresql",
    # Project-specific
    "hippograph pro": "hippograph",
    "neural memory": "hippograph",
    "semantic memory": "hippograph",
    # Russian (RU) — 15+ pairs
    "машинное обучение": "machine learning",
    "искусственный интеллект": "artificial intelligence",
    "нейронная сеть": "neural network",
    "нейронные сети": "neural network",
    "обработка естественного языка": "natural language processing",
    "компьютерное зрение": "computer vision",
    "глубокое обучение": "deep learning",
    "обучение с подкреплением": "reinforcement learning",
    "большая языковая модель": "large language model",
    "языковая модель": "language model",
    "векторное представление": "embedding",
    "векторные представления": "embeddings",
    "смысловой поиск": "semantic search",
    "граф знаний": "knowledge graph",
    "распространение активации": "spreading activation",
    "память": "memory",
    "сознание": "consciousness",
    "хиппограф": "hippograph",# Spanish / Chilean (ES)
    "aprendizaje automático": "machine learning",
    "inteligencia artificial": "artificial intelligence",
    "red neuronal": "neural network",
    "redes neuronales": "neural network",
    "procesamiento de lenguaje natural": "natural language processing",
    "visión por computadora": "computer vision",
    "aprendizaje profundo": "deep learning",
    "modelo de lenguaje": "language model",
    "búsqueda semántica": "semantic search",
    "grafo de conocimiento": "knowledge graph",
    "memoria": "memory",
    # German (DE)
    "maschinelles lernen": "machine learning",
    "künstliche intelligenz": "artificial intelligence",
    "neuronales netz": "neural network",
    "neuronale netze": "neural network",
    "sprachmodell": "language model",
    "wissensgraph": "knowledge graph",
    # French (FR)
    "apprentissage automatique": "machine learning",
    "intelligence artificielle": "artificial intelligence",
    "réseau de neurones": "neural network",
    "modèle de langage": "language model",
    "graphe de connaissances": "knowledge graph",
    "mémoire": "memory",
    # Portuguese (PT)
    "aprendizado de máquina": "machine learning",
    "inteligência artificial": "artificial intelligence",
    "rede neural": "neural network",
    "redes neurais": "neural network",
    "modelo de linguagem": "language model",
    "grafo de conhecimento": "knowledge graph",
    "memória": "memory",
}# Enhanced spaCy label mapping with more types
SPACY_LABEL_MAP = {
    "PERSON": "person",
    "ORG": "organization",
    "GPE": "location",
    "LOC": "location",
    "PRODUCT": "product",
    "EVENT": "event",
    "WORK_OF_ART": "creative_work",
    "LANGUAGE": "tech",
    "DATE": "temporal",
    "TIME": "temporal",
    "MONEY": "financial",
    "QUANTITY": "measurement",
    "ORDINAL": "number",
    "CARDINAL": "number",
    # xx_ent_wiki_sm uses these labels
    "PER": "person",
    "MISC": "concept",
}

# Unicode ranges for non-Latin scripts → use multilingual model
_NON_LATIN_RANGES = [
    (0x0400, 0x052F),   # Cyrillic (Russian, Ukrainian, Bulgarian, etc.)
    (0x0370, 0x03FF),   # Greek
    (0x0600, 0x06FF),   # Arabic
    (0x0900, 0x097F),   # Devanagari (Hindi)
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (Chinese/Japanese Kanji)
    (0x3040, 0x309F),   # Hiragana (Japanese)
    (0x30A0, 0x30FF),   # Katakana (Japanese)
    (0xAC00, 0xD7AF),   # Hangul (Korean)
    (0x0E00, 0x0E7F),   # Thai
    (0x0400, 0x04FF),   # Cyrillic extended
]

def detect_language(text: str) -> str:
    """
    Detect whether text is primarily English or non-English.
    Returns 'en' for English/Latin-script text, 'xx' for everything else.
    'xx' routes to xx_ent_wiki_sm (spaCy multilingual model, 50+ languages).
    No external dependencies — pure Unicode range detection.
    """
    if not text:
        return "en"
    non_latin = 0
    latin = 0
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _NON_LATIN_RANGES):
            non_latin += 1
        elif 'A' <= ch <= 'Z' or 'a' <= ch <= 'z':
            latin += 1
    total = non_latin + latin
    if total == 0:
        return "en"
    # >20% non-Latin characters → use multilingual model
    return "xx" if (non_latin / total) > 0.2 else "en"


def is_valid_entity(text: str) -> bool:
    """
    Filter out noise entities.
    Returns True if entity should be kept, False if filtered out.
    """
    normalized = text.lower().strip()
    if len(normalized) < MIN_ENTITY_LENGTH:
        return False
    if normalized.isdigit():
        return False
    if normalized in GENERIC_STOPWORDS:
        return False
    if len(normalized) == 1 and normalized not in {'i', 'a'}:
        return False
    # Filter multi-word phrases that are clearly not entities
    # (more than 4 words is almost never a real entity)
    if len(normalized.split()) > 4:
        return False
    return True


def normalize_entity(text: str) -> str:
    """Normalize entity text for deduplication. Applies synonym mapping."""
    text = " ".join(text.split())
    text = text.strip(".,!?;:'\"()[]{}").lower()
    text = SYNONYMS.get(text, text)
    return text


def normalize_query(text: str) -> str:
    """
    Normalize a search query string by applying synonym mapping to each token
    and to the full query. Enables cross-lingual search: a query in Russian,
    Spanish, German, French, or Portuguese maps to the English canonical form
    which is used during ingestion.

    Examples:
        'машинное обучение' -> 'machine learning'
        'inteligencia artificial' -> 'artificial intelligence'
        'k8s deployment' -> 'kubernetes deployment'
    """
    lowered = text.lower().strip()
    # Try full-phrase match first
    if lowered in SYNONYMS:
        return SYNONYMS[lowered]
    # Try word-by-word replacement for multi-word queries
    tokens = lowered.split()
    result_tokens = []
    i = 0
    while i < len(tokens):
        # Try longest match: 4-grams, 3-grams, 2-grams, then single token
        matched = False
        for n in (4, 3, 2):
            if i + n <= len(tokens):
                phrase = " ".join(tokens[i:i + n])
                if phrase in SYNONYMS:
                    result_tokens.append(SYNONYMS[phrase])
                    i += n
                    matched = True
                    break
        if not matched:
            token = tokens[i]
            result_tokens.append(SYNONYMS.get(token, token))
            i += 1
    return " ".join(result_tokens)

def _get_spacy_model(lang: str):
    """
    Load and cache the appropriate spaCy model based on language.
    English → en_core_web_sm (better NER for English)
    Any other language → xx_ent_wiki_sm (multilingual, 50+ languages)
    """
    cache_attr = f"_nlp_{lang}"
    if not hasattr(_get_spacy_model, cache_attr):
        import spacy
        if lang == "en":
            model = spacy.load("en_core_web_sm")
        else:
            # xx_ent_wiki_sm covers: Russian, German, Spanish, French,
            # Portuguese, Chinese, Japanese, Arabic, Dutch, Polish, and more
            try:
                model = spacy.load("xx_ent_wiki_sm")
            except OSError:
                print("⚠️  xx_ent_wiki_sm not found, falling back to en_core_web_sm")
                model = spacy.load("en_core_web_sm")
        setattr(_get_spacy_model, cache_attr, model)
    return getattr(_get_spacy_model, cache_attr)


def extract_entities_regex(text: str) -> List[Tuple[str, str, float]]:
    """
    Extract entities using regex patterns.
    Returns: List of (entity_text, entity_type, confidence)
    """
    entities = []
    text_lower = text.lower()
    for key, (name, etype) in KNOWN_ENTITIES.items():
        if key in text_lower:
            if is_valid_entity(name):
                entities.append((name, etype, 1.0))
    seen = set()
    unique = []
    for entity_text, entity_type, confidence in entities:
        normalized = normalize_entity(entity_text)
        if normalized not in seen:
            seen.add(normalized)
            unique.append((entity_text, entity_type, confidence))
    return unique

def extract_entities_spacy(text: str) -> List[Tuple[str, str, float]]:
    """
    Extract entities using spaCy NER with multilingual support.
    Detects language, routes to appropriate model.
    Returns: List of (entity_text, entity_type, confidence)
    """
    try:
        lang = detect_language(text)
        nlp = _get_spacy_model(lang)
        doc = nlp(text)

        entities = []
        text_lower = text.lower()

        # First, add known entities (high confidence)
        import re
        for key, (name, etype) in KNOWN_ENTITIES.items():
            if len(key) <= 3:
                if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
                    if is_valid_entity(name):
                        entities.append((name, etype, 1.0))
            else:
                if key in text_lower and is_valid_entity(name):
                    entities.append((name, etype, 1.0))

        # Then, add spaCy detected entities
        for ent in doc.ents:
            if not is_valid_entity(ent.text):
                continue
            normalized = normalize_entity(ent.text)
            if any(normalize_entity(e[0]) == normalized for e in entities):
                continue
            entity_type = SPACY_LABEL_MAP.get(ent.label_, "concept")
            if entity_type == "number":
                continue
            if entity_type == "measurement":
                continue
            confidence = 0.8
            entities.append((ent.text, entity_type, confidence))

        # Deduplicate
        seen = set()
        unique = []
        for entity_text, entity_type, confidence in entities:
            normalized = normalize_entity(entity_text)
            if normalized not in seen:
                seen.add(normalized)
                unique.append((entity_text, entity_type, confidence))
        return unique

    except Exception as e:
        print(f"⚠️  spaCy extraction failed: {e}, falling back to regex")
        return extract_entities_regex(text)

def extract_entities(text: str, min_confidence: float = 0.5) -> List[Tuple[str, str]]:
    """
    Extract entities from text using configured backend.
    Upgrade chain: gliner (best) → spacy → regex
    """
    if EXTRACTOR_TYPE == "gliner":
        from gliner_client import is_available as gliner_available, extract_entities_gliner
        if gliner_available():
            entities = extract_entities_gliner(text)
            if entities:
                return entities
        print("⚠️ GLiNER unavailable, falling back to spaCy")
        entities_with_confidence = extract_entities_spacy(text)
    elif EXTRACTOR_TYPE == "spacy":
        entities_with_confidence = extract_entities_spacy(text)
    else:
        entities_with_confidence = extract_entities_regex(text)
    filtered = [
        (entity_text, entity_type)
        for entity_text, entity_type, confidence in entities_with_confidence
        if confidence >= min_confidence
    ]
    return filtered


def extract_entities_with_confidence(text: str) -> List[Tuple[str, str, float]]:
    """
    Extract entities with confidence scores.
    """
    if EXTRACTOR_TYPE == "gliner":
        from gliner_client import is_available as gliner_available, extract_entities_gliner_with_confidence
        if gliner_available():
            entities = extract_entities_gliner_with_confidence(text)
            if entities:
                return entities
        return extract_entities_spacy(text)
    elif EXTRACTOR_TYPE == "spacy":
        return extract_entities_spacy(text)
    else:
        return extract_entities_regex(text)