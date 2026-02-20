"""
Ollama client — thin wrapper for LLM calls via Ollama API.
Configurable model and URL. Graceful fallback when unavailable.
"""

import os
import json
import urllib.request
import urllib.error

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://hippograph-ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

_available = None  # cached availability check


def is_available() -> bool:
    """Check if Ollama is reachable and model is loaded."""
    global _available
    if _available is not None:
        return _available
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/version", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            _available = resp.status == 200
    except Exception:
        _available = False
    return _available


def reset_availability():
    """Reset cached availability (call after config changes)."""
    global _available
    _available = None


def generate(prompt: str, system: str = "", temperature: float = 0.1,
             model: str = None, timeout: int = 60) -> str:
    """
    Generate text via Ollama API.
    
    Args:
        prompt: User prompt
        system: System prompt (optional)
        temperature: Sampling temperature (low = deterministic)
        model: Override OLLAMA_MODEL
        timeout: Request timeout in seconds
    
    Returns:
        Generated text, or empty string on failure
    """
    if not is_available():
        return ""
    
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
    }
    if system:
        payload["system"] = system
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        print(f"⚠️ Ollama generate failed: {e}")
        return ""


def extract_json(prompt: str, system: str = "", model: str = None) -> dict:
    """
    Generate and parse JSON response from Ollama.
    Returns empty dict on failure.
    """
    response = generate(prompt, system=system, model=model, temperature=0.0)
    if not response:
        return {}
    
    # Try to find JSON in response (model might wrap in markdown)
    text = response
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        print(f"⚠️ Ollama returned non-JSON: {response[:200]}")
        return {}


# Alias for backward compatibility with entity_extractor.py
is_ollama_available = is_available


def extract_entities_llm(text: str) -> list:
    """
    Extract entities from text using Ollama LLM.
    Returns list of (entity_name, entity_type) tuples.
    
    Entity types: person, organization, location, tech, concept, 
                  product, project, temporal, event
    """
    system = """You are an entity extraction system. Extract named entities from the given text.
Return ONLY a JSON array of objects with "name" and "type" fields.
Entity types: person, organization, location, tech, concept, product, project, temporal, event.

Rules:
- Extract specific, meaningful entities (not generic words like "system" or "project")
- Preserve original language (don't translate Russian to English or vice versa)
- For technical terms, use type "tech"
- For abstract ideas, use type "concept"
- Merge duplicates (same entity mentioned differently)
- Return empty array [] if no meaningful entities found

Example input: "Artem configured Docker on Mac Studio for the HippoGraph project"
Example output: [{"name": "Artem", "type": "person"}, {"name": "Docker", "type": "tech"}, {"name": "Mac Studio", "type": "tech"}, {"name": "HippoGraph", "type": "project"}]"""

    prompt = f"Extract entities from this text:\n\n{text}"
    
    result = extract_json(prompt, system=system)
    
    if isinstance(result, list):
        entities = []
        for item in result:
            if isinstance(item, dict) and "name" in item and "type" in item:
                name = str(item["name"]).strip()
                etype = str(item["type"]).strip().lower()
                if len(name) >= 2:
                    entities.append((name, etype))
        return entities
    
    return []
