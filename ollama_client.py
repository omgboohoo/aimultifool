"""
Ollama client wrapper that mimics the llama_cpp.Llama interface
for seamless integration with the existing codebase.
"""

import json
import requests
from typing import Generator, Dict, Any, List, Optional
from pathlib import Path


class OllamaClient:
    """
    Wrapper around Ollama API that mimics llama_cpp.Llama interface.
    This allows Ollama models to be used as drop-in replacements for local models.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        self.model_name = None
        self.context_size = 8192
    
    def load(self, model_name: str, n_ctx: int = 8192):
        """Load a model (equivalent to Llama.__init__)."""
        self.model_name = model_name
        self.context_size = n_ctx
        # Verify model exists by checking if it's in the list
        try:
            models = self.list_models()
            if model_name not in models:
                raise ValueError(f"Model '{model_name}' not found in Ollama. Available models: {', '.join(models)}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Ollama: {e}")
    
    def list_models(self) -> List[str]:
        """Get list of available Ollama models (excluding embedding models)."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            models = []
            for model in data.get("models", []):
                # Extract model name (may include tag like "llama3.2:latest")
                model_name = model.get("name", "")
                if model_name:
                    # Filter out embedding models (case-insensitive)
                    if "embed" not in model_name.lower() and "nomic" not in model_name.lower():
                        models.append(model_name)
            return models
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Ollama. Make sure Ollama is running on localhost:11434")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch Ollama models: {e}")
    
    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        max_tokens: Optional[int] = None,
        temperature: float = 0.8,
        top_p: float = 0.9,
        top_k: int = 40,
        repeat_penalty: float = 1.0,
        min_p: float = 0.0,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Create a chat completion, mimicking llama_cpp.Llama.create_chat_completion.
        Returns a generator that yields chunks in the same format as llama_cpp.
        """
        if not self.model_name:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Convert messages format if needed
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Ollama uses "assistant" not "assistant"
            if role == "assistant":
                ollama_messages.append({"role": "assistant", "content": content})
            elif role == "user":
                ollama_messages.append({"role": "user", "content": content})
            elif role == "system":
                ollama_messages.append({"role": "system", "content": content})
        
        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repeat_penalty": repeat_penalty,
                "min_p": min_p,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=stream,
                timeout=None  # No timeout for streaming
            )
            response.raise_for_status()
            
            if stream:
                # Stream response
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("done", False):
                            # Signal completion - yield empty content to indicate end
                            break
                        
                        # Ollama streams content in chunks via message.content
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield {"choices": [{"delta": {"content": content}}]}
                    except json.JSONDecodeError:
                        continue
            else:
                # Non-streaming response
                data = response.json()
                content = data.get("message", {}).get("content", "")
                yield {"choices": [{"delta": {"content": content}}]}
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Ollama. Make sure Ollama is running.")
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")
    
    def tokenize(self, text: bytes, add_bos: bool = False, special: bool = False) -> List[int]:
        """
        Tokenize text. Since Ollama doesn't expose tokenization directly,
        we use a simple approximation: ~4 characters per token.
        This is used for token counting, so approximation is acceptable.
        """
        # Simple approximation: ~4 chars per token for English
        # This is used for context window management, so precision isn't critical
        text_str = text.decode("utf-8", errors="ignore")
        approx_tokens = max(1, len(text_str) // 4)
        return list(range(approx_tokens))  # Return dummy token IDs
    
    def unload(self):
        """Unload the model from GPU memory by calling Ollama API with keep_alive=0."""
        if not self.model_name:
            return  # No model to unload
        
        try:
            # Call /api/generate with keep_alive=0 to force model unload
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": "",  # Empty prompt
                    "keep_alive": "0"  # 0 means unload immediately
                },
                timeout=5
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            # Ollama not running, nothing to unload
            pass
        except Exception:
            # Ignore errors - best effort unload
            pass
    
    def close(self):
        """Clean up resources - unload model from GPU memory."""
        self.unload()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_ollama_models(base_url: str = "http://localhost:11434") -> List[str]:
    """Get list of available Ollama models."""
    client = OllamaClient(base_url)
    return client.list_models()
