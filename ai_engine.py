import json
from pathlib import Path
from typing import List, Union

def get_models(inference_mode: str = "local") -> List[Union[Path, str]]:
    """
    Get list of models based on inference mode.
    
    Args:
        inference_mode: "local" for local GGUF files, "ollama" for Ollama models
    
    Returns:
        List of model paths (Path objects for local, strings for Ollama)
    """
    if inference_mode == "ollama":
        try:
            from ollama_client import get_ollama_models
            # Try to get ollama_url from app if available, otherwise use default
            base_url = "http://localhost:11434"
            try:
                import sys
                # Try to get from app instance if available
                if hasattr(sys.modules.get('__main__', None), 'app'):
                    app = sys.modules['__main__'].app
                    if hasattr(app, 'ollama_url'):
                        url = app.ollama_url
                        if url and '://' not in url:
                            base_url = f"http://{url}"
                        elif url:
                            base_url = url
            except Exception:
                pass
            models = get_ollama_models(base_url)
            return models
        except Exception:
            # If Ollama is not available, return empty list
            return []
    else:
        # Local mode - get GGUF files
        models_dir = Path(__file__).parent / "models"
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
        
        model_files = [m for m in models_dir.glob("*.gguf") if "nomic" not in m.name.lower() and "embed" not in m.name.lower()]
        return sorted(model_files)

def get_model_cache_path():
    """Get path to model configuration cache file"""
    return Path(__file__).parent / "model_cache.json"

def load_model_cache():
    """Load model configuration cache"""
    cache_path = get_model_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_model_cache(cache):
    """Save model configuration cache"""
    cache_path = get_model_cache_path()
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
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
        
        # Check if it's an Ollama client (has tokenize method that returns list)
        if hasattr(llm, 'tokenize'):
            tokens = llm.tokenize(text.encode("utf-8"), add_bos=False, special=False)
            total_tokens += len(tokens)
        else:
            # Fallback for llama_cpp
            tokens = llm.tokenize(text.encode("utf-8"), add_bos=False, special=False)
            total_tokens += len(tokens)
    
    total_tokens += (len(messages) - 1) * 2
    return total_tokens

def prune_messages_if_needed(llm, messages, context_size):
    """
    Prune messages when context exceeds 85%.
    Preserves system prompt and first 3 exchanges (3 user prompts + 3 AI replies),
    then removes from the middle one by one until we're at or below 60% target.
    """
    if not llm or len(messages) <= 2:
        return messages
    
    current_tokens = count_tokens_in_messages(llm, messages)
    threshold = int(context_size * 0.85)
    
    if current_tokens > threshold:
        target_tokens = int(context_size * 0.6)
        
        # Preserve system prompt (index 0) and first 3 exchanges (indices 1-6)
        # First 3 exchanges = 3 user prompts + 3 AI replies = 6 messages
        preserve_first_count = min(7, len(messages))  # System + 6 messages for 3 exchanges
        
        # If we have more messages than what we're preserving, we need to prune
        if len(messages) > preserve_first_count:
            # Start with all messages
            pruned_messages = messages.copy()
            
            # Delete messages one by one from after the preserved section
            # Keep deleting until we're at or below target token count
            # Always keep the last message
            while count_tokens_in_messages(llm, pruned_messages) > target_tokens and len(pruned_messages) > preserve_first_count + 1:
                # Remove the message right after the preserved section
                pruned_messages.pop(preserve_first_count)
            
            return pruned_messages
        else:
            # Not enough messages to prune, but still over threshold
            # Just remove from middle if possible
            pruned_messages = messages.copy()
            while count_tokens_in_messages(llm, pruned_messages) > target_tokens and len(pruned_messages) > 2:
                if len(pruned_messages) > 3:
                    middle_idx = len(pruned_messages) // 2
                    pruned_messages.pop(middle_idx)
                else:
                    break
            return pruned_messages
    
    return messages
