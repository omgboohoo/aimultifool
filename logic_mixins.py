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
from llm_subprocess_client import SubprocessLlama, SubprocessEmbedder

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
                        # Windows (subprocess): close generator to drain remaining deltas and keep JSONL protocol aligned
                        # Linux (direct llama_cpp): closing is optional but harmless
                        try:
                            if hasattr(stream, "close"):
                                stream.close()
                        except Exception:
                            pass
                        break
                    
                    # Handle None yields from timeout-based reading (Windows subprocess only - allows interruption checks)
                    if output is None:
                        # This is a timeout yield - check cancellation and continue
                        if self.is_loading == False:
                            was_cancelled = True
                            try:
                                if hasattr(stream, "close"):
                                    stream.close()
                            except Exception:
                                pass
                            break
                        continue
                        
                    text_chunk = output["choices"][0].get("delta", {}).get("content", "")
                    if not text_chunk:
                        continue
                    
                    assistant_content += text_chunk
                    
                    # Stats calculation (internal only, not UI yet)
                    if isinstance(self.llm, SubprocessLlama):
                        token_count += max(1, len(text_chunk) // 4) if text_chunk else 0
                    else:
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

    def load_model_task(self, model_path, context_size, requested_gpu_layers, needs_cleanup=False, old_llm=None):
        # Unified fix: Manual threading completely bypassing Textual's @work decorator
        # Use a queue to communicate back to the main thread
        # ALL blocking operations (including backend cleanup) happen in the thread
        
        if requested_gpu_layers == 0:
            layers_to_try = [0]
        else:
            cache = load_model_cache()
            cache_key = get_cache_key(model_path, context_size)
            
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
        
        # Ensure model_path is a string (Windows path handling)
        model_path_str = str(model_path) if model_path else None
        if not model_path_str:
            self.is_model_loading = False
            return

        # Create a queue for thread communication
        result_queue = Queue()
        
        # Define the blocking function to run in a manual thread
        def _load_llama_thread():
            nonlocal old_llm
            llm = None
            actual_layers = 0
            
            try:
                # Platform-specific model loading:
                # - Windows: Use subprocess to avoid GIL-related UI freezes
                # - Linux: Use direct llama_cpp (no subprocess/JSONL complexity needed)
                
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
                
                if sys.platform == "win32":
                    # Windows: Use subprocess to avoid GIL issues
                    client = SubprocessLlama(
                        python_exe=sys.executable,
                        worker_path=str(Path(__file__).parent / "llm_subprocess_worker.py"),
                    )
                    for layers in layers_to_try:
                        try:
                            self.call_from_thread(setattr, self, "status_text", f"Loading (GPU Layers: {layers})...")
                            # If model load hangs or fails, timeout and restart subprocess, then try next option.
                            client.load(
                                model_path=model_path_str,
                                n_ctx=int(context_size),
                                n_gpu_layers=int(layers),
                                verbose=False,
                                timeout_s=120.0,
                            )
                            llm = client
                            actual_layers = int(layers)
                            
                            # Cache the successful result
                            cache = load_model_cache()
                            cache[cache_key] = {"gpu_layers": layers, "model_path": model_path_str, "context_size": int(context_size)}
                            save_model_cache(cache)
                            break
                        except Exception as e:
                            last_err = e
                            try:
                                client.restart()
                            except Exception:
                                pass
                            continue
                else:
                    # Linux: Use direct llama_cpp (simpler, no JSONL protocol needed)
                    import llama_cpp
                    for layers in layers_to_try:
                        try:
                            self.call_from_thread(setattr, self, "status_text", f"Loading (GPU Layers: {layers})...")
                            llm = llama_cpp.Llama(
                                model_path=model_path_str,
                                n_ctx=int(context_size),
                                n_gpu_layers=int(layers),
                                verbose=False,
                            )
                            actual_layers = int(layers)
                            
                            # Cache the successful result
                            cache = load_model_cache()
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
        # Unified: Use manual threading, NOT Textual's @work decorator
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
                    self.query_one("#chat-input").value = last_user_content
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
            "temp": self.temp,
            "topp": self.topp,
            "topk": self.topk,
            "repeat": self.repeat,
            "minp": self.minp,
            "style": self.style
        }
        save_settings(settings)

class VectorMixin:
    """Mixin for handling Vector DB (RAG) operations."""
    qdrant_instance = None
    embed_llm = None
    vector_password = None
    vector_collection_name = "chat_memory"
    _embedder = None

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

    def get_embedding(self, text: str, task: str = "document"):
        """Get embedding for text. task can be 'document' or 'query' for Nomic 1.5 prefixes."""
        try:
            embed_model_path = Path(__file__).parent / "models" / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
            if not embed_model_path.exists():
                self.call_from_thread(self.notify, "Embedding model not found! Download it first.", severity="error")
                return None
            
            if sys.platform == "win32":
                # Windows: Use subprocess to avoid blocking
                if not hasattr(self, "_embedder") or self._embedder is None:
                    self._embedder = SubprocessEmbedder(
                        python_exe=sys.executable,
                        worker_path=str(Path(__file__).parent / "llm_subprocess_worker.py"),
                    )
                    self._embedder.load(model_path=str(embed_model_path), n_ctx=2048, timeout_s=120.0)
                emb = self._embedder.embed(text, task=task, timeout_s=30.0)
            else:
                # Linux: Use direct llama_cpp (simpler, no subprocess needed)
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
