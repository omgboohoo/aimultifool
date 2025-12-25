import json
from pathlib import Path

def get_models():
    """Get list of model files from models directory"""
    models_dir = Path(__file__).parent / "models"
    if not models_dir.exists():
        models_dir.mkdir(parents=True, exist_ok=True)
    
    model_files = list(models_dir.glob("*.gguf"))
    return sorted(model_files)

def get_model_cache_path():
    """Get path to model configuration cache file"""
    return Path(__file__).parent / "model_cache.json"

def load_model_cache():
    """Load model configuration cache"""
    cache_path = get_model_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_model_cache(cache):
    """Save model configuration cache"""
    cache_path = get_model_cache_path()
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except IOError:
        pass

def get_cache_key(model_path, context_size):
    """Generate cache key for model path and context size"""
    return f"{model_path}:{context_size}"

def count_tokens_in_messages(llm, messages):
    """Count total tokens in message history"""
    if not llm:
        return 0
    total_tokens = 0
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            text = content
        elif role == "user":
            text = content
        else:
            text = f"Assistant: {content}"
        tokens = llm.tokenize(text.encode("utf-8"), add_bos=False, special=False)
        total_tokens += len(tokens)
    total_tokens += (len(messages) - 1) * 2
    return total_tokens

def prune_messages_if_needed(llm, messages, context_size):
    """
    Prune messages when context exceeds 80%.
    """
    if not llm or len(messages) <= 2:
        return messages
    
    current_tokens = count_tokens_in_messages(llm, messages)
    threshold = int(context_size * 0.8)
    
    if current_tokens > threshold:
        target_tokens = int(context_size * 0.6)
        while len(messages) > 2 and count_tokens_in_messages(llm, messages) > target_tokens:
            messages.pop(1)
    
    return messages
