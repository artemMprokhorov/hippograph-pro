#!/usr/bin/env python3
"""
Enhanced Entity Extractor for Neural Memory Graph
Supports regex and spaCy backends with confidence scores and noise filtering.
Multilingual: English (en_core_web_sm) + Russian/mixed (xx_ent_wiki_sm)
"""
import re
import os
from typing import List, Tuple, Dict

EXTRACTOR_TYPE = os.getenv("ENTITY_EXTRACTOR", "regex")

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
    "this", "that", "these", "those",
    # Russian ordinals and sequence words
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
}

# Expanded known entities with tech stack, concepts, and tools
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
    "faiss": ("FAISS", "tech"),
    "numpy": ("NumPy", "tech"),
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
    "semantic": ("semantic", "concept"),
    "activation": ("activation", "concept"),
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

# Enhanced spaCy label mapping with more types
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


def detect_language(text: str) -> str:
    """
    Detect primary language using Unicode character ranges.
    Returns 'ru' if >30% Cyrillic characters, 'en' otherwise.
    No external dependencies needed.
    """
    if not text:
        return "en"
    # Count Cyrillic vs Latin characters (ignore digits, punctuation, spaces)
    cyrillic = 0
    latin = 0
    for ch in text:
        if '\u0400' <= ch <= '\u04FF' or '\u0500' <= ch <= '\u052F':
            cyrillic += 1
        elif 'A' <= ch <= 'Z' or 'a' <= ch <= 'z':
            latin += 1
    total = cyrillic + latin
    if total == 0:
        return "en"
    return "ru" if (cyrillic / total) > 0.3 else "en"


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
    # Filter multi-word Russian phrases that are clearly not entities
    # (more than 4 words is almost never a real entity)
    if len(normalized.split()) > 4:
        return False
    return True


def normalize_entity(text: str) -> str:
    """Normalize entity text for deduplication"""
    text = " ".join(text.split())
    text = text.strip(".,!?;:'\"()[]{}").lower()
    return text


def _get_spacy_model(lang: str):
    """
    Load and cache the appropriate spaCy model based on language.
    English → en_core_web_sm (better for English NER)
    Russian/mixed → xx_ent_wiki_sm (multilingual NER)
    """
    cache_attr = f"_nlp_{lang}"
    if not hasattr(_get_spacy_model, cache_attr):
        import spacy
        if lang == "ru":
            try:
                model = spacy.load("xx_ent_wiki_sm")
            except OSError:
                print("⚠️  xx_ent_wiki_sm not found, falling back to en_core_web_sm")
                model = spacy.load("en_core_web_sm")
        else:
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
        # Use word boundary matching for short keywords to avoid false positives
        import re
        for key, (name, etype) in KNOWN_ENTITIES.items():
            if len(key) <= 3:
                # Short keywords: require word boundaries
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
            # Skip if already found in known entities
            if any(normalize_entity(e[0]) == normalized for e in entities):
                continue
            # Map spaCy label to our types
            entity_type = SPACY_LABEL_MAP.get(ent.label_, "concept")
            # Skip NUMBER types - these are noise
            if entity_type == "number":
                continue
            # Skip measurement types - usually noise
            if entity_type == "measurement":
                continue
            confidence = 0.8
            entities.append((ent.text, entity_type, confidence))
        
        # Deduplicate based on normalized text
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
    """
    if EXTRACTOR_TYPE == "spacy":
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
    if EXTRACTOR_TYPE == "spacy":
        return extract_entities_spacy(text)
    else:
        return extract_entities_regex(text)
