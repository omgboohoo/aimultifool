import time
import gc
import asyncio
import threading
import uuid
import json
from pathlib import Path
from textual import work
from textual.widgets import Select
from queue import Queue
import sys

# Imports for functional logic
from ai_engine import (
    load_model_cache, save_model_cache, get_cache_key, 
    count_tokens_in_messages, prune_messages_if_needed,
    get_models
)
from character_manager import create_initial_messages
from utils import DOWNLOAD_AVAILABLE, save_settings, load_settings, get_style_prompt, encrypt_data, decrypt_data
from widgets import MessageWidget

# Windows-specific subprocess embedding support
if sys.platform == "win32":
    try:
        from llm_subprocess_client import SubprocessEmbedder
    except ImportError:
        SubprocessEmbedder = None
else:
    SubprocessEmbedder = None

# Optional for download
if DOWNLOAD_AVAILABLE:
    import requests

try:
    import qdrant_client
    from qdrant_client.models import PointStruct, VectorParams, Distance
except ImportError:
    qdrant_client = None

# Global lock to prevent concurrent inference operations
_inference_lock = threading.Lock()

class InferenceMixin:
    """Mixin for handling AI inference and model loading tasks."""
    
    @work(exclusive=True, thread=True)
    def run_inference(self, user_text: str):
        # Clear the starting flag once inference actually begins (or fails)
        self.call_from_thread(setattr, self, "_inference_starting", False)
        
        # Try to acquire the lock with a timeout to prevent deadlocks
        if not _inference_lock.acquire(timeout=5.0):
            self.call_from_thread(self.notify, "Another inference is still running. Please wait.", severity="warning")
            self.call_from_thread(setattr, self, "is_loading", False)
            self.call_from_thread(setattr, self, "status_text", "Ready")
            return
        
        try:
            if not self.llm:
                self.call_from_thread(self.notify, "Model not loaded! Load a model from the sidebar first.", severity="error")
                self.call_from_thread(setattr, self, "is_loading", False)
                self.call_from_thread(setattr, self, "status_text", "Ready")
                self.call_from_thread(setattr, self, "_inference_starting", False)
                return

            # Only set status after lock is acquired and model is confirmed loaded
            self.call_from_thread(setattr, self, "status_text", "Thinking...")
            
            # Get a snapshot of current messages to avoid race conditions
            messages_to_use = [msg.copy() for msg in self.messages]
            
            # Ensure the user's current message is in the list
            if not messages_to_use or messages_to_use[-1].get("role") != "user":
                messages_to_use.append({"role": "user", "content": user_text})
            elif messages_to_use[-1].get("content") != user_text:
                messages_to_use[-1]["content"] = user_text
            
            # Prune if needed
            messages_to_use = prune_messages_if_needed(self.llm, messages_to_use, self.context_size)
            
            # Update self.messages with pruned version
            self.call_from_thread(self._update_messages_safely, messages_to_use)
            
            # Calculate initial token count
            prompt_tokens = count_tokens_in_messages(self.llm, messages_to_use)
            
            assistant_widget = None
            assistant_content = ""
            
            try:
                
                self.call_from_thread(setattr, self, "status_text", f"Thinking (T:{self.temp} P:{self.topp})...")
                
                # Retrieve vector context if enabled
                if getattr(self, "enable_vector_chat", False) and user_text.lower() != "continue":
                    self.call_from_thread(setattr, self, "status_text", "Retrieving context...")
                    context_msgs = self.retrieve_similar_context(user_text)
                    if context_msgs:
                        # Prepend context messages after the system prompt (index 0)
                        # This makes them appear as part of the conversation history
                        insert_idx = 1 if len(messages_to_use) > 0 and messages_to_use[0]["role"] == "system" else 0
                        for i, msg in enumerate(context_msgs):
                            messages_to_use.insert(insert_idx + i, msg)
                        
                        self.call_from_thread(setattr, self, "status_text", f"Recall: {len(context_msgs)//2} memories found.")
                        # Small delay so user can see it found something
                        time.sleep(0.5)
                        self.call_from_thread(setattr, self, "status_text", "Thinking with context...")
                    else:
                        # Make it explicit when RAG found nothing (helps debugging)
                        self.call_from_thread(setattr, self, "status_text", "Recall: 0 memories found.")
                
                # Retrieve RLM context if enabled (Recursive Language Models approach)
                if getattr(self, "enable_rlm_chat", False) and user_text.lower() != "continue":
                    self.call_from_thread(setattr, self, "status_text", "Querying RLM context...")
                    rlm_context_msgs = self.query_rlm_context(user_text)
                    if rlm_context_msgs:
                        # Prepend RLM context after system prompt
                        insert_idx = 1 if len(messages_to_use) > 0 and messages_to_use[0]["role"] == "system" else 0
                        # Format RLM context as system messages to indicate they're from external store
                        for i, msg in enumerate(rlm_context_msgs[:10]):  # Limit to 10 most relevant
                            # Get content and strip any existing RLM Context prefix to prevent double-formatting
                            content = msg.get('content', '')
                            # Remove any existing "[RLM Context" prefix if present
                            if content.startswith("[RLM Context"):
                                # Find the colon after the prefix and extract the actual content
                                colon_idx = content.find("]:")
                                if colon_idx != -1:
                                    content = content[colon_idx + 2:].strip()
                            
                            rlm_msg = {
                                "role": "system",
                                "content": f"[RLM Context - {msg.get('role', 'unknown')}]: {content[:500]}"
                            }
                            messages_to_use.insert(insert_idx + i, rlm_msg)
                        
                        self.call_from_thread(setattr, self, "status_text", f"RLM: {len(rlm_context_msgs)} context chunks retrieved.")
                        time.sleep(0.3)
                        self.call_from_thread(setattr, self, "status_text", "Thinking with RLM context...")

                stream = self.llm.create_chat_completion(
                    messages=messages_to_use,
                    max_tokens=self.context_size - 100,
                    temperature=self.temp,
                    top_p=self.topp,
                    top_k=self.topk,
                    repeat_penalty=self.repeat,
                    min_p=self.minp,
                    stream=True
                )
                
                start_time = time.time()
                last_ui_update = 0  # Force first update
                last_status_update = 0
                token_count = 0
                peak_tps = 0.0
                
                was_cancelled = False
                for output in stream:
                    # Check for cancellation FIRST, before processing output
                    # This makes interruption detection immediate
                    if self.is_loading == False: # Cancelled
                        was_cancelled = True
                        # Close generator to drain remaining deltas
                        try:
                            if hasattr(stream, "close"):
                                stream.close()
                        except Exception:
                            pass
                        break
                        
                    text_chunk = output["choices"][0].get("delta", {}).get("content", "")
                    if not text_chunk:
                        continue
                    
                    assistant_content += text_chunk
                    
                    # Stats calculation (internal only, not UI yet)
                    chunk_tokens = self.llm.tokenize(text_chunk.encode("utf-8"), add_bos=False, special=False)
                    token_count += len(chunk_tokens)
                    
                    now = time.time()
                    
                    # Batch UI updates: 每 50ms 更新一次界面
                    if assistant_widget is None:
                        try:
                            assistant_widget = self.call_from_thread(self.sync_add_assistant_widget, assistant_content)
                            last_ui_update = now
                        except Exception:
                            was_cancelled = True
                            break
                    elif now - last_ui_update > 0.05:
                        try:
                            self.call_from_thread(self.sync_update_assistant_widget, assistant_widget, assistant_content)
                            last_ui_update = now
                        except Exception:
                            was_cancelled = True
                            break
                    
                    # Batch Status updates: 每 500ms 更新一次状态栏
                    if now - last_status_update > 0.5:
                        elapsed = now - start_time
                        tps = token_count / elapsed if elapsed > 0 else 0
                        peak_tps = max(peak_tps, tps)
                        
                        total_tokens = prompt_tokens + token_count
                        ctx_pct = (total_tokens / self.context_size) * 100
                        self.call_from_thread(setattr, self, "status_text", f"TPS: {tps:.1f} | Peak: {peak_tps:.1f} | Context: {ctx_pct:.1f}% | Tokens: {token_count}")
                        last_status_update = now

                # FINAL UPDATE: Ensure everything is flushed to UI after the stream finishes
                if assistant_widget and assistant_content:
                    self.call_from_thread(self.sync_update_assistant_widget, assistant_widget, assistant_content)

                if assistant_content:
                    try:
                        messages_to_use.append({"role": "assistant", "content": assistant_content})
                        
                        # Save to vector DB if enabled
                        if getattr(self, "enable_vector_chat", False) and user_text.lower() != "continue":
                            self.save_vector_entry(user_text, assistant_content)
                        
                        # Save to RLM context store if enabled
                        if getattr(self, "enable_rlm_chat", False) and user_text.lower() != "continue":
                            # Add user message and assistant response to RLM store
                            rlm_messages = [
                                {"role": "user", "content": user_text},
                                {"role": "assistant", "content": assistant_content}
                            ]
                            self.add_to_rlm_context(rlm_messages)

                        messages_to_use = prune_messages_if_needed(self.llm, messages_to_use, self.context_size)
                        self.call_from_thread(self._update_messages_safely, messages_to_use)
                        
                        final_tokens = count_tokens_in_messages(self.llm, messages_to_use)
                        final_pct = (final_tokens / self.context_size) * 100
                        
                        self.call_from_thread(setattr, self, "status_text", f"{'Stopped' if was_cancelled else 'Finished'}. {token_count} tokens. Peak TPS: {peak_tps:.1f} | Context: {final_pct:.1f}%")
                    except Exception:
                        pass
                
            except Exception as e:
                self.call_from_thread(self.notify, f"Error during inference: {e}", severity="error")
        finally:
            self.call_from_thread(setattr, self, "is_loading", False)
            self._inference_worker = None
            # Always release the lock
            _inference_lock.release()

    def load_model_task(self, model_path, context_size, requested_gpu_layers, inference_mode="local", needs_cleanup=False, old_llm=None):
        # Use manual threading with proper GIL release to prevent UI freezes on Windows
        # llama_cpp.Llama() can hold GIL in native code, so we need to ensure UI updates happen
        
        # Ensure model_path is a string (Windows path handling)
        model_path_str = str(model_path) if model_path else None
        if not model_path_str:
            self.is_model_loading = False
            return

        # Handle Ollama models differently
        if inference_mode == "ollama":
            # Create a queue for thread communication
            result_queue = Queue()
            
            # Define the blocking function to run in a manual thread
            def _load_ollama_thread():
                nonlocal old_llm
                llm = None
                
                try:
                    # Clean up old model if needed
                    if old_llm is not None:
                        try:
                            if hasattr(old_llm, "close"):
                                old_llm.close()
                            old_llm = None
                            gc.collect()
                        except Exception:
                            pass

                    # Update status
                    try:
                        self.call_from_thread(setattr, self, "status_text", f"Connecting to Ollama...")
                    except Exception:
                        pass
                    
                    # Small delay to allow UI to update
                    time.sleep(0.05)
                    
                    # Load Ollama client with configured URL
                    from ollama_client import OllamaClient
                    # Get ollama_url from app instance
                    ollama_url = getattr(self, "ollama_url", "127.0.0.1:11434")
                    if ollama_url and '://' not in ollama_url:
                        base_url = f"http://{ollama_url}"
                    elif ollama_url:
                        base_url = ollama_url
                    else:
                        base_url = "http://127.0.0.1:11434"
                    llm = OllamaClient(base_url=base_url)
                    llm.load(model_path_str, n_ctx=int(context_size))
                    
                    # Put result in queue
                    result_queue.put(("success", llm, 0))  # GPU layers not applicable for Ollama
                except Exception as e:
                    result_queue.put(("error", str(e), None))
            
            # Start the thread
            thread = threading.Thread(target=_load_ollama_thread, daemon=True, name="OllamaLoadThread")
            try:
                thread.start()
            except Exception as e:
                self.is_model_loading = False
                self.status_text = f"Thread start failed: {e}"
                return
            
            # Set up a periodic check for the result
            self._model_load_thread = thread
            self._model_load_queue = result_queue
            self.set_timer(0.1, self._check_model_load_result)
            return
        
        # Local model loading (original logic)
        if requested_gpu_layers == 0:
            layers_to_try = [0]
        else:
            cache = load_model_cache()
            cache_key = get_cache_key(model_path_str, context_size)
            
            cached_layers = None
            if cache_key in cache:
                cached_layers = cache[cache_key].get("gpu_layers")
            
            layers_to_try = []
            if cached_layers is not None:
                layers_to_try = [cached_layers]
                if cached_layers != requested_gpu_layers:
                    layers_to_try.append(requested_gpu_layers)
            else:
                layers_to_try = [requested_gpu_layers]
            
            if requested_gpu_layers == -1:
                fallback = list(range(64, -1, -4))
                for layer in fallback:
                    if layer not in layers_to_try:
                        layers_to_try.append(layer)
            else:
                current = requested_gpu_layers
                while current > 4:
                    current = current // 2
                    if current not in layers_to_try:
                        layers_to_try.append(current)
                if 0 not in layers_to_try:
                    layers_to_try.append(0)

        # Create a queue for thread communication
        result_queue = Queue()
        
        # Define the blocking function to run in a manual thread
        def _load_llama_thread():
            nonlocal old_llm
            llm = None
            actual_layers = 0
            
            try:
                # Clean up old model if needed (do this in thread, not main thread!)
                if old_llm is not None:
                    try:
                        if hasattr(old_llm, "close"):
                            old_llm.close()
                        old_llm = None
                        gc.collect()
                    except Exception:
                        pass

                last_err = None
                
                # Use direct llama_cpp for all platforms
                import llama_cpp
                for layers in layers_to_try:
                    try:
                        # Update status before blocking call - use call_from_thread to ensure UI updates
                        # Note: This might not work if GIL is held, but we try anyway
                        try:
                            self.call_from_thread(setattr, self, "status_text", f"Loading (GPU Layers: {layers})...")
                        except Exception:
                            pass
                        
                        # Small delay to allow UI to update before blocking
                        time.sleep(0.05)
                        
                        # This call can hold GIL in native code on Windows
                        llm = llama_cpp.Llama(
                            model_path=model_path_str,
                            n_ctx=int(context_size),
                            n_gpu_layers=int(layers),
                            verbose=False,
                        )
                        actual_layers = int(layers)
                        
                        # Cache the successful result
                        cache = load_model_cache()
                        cache_key = get_cache_key(model_path_str, context_size)
                        cache[cache_key] = {"gpu_layers": layers, "model_path": model_path_str, "context_size": int(context_size)}
                        save_model_cache(cache)
                        break
                    except Exception as e:
                        last_err = e
                        continue

                if llm is None and last_err is not None:
                    raise last_err
                
                # Put result in queue
                result_queue.put(("success", llm, actual_layers))
            except Exception as e:
                result_queue.put(("error", str(e), None))
        
        # Start the thread (daemon=True so it doesn't block app shutdown)
        thread = threading.Thread(target=_load_llama_thread, daemon=True, name="ModelLoadThread")
        try:
            thread.start()
        except Exception as e:
            self.is_model_loading = False
            self.status_text = f"Thread start failed: {e}"
            return
        
        # Set up a periodic check for the result
        self._model_load_thread = thread
        self._model_load_queue = result_queue
        # Start checking after a short delay (use set_timer for non-blocking)
        self.set_timer(0.1, self._check_model_load_result)
    
    def _check_model_load_result(self):
        """Check if model loading is complete and update UI."""
        if not hasattr(self, '_model_load_queue') or self._model_load_queue is None:
            return
        
        try:
            # Non-blocking check
            if not self._model_load_queue.empty():
                result_type, llm_or_error, actual_layers = self._model_load_queue.get_nowait()
                
                if result_type == "success":
                    llm = llm_or_error
                    if llm:
                        self.llm = llm
                        self.context_size = self.context_size  # Keep current
                        self.gpu_layers = actual_layers
                        layer_display = "all" if actual_layers == -1 else str(actual_layers)
                        self.notify(f"Model loaded successfully with {layer_display} GPU layers!")
                        self.enable_character_list()
                        # Get model name based on inference mode
                        inference_mode = getattr(self, "inference_mode", "local")
                        if inference_mode == "ollama":
                            model_name = self.selected_model
                        else:
                            model_name = Path(self.selected_model).stem
                        self.status_text = f"{model_name} Ready"
                    else:
                        self.notify("Failed to load model!", severity="error")
                        self.status_text = "Load Failed"
                else:
                    error_msg = llm_or_error
                    self.notify(f"Model loading error: {error_msg}", severity="error")
                    self.status_text = "Load Failed"
                
                # Clean up
                self.is_model_loading = False
                self._model_load_queue = None
                self._model_load_thread = None
                
                if self.llm:
                    self.focus_chat_input()
            else:
                # Still loading, check again in 0.1 seconds
                if hasattr(self, '_model_load_thread') and self._model_load_thread and self._model_load_thread.is_alive():
                    self.set_timer(0.1, self._check_model_load_result)
                else:
                    # Thread died unexpectedly
                    self.notify("Model loading thread terminated unexpectedly", severity="error")
                    self.status_text = "Load Failed"
                    self.is_model_loading = False
                    self._model_load_queue = None
                    self._model_load_thread = None
        except Exception as e:
            self.notify(f"Error checking model load: {e}", severity="error")
            self.status_text = "Load Failed"
            self.is_model_loading = False
            self._model_load_queue = None
            self._model_load_thread = None

    @work(exclusive=True, thread=True)
    def download_default_model(self):
        if not DOWNLOAD_AVAILABLE:
            self.call_from_thread(self.notify, "requests and tqdm required for download!", severity="error")
            return

        self.call_from_thread(setattr, self, "is_downloading", True)
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Default LLM
        llm_url = "https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf?download=true"
        llm_path = models_dir / "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
        
        # Embedding Model
        embed_url = "https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe-GGUF/resolve/main/nomic-embed-text-v2-moe.Q4_K_M.gguf?download=true"
        embed_path = models_dir / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
        
        downloads = [
            ("LLM", llm_url, llm_path),
            ("Embedding", embed_url, embed_path)
        ]
        
        import requests
        try:
            for name, url, path in downloads:
                if path.exists():
                    self.call_from_thread(self.notify, f"{name} already exists, skipping.", severity="information")
                    continue
                    
                self.status_text = f"Downloading {name} model..."
                response = requests.get(url, stream=True)
                response.raise_for_status()
                total_size_str = response.headers.get('content-length')
                total_size = int(total_size_str) if total_size_str else None
                
                downloaded = 0
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not self.is_downloading: # Cancel if app closing or whatever
                             break
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size and total_size > 0:
                                pct = (downloaded / total_size) * 100
                                self.status_text = f"Downloading {name}: {pct:.1f}% ({downloaded / 1024 / 1024:.1f} MB)"
                            else:
                                self.status_text = f"Downloading {name}: {downloaded / 1024 / 1024:.1f} MB"
                
                if not self.is_downloading:
                    break
                self.call_from_thread(self.notify, f"{name} downloaded successfully!")
            
            self.call_from_thread(self.update_model_list)
            self.status_text = "Ready"
        except Exception as e:
            self.call_from_thread(self.notify, f"Download failed: {e}", severity="error")
            self.status_text = "Download Failed"
        finally:
            self.call_from_thread(setattr, self, "is_downloading", False)

class ActionsMixin:
    """Mixin for handling application actions."""

    def _get_actions_lock(self):
        """Serialize stop/regenerate/reset actions to avoid race conditions (esp. on Windows)."""
        lock = getattr(self, "_actions_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            setattr(self, "_actions_lock", lock)
        return lock
    
    async def _check_lock_available(self) -> bool:
        """Check if the inference lock is actually available (not held by another thread)."""
        # Run lock check in thread executor to avoid blocking async event loop
        loop = asyncio.get_event_loop()
        def try_lock():
            # Try to acquire lock with very short timeout
            acquired = _inference_lock.acquire(timeout=0.01)
            if acquired:
                _inference_lock.release()
                return True
            return False
        
        try:
            return await loop.run_in_executor(None, try_lock)
        except Exception:
            return False
    
    async def _wait_for_cleanup_if_needed(self, max_wait_seconds: float = 2.0) -> None:
        """Wait for stop cleanup to finish if it's in progress. Used before starting new inference."""
        max_wait = int(max_wait_seconds * 33)  # 33 iterations per second (check every 0.03s)
        while max_wait > 0:
            # Check multiple conditions that indicate we should wait
            cleanup_in_progress = getattr(self, "_stop_cleanup_in_progress", False)
            has_worker = hasattr(self, "_inference_worker") and self._inference_worker is not None
            is_loading_state = getattr(self, "is_loading", False)
            
            # If any of these indicate work is happening, wait
            if cleanup_in_progress or (has_worker and is_loading_state):
                await asyncio.sleep(0.03)  # Reduced from 0.05 to 0.03 for faster checking
                max_wait -= 1
            else:
                break
        
        # One final check - if still in cleanup, wait a bit more (further reduced)
        if getattr(self, "_stop_cleanup_in_progress", False):
            await asyncio.sleep(0.03)  # Reduced from 0.05 to 0.03
        
        # Wait for lock to actually be available (not just worker cleared)
        # Further reduced wait time since interruption is now more responsive
        max_lock_waits = 30  # Reduced from 40 to 30 (1.5 seconds max instead of 2)
        lock_waits = 0
        while lock_waits < max_lock_waits:
            if await self._check_lock_available():
                break
            await asyncio.sleep(0.03)  # Reduced from 0.05 to 0.03 for faster checking
            lock_waits += 1
    
    async def _can_start_inference(self) -> bool:
        """Check if it's safe to start new inference. Returns True if safe, False otherwise."""
        # Don't start if cleanup is in progress
        if getattr(self, "_stop_cleanup_in_progress", False):
            return False
        # Don't start if there's still a worker active
        if hasattr(self, "_inference_worker") and self._inference_worker is not None:
            return False
        # Don't start if is_loading is still True (shouldn't happen, but check anyway)
        if getattr(self, "is_loading", False):
            return False
        # Don't start if another inference start is already in progress (prevents rapid typing issues)
        if getattr(self, "_inference_starting", False):
            return False
        return True

    async def _stop_generation_unlocked(self) -> None:
        """Inner stop logic. Caller must hold `_actions_lock`."""
        if self.is_loading or (hasattr(self, "_inference_worker") and self._inference_worker):
            # Set cleanup flag FIRST (before is_loading) to prevent race conditions
            setattr(self, "_stop_cleanup_in_progress", True)
            # Then set flag immediately for responsive UI
            self.is_loading = False
            # Clear inference starting flag to allow new inference after stop
            setattr(self, "_inference_starting", False)
            
            # Immediate feedback
            try:
                self.status_text = "Stopping..."
            except Exception:
                pass
            
            # Store worker reference before releasing lock
            worker_ref = getattr(self, "_inference_worker", None)
            
            # Release lock immediately so buttons become responsive
            # The cleanup will happen in background
            
            # Start background cleanup task
            asyncio.create_task(self._cleanup_stopped_worker(worker_ref))
        else:
            # Ensure cleanup flag is cleared if nothing was running
            setattr(self, "_stop_cleanup_in_progress", False)
            # Also clear inference starting flag
            setattr(self, "_inference_starting", False)
            self.status_text = "Ready"
    
    async def _cleanup_stopped_worker(self, worker_ref) -> None:
        """Background task to clean up stopped worker without blocking UI."""
        try:
            # Further reduced wait time for faster response - worker should exit quickly now
            # with more frequent interruption checks (every 0.1s)
            max_waits = 15  # Reduced from 20 to 15 (0.75 seconds max wait)
            while worker_ref and max_waits > 0:
                await asyncio.sleep(0.05)
                max_waits -= 1
                # Check if worker is still active - if it's been replaced or cleared, we're done
                current_worker = getattr(self, "_inference_worker", None)
                if current_worker != worker_ref:
                    # Worker has been replaced or cleared, cleanup is done
                    break

            # If still stuck after graceful wait, then and only then attempt a cancel
            current_worker = getattr(self, "_inference_worker", None)
            if current_worker == worker_ref:
                try:
                    current_worker.cancel()
                    await asyncio.sleep(0.03)  # Reduced from 0.05 to 0.03
                except Exception:
                    pass
                # Only clear if it's still the same worker
                if getattr(self, "_inference_worker", None) == worker_ref:
                    self._inference_worker = None

            # Minimal delay - worker should respond very quickly now
            await asyncio.sleep(0.01)  # Reduced from 0.02 to 0.01

            # Update status and clear cleanup flag (CRITICAL: must always clear this)
            try:
                self.status_text = "Stopped"
                # Don't show notification on Windows - buttons are already responsive
                # No persistent notification needed - UI buttons are already responsive
                pass
            except Exception:
                pass
        finally:
            # ALWAYS clear cleanup flag, even if errors occurred
            setattr(self, "_stop_cleanup_in_progress", False)
            # Also clear inference starting flag to ensure clean state
            setattr(self, "_inference_starting", False)
    
    async def action_stop_generation(self) -> None:
        """Gracefully stop the AI by setting the flag and waiting for the worker to exit."""
        # Use lock only to prevent concurrent stop calls, but release immediately
        async with self._get_actions_lock():
            await self._stop_generation_unlocked()
        # Lock is released here, making buttons immediately responsive

    def action_clear_history(self) -> None:
        if self.current_character:
            self.messages = create_initial_messages(self.current_character, self.user_name)
        else:
            style = self.query_one("#select-style").value
            content = get_style_prompt(style)
            self.messages = [{"role": "system", "content": content}]
        
        self.query_one("#chat-scroll").query("*").remove()
        self.notify("History cleared.")

    async def action_reset_chat(self) -> None:
        # Serialize with actions lock to prevent race conditions from rapid clicking
        async with self._get_actions_lock():
            # 1. Stop the AI gracefully (same method as Clear/Wipe All)
            await self._stop_generation_unlocked()
            
            # 2. Wait for cleanup to finish
            await self._wait_for_cleanup_if_needed()
            
            # 3. Safety gap for CUDA to settle
            await asyncio.sleep(0.2)
            
            # 4. Clear UI state
            try:
                self.query_one("#chat-input").value = ""
            except Exception:
                pass

            # 5. Reset messages
            if self.current_character:
                self.messages = create_initial_messages(self.current_character, self.user_name)
            else:
                self.messages = [{"role": "system", "content": ""}]
            
            # 6. Clear chat window
            self.query_one("#chat-scroll").query("*").remove()
            
            # 7. Apply style and print instructions
            if hasattr(self, "update_system_prompt_style"):
                # Suppress info message if restarting with a character card to keep it clean
                await self.update_system_prompt_style(self.style, suppress_info=bool(self.current_character))
            
            # 8. Restart the inference
            # Final safety check before starting
            if not await self._can_start_inference():
                await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                if not await self._can_start_inference():
                    self.notify("Please wait for current operation to finish.", severity="warning")
                    self.status_text = "Reset complete (inference delayed)"
                    self.focus_chat_input()
                    return
            
            if self.current_character and getattr(self, "force_ai_speak_first", True):
                # For character cards, we send 'continue' to trigger the character's first response
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages[-1]["content"] = "continue"
                else:
                    self.messages.append({"role": "user", "content": "continue"})
                self.is_loading = True
                self._inference_worker = self.run_inference("continue")
            elif self.first_user_message:
                user_text = self.first_user_message
                if user_text:
                    await self.add_message("user", user_text)
                    self.is_loading = True
                    self._inference_worker = self.run_inference(user_text)
                    
            self.status_text = "Reset complete"
            self.focus_chat_input()

    async def action_rewind(self) -> None:
        # Serialize with actions lock to prevent race conditions from rapid clicking
        async with self._get_actions_lock():
            if self.is_loading:
                await self._stop_generation_unlocked()
                await self._wait_for_cleanup_if_needed()

            if len(self.messages) <= 1:
                self.notify("Nothing to rewind.", severity="warning")
                return

            # 1. Pop the last interaction from the context window
            last_user_content = ""
            
            # Remove assistant message if it's the last one
            if self.messages[-1]["role"] == "assistant":
                self.messages.pop()
            
            # Remove user message if it's the last one
            if len(self.messages) > 1 and self.messages[-1]["role"] == "user":
                user_msg = self.messages.pop()
                last_user_content = user_msg.get("content", "")
                if self.first_user_message == last_user_content:
                    self.first_user_message = None
                
            # 2. Put the user's message back into the input box for editing
            try:
                if last_user_content and last_user_content != "continue":
                    # Strip newlines from action prompts when loading into input box
                    cleaned_content = last_user_content.replace('\n', ' ').replace('\r', ' ')
                    self.query_one("#chat-input").value = cleaned_content
            except Exception:
                pass

            # 3. Synchronize the UI perfectly with the new state
            if hasattr(self, "full_sync_chat_ui"):
                await self.full_sync_chat_ui()
            else:
                # Fallback for manual removal (less robust but safe)
                chat_scroll = self.query_one("#chat-scroll")
                # Remove trailing info widgets and the last context widgets
                widgets = [w for w in chat_scroll.children if isinstance(w, MessageWidget)]
                while widgets and (widgets[-1].is_info or len(list(w for w in widgets if not w.is_info)) > len(self.messages)-1):
                    widgets.pop().remove()

            self.notify("Rewound last interaction.")
            self.focus_chat_input()

    async def action_wipe_all(self) -> None:
        # Serialize with actions lock to prevent race conditions from rapid clicking
        async with self._get_actions_lock():
            await self._stop_generation_unlocked()
            await self._wait_for_cleanup_if_needed()
            
            # Ensure all inference state flags are cleared after cleanup
            setattr(self, "_inference_starting", False)
            setattr(self, "_inference_worker", None)
            
            self.current_character = None
            self.first_user_message = None
            self.messages = [{"role": "system", "content": ""}]
            
            self.query_one("#chat-scroll").query("*").remove()
            
            if hasattr(self, "update_system_prompt_style"):
                await self.update_system_prompt_style(self.style)
                
            self.notify("Chat wiped clean.")

    async def action_continue_chat(self) -> None:
        # Serialize with actions lock to prevent race conditions
        async with self._get_actions_lock():
            if not self.is_loading and self.llm:
                # Wait for cleanup to finish if it's in progress
                await self._wait_for_cleanup_if_needed()
                
                # Final safety check before starting
                if not await self._can_start_inference():
                    await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                    if not await self._can_start_inference():
                        self.notify("Please wait for current operation to finish.", severity="warning")
                        return
                
                user_text = "continue"
                await self.add_message("user", user_text)
                self.is_loading = True
                self._inference_worker = self.run_inference(user_text)

    async def action_regenerate(self) -> None:
        """Regenerate the last AI reply by removing it and re-running inference."""
        # Safety: disable regenerate during streaming (UI also disables button)
        # to avoid protocol interleaving / crashes.
        if getattr(self, "is_loading", False):
            self.notify("Regenerate is disabled while AI is speaking. Stop first, then Regenerate.", severity="warning")
            return
        
        # Check if stop cleanup is in progress - wait briefly if so
        await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
        
        # Serialize regenerate requests so repeated button presses can't interleave
        # with stop / UI rebuild / worker startup.
        async with self._get_actions_lock():
            if getattr(self, "_regen_in_progress", False):
                # Ignore extra clicks (prevents crashes from re-entrancy)
                return
            self._regen_in_progress = True
            try:
                # Windows safety: don't remove/update widgets while the inference thread may still
                # be streaming UI updates. Instead, stop generation, mutate message state, then
                # rebuild the chat UI from state and restart inference.
                was_loading = bool(self.is_loading)

                if not self.llm:
                    self.notify("No model loaded!", severity="warning")
                    return

                if len(self.messages) <= 1:
                    self.notify("Nothing to regenerate.", severity="warning")
                    return

                # If currently generating, stop first (but don't wait long - cleanup is async)
                if was_loading:
                    await self._stop_generation_unlocked()
                    # Brief wait for worker to start shutting down, but don't block UI
                    await asyncio.sleep(0.1)

                # If the last message is an assistant (possibly partial from a cancelled stream), remove it.
                if self.messages and self.messages[-1].get("role") == "assistant":
                    self.messages.pop()

                # Find the last user message to regenerate from
                user_text = None
                for i in range(len(self.messages) - 1, -1, -1):
                    if self.messages[i].get("role") == "user":
                        user_text = self.messages[i].get("content")
                        break

                if not user_text:
                    self.notify("Could not find user message to regenerate from.", severity="warning")
                    return

                # Rebuild UI to match message state (avoids widget races/crashes)
                if hasattr(self, "full_sync_chat_ui"):
                    await self.full_sync_chat_ui()

                # Final safety check before starting inference
                if not await self._can_start_inference():
                    await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                    if not await self._can_start_inference():
                        self.notify("Please wait for current operation to finish.", severity="warning")
                        return
                
                # Re-run inference with the same user message
                self.is_loading = True
                self._inference_worker = self.run_inference(user_text)
                self.notify("Regenerating last reply...")
            finally:
                self._regen_in_progress = False

    def save_user_settings(self):
        settings = {
            "user_name": self.user_name,
            "context_size": self.context_size,
            "gpu_layers": self.gpu_layers,
            "selected_model": self.selected_model,
            "inference_mode": getattr(self, "inference_mode", "local"),
            "temp": self.temp,
            "topp": self.topp,
            "topk": self.topk,
            "repeat": self.repeat,
            "minp": self.minp,
            "style": self.style
        }
        save_settings(settings)
        
        # Save RLM context if enabled
        if getattr(self, "enable_rlm_chat", False):
            try:
                self.save_rlm_context()
            except Exception:
                pass

class VectorMixin:
    """Mixin for handling Vector DB (RAG) operations."""
    qdrant_instance = None
    embed_llm = None
    vector_password = None
    vector_collection_name = "chat_memory"
    _embedder = None
    _subprocess_embedder = None  # Windows subprocess embedder

    def _ensure_collection_dim(self, dim: int) -> None:
        """Ensure the active collection exists with the right vector dimension."""
        if not self.qdrant_instance or not dim:
            return

        # Use a dimension-specific collection name to avoid destroying older data.
        desired = f"chat_memory_{dim}"
        self.vector_collection_name = desired

        try:
            # If it exists, we're good
            self.qdrant_instance.get_collection(desired)
            return
        except Exception:
            pass

        try:
            self.qdrant_instance.create_collection(
                collection_name=desired,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        except Exception as e:
            # If it already exists (race), ignore
            if "already exists" not in str(e).lower():
                raise

    def validate_vector_password(self, name: str, password: str):
        """Pre-validation check for vector chat passwords without setting state."""
        if not qdrant_client:
            return # No-op if client not available
            
        vectors_dir = Path(__file__).parent / "vectors" / name
        if not (vectors_dir / ".encrypted").exists():
            return True # Not encrypted
            
        if not password:
            raise ValueError("Password required for encrypted vector chat.")
            
        # 1. Try verify.bin first
        verify_file = vectors_dir / "verify.bin"
        if verify_file.exists():
            try:
                with open(verify_file, "r") as f:
                    enc_v = f.read()
                decrypt_data(enc_v, password)
                return True
            except Exception:
                raise ValueError("Incorrect password for encrypted vector chat.")
        
        # 2. If no verify.bin, try scrolling points to find an encrypted one
        # Use a temporary client for validation to avoid locking the main process if possible
        temp_client = None
        try:
            temp_client = qdrant_client.QdrantClient(path=str(vectors_dir))
            collections = temp_client.get_collections().collections
            verified = False
            found_encrypted = False
            for coll in collections:
                res = temp_client.scroll(collection_name=coll.name, limit=10, with_payload=True)
                if res and res[0]:
                    for point in res[0]:
                        if point.payload.get("encrypted"):
                            found_encrypted = True
                            try:
                                decrypt_data(point.payload["text"], password)
                                verified = True
                                break
                            except Exception:
                                pass # Try next point
                if verified: break
            
            if found_encrypted and not verified:
                raise ValueError("Incorrect password for encrypted vector chat.")
            
            return True
        except Exception as e:
            if "Incorrect password" in str(e) or isinstance(e, ValueError):
                raise e
            return True # If we can't open it to check, allow fallthrough to main init
        finally:
            if temp_client:
                try: temp_client.close()
                except Exception: pass

    def initialize_vector_db(self, name: str):
        try:
            if not qdrant_client:
                self.notify("qdrant-client not installed!", severity="error")
                return
            
            # Close existing instance if any
            self.close_vector_db()
                
            vectors_dir = Path(__file__).parent / "vectors" / name
            vectors_dir.mkdir(parents=True, exist_ok=True)
            
            self.qdrant_instance = qdrant_client.QdrantClient(path=str(vectors_dir))
            
            # Default collection (we may switch to dimension-specific collection after first embedding)
            self.vector_collection_name = "chat_memory"

            # Try to get collection info to check if it exists
            try:
                self.qdrant_instance.get_collection(self.vector_collection_name)
                # Collection exists, we're good to go
            except Exception:
                # Collection doesn't exist, need to create it
                pass

            # Password validation for encrypted chats
            if (vectors_dir / ".encrypted").exists():
                self.validate_vector_password(name, self.vector_password)
                
                # Create verify.bin if it doesn't exist yet (and we haven't failed yet)
                verify_file = vectors_dir / "verify.bin"
                if not verify_file.exists():
                    try:
                        enc_v = encrypt_data("verification_string", self.vector_password)
                        with open(verify_file, "w") as f:
                            f.write(enc_v)
                    except Exception:
                        pass
            
            # If we reached here, either it's not encrypted or password is correct
            # If collection exists, we can return now
            try:
                self.qdrant_instance.get_collection(self.vector_collection_name)
                return
            except Exception:
                pass
            
            # Default dimension for nomic models (will be verified on first embedding)
            dim = 768
            
            try:
                self.qdrant_instance.create_collection(
                    collection_name=self.vector_collection_name,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
                )
            except Exception as e:
                err_msg = str(e).lower()
                if "already exists" not in err_msg:
                    self.notify(f"Database initialization error: {e}", severity="error")
        except Exception as e:
            raise e
            
    def close_vector_db(self):
        """Safely close and clear the current vector database instance."""
        if self.qdrant_instance:
            try:
                # Explicitly close the client to release file locks
                self.qdrant_instance.close()
            except Exception:
                pass
            self.qdrant_instance = None
        
        # Close subprocess embedder on Windows
        if hasattr(self, "_subprocess_embedder") and self._subprocess_embedder is not None:
            try:
                self._subprocess_embedder.close()
            except Exception:
                pass
            self._subprocess_embedder = None
        
        # Clear direct embedder
        if hasattr(self, "_embed_llm") and self._embed_llm is not None:
            try:
                if hasattr(self._embed_llm, "close"):
                    self._embed_llm.close()
            except Exception:
                pass
            self._embed_llm = None

    def get_embedding(self, text: str, task: str = "document"):
        """Get embedding for text. task can be 'document' or 'query' for Nomic 1.5 prefixes."""
        try:
            embed_model_path = Path(__file__).parent / "models" / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
            if not embed_model_path.exists():
                try:
                    self.call_from_thread(self.notify, "Embedding model not found! Download it first.", severity="error")
                except Exception:
                    # If we can't notify (e.g., in worker thread), just return None
                    pass
                return None
            
            # Windows: Use subprocess embedder to avoid blocking worker threads
            if sys.platform == "win32" and SubprocessEmbedder is not None:
                if not hasattr(self, "_subprocess_embedder") or self._subprocess_embedder is None:
                    try:
                        worker_path = Path(__file__).parent / "llm_subprocess_worker.py"
                        if not worker_path.exists():
                            raise FileNotFoundError(f"Worker script not found: {worker_path}")
                        python_exe = sys.executable
                        self._subprocess_embedder = SubprocessEmbedder(
                            python_exe=python_exe,
                            worker_path=str(worker_path)
                        )
                        # Load the embedding model
                        self._subprocess_embedder.load(
                            model_path=str(embed_model_path),
                            n_ctx=2048,
                            timeout_s=120.0
                        )
                    except Exception as e:
                        # If subprocess embedder fails, fall back to direct llama_cpp
                        # (may block on Windows, but better than failing completely)
                        try:
                            self.call_from_thread(self.notify, f"Subprocess embedder failed, using direct mode: {e}", severity="warning")
                        except Exception:
                            pass
                        # Fall through to direct llama_cpp path
                        if not hasattr(self, "_embed_llm") or self._embed_llm is None:
                            import llama_cpp
                            self._embed_llm = llama_cpp.Llama(
                                model_path=str(embed_model_path),
                                n_ctx=2048,
                                n_gpu_layers=0,
                                embedding=True,
                                verbose=False,
                            )
                        prefix = "search_document: " if task == "document" else "search_query: "
                        emb_result = self._embed_llm.create_embedding(prefix + text)
                        emb = emb_result["data"][0]["embedding"]
                        if emb:
                            try:
                                self._ensure_collection_dim(len(emb))
                            except Exception as e:
                                try:
                                    self.call_from_thread(self.notify, f"Vector DB dimension setup failed: {e}", severity="error")
                                except Exception:
                                    pass
                        return emb
                
                # Get embedding via subprocess
                try:
                    emb = self._subprocess_embedder.embed(text, task=task, timeout_s=30.0)
                except Exception as e:
                    # If embedding fails, try to reinitialize and retry once
                    try:
                        if hasattr(self, "_subprocess_embedder") and self._subprocess_embedder is not None:
                            self._subprocess_embedder.close()
                        self._subprocess_embedder = None
                        # Retry initialization
                        worker_path = Path(__file__).parent / "llm_subprocess_worker.py"
                        python_exe = sys.executable
                        self._subprocess_embedder = SubprocessEmbedder(
                            python_exe=python_exe,
                            worker_path=str(worker_path)
                        )
                        self._subprocess_embedder.load(
                            model_path=str(embed_model_path),
                            n_ctx=2048,
                            timeout_s=120.0
                        )
                        emb = self._subprocess_embedder.embed(text, task=task, timeout_s=30.0)
                    except Exception as retry_e:
                        try:
                            self.call_from_thread(self.notify, f"Embedding failed: {retry_e}", severity="error")
                        except Exception:
                            pass
                        return None
                
                # Ensure collection dimension matches embeddings
                if emb:
                    try:
                        self._ensure_collection_dim(len(emb))
                    except Exception as e:
                        try:
                            self.call_from_thread(self.notify, f"Vector DB dimension setup failed: {e}", severity="error")
                        except Exception:
                            pass
                return emb
            else:
                # Non-Windows: Use direct llama_cpp
                if not hasattr(self, "_embed_llm") or self._embed_llm is None:
                    import llama_cpp
                    self._embed_llm = llama_cpp.Llama(
                        model_path=str(embed_model_path),
                        n_ctx=2048,
                        n_gpu_layers=0,
                        embedding=True,
                        verbose=False,
                    )
                prefix = "search_document: " if task == "document" else "search_query: "
                emb_result = self._embed_llm.create_embedding(prefix + text)
                emb = emb_result["data"][0]["embedding"]
                # Ensure collection dimension matches embeddings
                if emb:
                    try:
                        self._ensure_collection_dim(len(emb))
                    except Exception as e:
                        try:
                            self.call_from_thread(self.notify, f"Vector DB dimension setup failed: {e}", severity="error")
                        except Exception:
                            pass
                return emb
        except Exception as e:
            try:
                self.call_from_thread(self.notify, f"Embedding error: {e}", severity="error")
            except Exception:
                pass
            return None

    def retrieve_similar_context(self, user_text: str, k=3):
        if not self.qdrant_instance:
            return []
            
        emb = self.get_embedding(user_text, task="query")
        if not emb:
            return []
            
        try:
            results = self.qdrant_instance.query_points(
                collection_name=getattr(self, "vector_collection_name", "chat_memory"),
                query=emb,
                limit=k
            )
            
            context_messages = []
            for point in results.points:
                text = point.payload.get("text", "")
                if not text:
                    continue
                
                # Decrypt if needed
                if point.payload.get("encrypted", False):
                    if not self.vector_password:
                        # Should have been caught earlier, but safety first
                        continue
                    try:
                        text = decrypt_data(text, self.vector_password)
                    except Exception:
                        continue

                # Try to split back into User/Assistant roles
                parts = text.split("\nAssistant: ")
                if len(parts) == 2:
                    user_part = parts[0].replace("User: ", "").strip()
                    assistant_part = parts[1].strip()
                    if user_part:
                        context_messages.append({"role": "user", "content": f"[Past Context]: {user_part}"})
                    if assistant_part:
                        context_messages.append({"role": "assistant", "content": assistant_part})
                else:
                    # Fallback for simple text entries
                    context_messages.append({"role": "system", "content": f"Relevant past context: {text}"})
                    
            return context_messages
        except Exception as e:
            self.notify(f"Vector search error: {e}", severity="error")
            return []

    def save_vector_entry(self, user_text: str, assistant_text: str):
        if not self.qdrant_instance or not self.enable_vector_chat:
            return
            
        combined_text = f"User: {user_text}\nAssistant: {assistant_text}"
        
        # Encrypt if password set
        payload_text = combined_text
        is_encrypted = False
        if self.vector_password:
            try:
                payload_text = encrypt_data(combined_text, self.vector_password)
                is_encrypted = True
            except Exception as e:
                self.notify(f"Vector encryption failed: {e}", severity="error")
                return

        emb = self.get_embedding(combined_text, task="document")
        if not emb:
            return
            
        try:
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload={"text": payload_text, "encrypted": is_encrypted}
            )
            self.qdrant_instance.upsert(collection_name=getattr(self, "vector_collection_name", "chat_memory"), points=[point])
        except Exception as e:
            self.notify(f"Failed to save vector entry: {e}", severity="error")


class RLMMixin:
    """Mixin for handling RLM (Recursive Language Models) context management."""
    rlm_context_store = None
    rlm_password = None
    rlm_collection_name = None
    _rlm_password_backup = None  # Backup to ensure password persists even if reactive clears it
    
    def validate_rlm_password(self, password):
        """Validator for reactive rlm_password attribute. Normalizes empty strings to None."""
        # Allow None or string values
        if password is None:
            return None
        if isinstance(password, str):
            # Normalize empty strings to None
            password = password.strip()
            return password if password else None
        # Reject other types
        raise ValueError("Password must be a string or None")
    
    def check_rlm_password(self, name: str, password):
        """Pre-validation check for RLM chat passwords without setting state."""
        rlm_dir = Path(__file__).parent / "rlmcontexts" / name
        
        # If .encrypted doesn't exist, no password needed
        if not (rlm_dir / ".encrypted").exists():
            return True  # Not encrypted
        
        # Normalize password: None or empty string means no password
        # But if .encrypted exists, we need a password
        if not password:
            raise ValueError("Password required for encrypted RLM chat.")
        
        # Ensure password is a string (not None)
        if not isinstance(password, str):
            raise ValueError("Password must be a string.")
        
        password = password.strip()
        if not password:
            raise ValueError("Password required for encrypted RLM chat.")
            
        # Try verify.bin first
        verify_file = rlm_dir / "verify.bin"
        if verify_file.exists():
            try:
                with open(verify_file, "r") as f:
                    enc_v = f.read()
                decrypt_data(enc_v, password)
                return True
            except ValueError as e:
                # Re-raise ValueError as-is (it has the error message)
                raise
            except Exception as e:
                raise ValueError("Incorrect password for encrypted RLM chat.")
        
        return True
    
    def initialize_rlm_context(self, name: str):
        """Initialize RLM context store for a given name."""
        try:
            rlm_dir = Path(__file__).parent / "rlmcontexts" / name
            rlm_dir.mkdir(parents=True, exist_ok=True)
            
            # Load existing context or create new
            context_file = rlm_dir / "context.json"
            if context_file.exists():
                try:
                    with open(context_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    messages = data.get("messages", [])
                    # Decrypt if needed
                    if data.get("encrypted", False) and self.rlm_password:
                        decrypted_messages = []
                        for msg in messages:
                            try:
                                decrypted_messages.append({
                                    "role": msg.get("role"),
                                    "content": decrypt_data(msg.get("content", ""), self.rlm_password)
                                })
                            except Exception:
                                # Skip messages that can't be decrypted
                                pass
                        self.rlm_context_store = decrypted_messages
                    else:
                        self.rlm_context_store = messages
                except Exception:
                    self.rlm_context_store = []
            else:
                self.rlm_context_store = []
            
            # Password validation for encrypted chats
            # Only validate if .encrypted exists (for loading existing encrypted chats)
            # New chats without passwords won't have .encrypted file, so validation is skipped
            encrypted_file = rlm_dir / ".encrypted"
            
            if encrypted_file.exists():
                # Validate password if .encrypted exists (means it's an encrypted chat)
                self.check_rlm_password(name, self.rlm_password)
                
                # Create verify.bin if it doesn't exist yet
                verify_file = rlm_dir / "verify.bin"
                if not verify_file.exists() and self.rlm_password:
                    try:
                        enc_v = encrypt_data("verification_string", self.rlm_password)
                        with open(verify_file, "w") as f:
                            f.write(enc_v)
                    except Exception:
                        pass
            
            self.rlm_collection_name = name
        except Exception as e:
            raise e
    
    def close_rlm_context(self):
        """Safely close and save the current RLM context store."""
        if self.rlm_context_store is not None:
            try:
                self.save_rlm_context()
            except Exception:
                pass
            self.rlm_context_store = None
        self.rlm_collection_name = None
    
    def save_rlm_context(self):
        """Save current RLM context to disk."""
        if not self.rlm_collection_name or self.rlm_context_store is None:
            return
        
        rlm_dir = Path(__file__).parent / "rlmcontexts" / self.rlm_collection_name
        rlm_dir.mkdir(parents=True, exist_ok=True)
        context_file = rlm_dir / "context.json"
        
        # Check if this chat should be encrypted (has .encrypted marker file)
        encrypted_file = rlm_dir / ".encrypted"
        should_encrypt = encrypted_file.exists()
        
        # Encrypt messages if .encrypted marker exists
        # We check for .encrypted file as the source of truth for whether encryption should be used
        messages_to_save = self.rlm_context_store
        is_encrypted = False
        if should_encrypt:
            # Get password from reactive attribute or backup
            password_to_use = getattr(self, 'rlm_password', None) or getattr(self, '_rlm_password_backup', None)
            
            # If .encrypted exists, we must have a password (it was set during creation/load)
            if not password_to_use:
                self.notify("RLM encryption error: Password not available for encrypted chat.", severity="error")
                return
            
            # Encrypt all messages
            try:
                from utils import encrypt_data
                encrypted_messages = []
                for msg in messages_to_save:
                    encrypted_messages.append({
                        "role": msg.get("role"),
                        "content": encrypt_data(msg.get("content", ""), password_to_use)
                    })
                messages_to_save = encrypted_messages
                is_encrypted = True
            except Exception as e:
                self.notify(f"RLM encryption failed: {e}", severity="error")
                return
        
        data = {
            "messages": messages_to_save,
            "encrypted": is_encrypted,
            "message_count": len(messages_to_save)
        }
        
        try:
            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.notify(f"Failed to save RLM context: {e}", severity="error")
    
    def add_to_rlm_context(self, messages: list):
        """Add messages to RLM context store."""
        if self.rlm_context_store is None:
            self.rlm_context_store = []
        
        # Append new messages
        self.rlm_context_store.extend(messages)
        
        # Save after every message exchange (user + assistant = 2 messages)
        # This ensures RLM context is constantly updated and available for queries
        # RLM needs frequent saves to work properly - the context should be available
        # for recursive queries, not just at the end of the chat
        try:
            self.save_rlm_context()
        except Exception:
            pass
    
    def query_rlm_context(self, user_query: str, max_chunks: int = 5, chunk_size: int = 10):
        """
        Query RLM context store recursively using LLM-generated search queries.
        Uses prewritten Python functions to safely execute search strategies.
        Implements MIT RLM approach: model queries its own context recursively.
        """
        if not self.rlm_context_store or len(self.rlm_context_store) == 0:
            return []
        
        if not self.llm:
            return []
        
        try:
            # Step 1: Have LLM generate search query/strategy (not code, just a query)
            search_prompt = f"""Given this user query: "{user_query}"

I need to search through conversation history ({len(self.rlm_context_store)} messages) to find relevant context.

Generate a search query that would help find relevant messages. Consider:
- Key topics or themes
- Important keywords or phrases
- What type of information is needed

Return ONLY a concise search query (1-2 sentences), no explanations."""

            strategy_messages = [
                {"role": "system", "content": "You are a search query generator. Return only the search query text."},
                {"role": "user", "content": search_prompt}
            ]
            
            strategy_response = self.llm.create_chat_completion(
                messages=strategy_messages,
                temperature=0.3,
                max_tokens=100
            )
            
            search_query = strategy_response["choices"][0]["message"]["content"].strip()
            
            # Step 2: Use prewritten Python functions to search
            results = self._search_rlm_store(search_query, user_query, max_chunks * chunk_size)
            
            return results
            
        except Exception as e:
            # Fallback on error
            return self.rlm_context_store[-20:] if len(self.rlm_context_store) > 20 else self.rlm_context_store
    
    def _search_rlm_store(self, search_query: str, original_query: str, max_results: int = 50):
        """
        Prewritten Python function to search RLM context store.
        Uses multiple search strategies: keyword matching, semantic similarity, and temporal relevance.
        """
        if not self.rlm_context_store:
            return []
        
        results = []
        search_query_lower = search_query.lower()
        original_query_lower = original_query.lower()
        
        # Extract keywords from both queries
        all_keywords = set(search_query_lower.split() + original_query_lower.split())
        # Filter out common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "was", "are", "were"}
        keywords = [kw for kw in all_keywords if kw not in stop_words and len(kw) > 2]
        
        # Strategy 1: Keyword matching with scoring
        keyword_matches = []
        for i, msg in enumerate(self.rlm_context_store):
            content = msg.get("content", "").lower()
            role = msg.get("role", "")
            
            # Count keyword matches
            match_count = sum(1 for kw in keywords if kw in content)
            if match_count > 0:
                # Score: keyword matches + recency bonus
                score = match_count * 10
                # Recent messages get bonus
                recency_bonus = max(0, (len(self.rlm_context_store) - i) / len(self.rlm_context_store) * 5)
                score += recency_bonus
                
                keyword_matches.append((score, i, msg))
        
        # Sort by score
        keyword_matches.sort(reverse=True, key=lambda x: x[0])
        results.extend([msg for _, _, msg in keyword_matches[:max_results // 2]])
        
        # Strategy 2: Semantic similarity (if embeddings available)
        if hasattr(self, "get_embedding"):
            try:
                query_emb = self.get_embedding(search_query, task="query")
                if query_emb:
                    semantic_matches = []
                    
                    # Sample messages for semantic search (don't search all to save time)
                    sample_size = min(100, len(self.rlm_context_store))
                    # Sample from recent, middle, and old sections
                    indices_to_check = set()
                    if len(self.rlm_context_store) > 0:
                        # Recent
                        indices_to_check.update(range(max(0, len(self.rlm_context_store) - 30), len(self.rlm_context_store)))
                        # Middle
                        mid_start = len(self.rlm_context_store) // 2
                        indices_to_check.update(range(mid_start, min(mid_start + 20, len(self.rlm_context_store))))
                        # Old (if large enough)
                        if len(self.rlm_context_store) > 50:
                            indices_to_check.update(range(0, min(20, len(self.rlm_context_store))))
                    
                    for i in indices_to_check:
                        if i < len(self.rlm_context_store):
                            msg = self.rlm_context_store[i]
                            content = msg.get("content", "")
                            if not content or len(content) < 10:
                                continue
                            
                            try:
                                msg_emb = self.get_embedding(content[:500], task="document")  # Limit length
                                if msg_emb:
                                    # Cosine similarity (manual calculation without numpy)
                                    dot_product = sum(a * b for a, b in zip(query_emb, msg_emb))
                                    norm_a = sum(a * a for a in query_emb) ** 0.5
                                    norm_b = sum(b * b for b in msg_emb) ** 0.5
                                    similarity = dot_product / (norm_a * norm_b + 1e-8)
                                    
                                    # Add recency bonus
                                    recency = (len(self.rlm_context_store) - i) / len(self.rlm_context_store)
                                    final_score = similarity * 0.7 + recency * 0.3
                                    
                                    semantic_matches.append((final_score, i, msg))
                            except Exception:
                                continue
                    
                    # Sort by similarity score
                    semantic_matches.sort(reverse=True, key=lambda x: x[0])
                    results.extend([msg for _, _, msg in semantic_matches[:max_results // 2]])
            except Exception:
                pass
        
        # Strategy 3: Always include some recent messages (temporal relevance)
        recent_count = min(10, len(self.rlm_context_store))
        recent_messages = self.rlm_context_store[-recent_count:]
        results.extend(recent_messages)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for msg in results:
            # Create a unique identifier for the message
            msg_id = (msg.get("role", ""), msg.get("content", "")[:100])  # Use role + content prefix
            if msg_id not in seen:
                seen.add(msg_id)
                unique_results.append(msg)
        
        # Limit to max_results
        return unique_results[:max_results]
