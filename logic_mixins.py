import time
import gc
import asyncio
import threading
import uuid
import json
from pathlib import Path
from textual import work
from textual.widgets import Select

# Imports for functional logic
from ai_engine import (
    load_model_cache, save_model_cache, get_cache_key, 
    count_tokens_in_messages, prune_messages_if_needed,
    get_models
)
from character_manager import create_initial_messages
from utils import DOWNLOAD_AVAILABLE, save_settings, load_settings, get_style_prompt
from widgets import MessageWidget

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
        # Try to acquire the lock with a timeout to prevent deadlocks
        if not _inference_lock.acquire(timeout=5.0):
            self.call_from_thread(self.notify, "Another inference is still running. Please wait.", severity="warning")
            self.call_from_thread(setattr, self, "is_loading", False)
            return
        
        try:
            if not self.llm:
                self.call_from_thread(self.notify, "Model not loaded! Load a model from the sidebar first.", severity="error")
                self.call_from_thread(setattr, self, "is_loading", False)
                return

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
                from llama_cpp import Llama  # Local import to avoid top-level issues if any
                
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
                token_count = 0
                peak_tps = 0.0
                
                was_cancelled = False
                for output in stream:
                    if self.is_loading == False: # Cancelled
                        was_cancelled = True
                        break
                        
                    text_chunk = output["choices"][0].get("delta", {}).get("content", "")
                    if not text_chunk:
                        continue
                    
                    assistant_content += text_chunk
                    
                    if assistant_widget is None:
                        try:
                            assistant_widget = self.call_from_thread(self.sync_add_assistant_widget, assistant_content)
                        except Exception:
                            was_cancelled = True
                            break
                    else:
                        try:
                            self.call_from_thread(self.sync_update_assistant_widget, assistant_widget, assistant_content)
                        except Exception:
                            was_cancelled = True
                            break
                    
                    # Stats
                    chunk_tokens = self.llm.tokenize(text_chunk.encode("utf-8"), add_bos=False, special=False)
                    token_count += len(chunk_tokens)
                    elapsed = time.time() - start_time
                    tps = token_count / elapsed if elapsed > 0 else 0
                    peak_tps = max(peak_tps, tps)
                    
                    total_tokens = prompt_tokens + token_count
                    ctx_pct = (total_tokens / self.context_size) * 100
                    self.call_from_thread(setattr, self, "status_text", f"TPS: {tps:.1f} | Peak: {peak_tps:.1f} | Context: {ctx_pct:.1f}% | Tokens: {token_count}")

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

    @work(exclusive=True, thread=True)
    def load_model_task(self, model_path, context_size, requested_gpu_layers):
        self.status_text = "Loading model..."
        
        if requested_gpu_layers == 0:
            layers_to_try = [0]
            self.call_from_thread(self.notify, "CPU Only selected, bypassing GPU cache.", severity="information")
        else:
            cache = load_model_cache()
            cache_key = get_cache_key(model_path, context_size)
            
            cached_layers = None
            if cache_key in cache:
                cached_layers = cache[cache_key].get("gpu_layers")
                self.call_from_thread(self.notify, f"Found cached GPU layer count: {cached_layers}", severity="information")
            
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
        
        llm = None
        actual_layers = 0
        from llama_cpp import Llama

        for layers in layers_to_try:
            try:
                layer_display = "all" if layers == -1 else str(layers)
                self.status_text = f"Trying {layer_display} GPU layers..."
                self.call_from_thread(self.notify, f"Trying {layer_display} GPU layers...", severity="information")
                llm = Llama(
                    model_path=model_path,
                    n_ctx=context_size,
                    n_gpu_layers=layers,
                    verbose=False
                )
                actual_layers = layers
                cache = load_model_cache()
                cache[cache_key] = {"gpu_layers": layers, "model_path": model_path, "context_size": context_size}
                save_model_cache(cache)
                self.call_from_thread(self.notify, f"✓ Successfully loaded with {layer_display} GPU layers!", severity="success")
                break
            except Exception:
                continue
        
        if llm:
            self.llm = llm
            self.context_size = context_size
            self.gpu_layers = actual_layers
            self.call_from_thread(self.notify, f"Model loaded successfully with {actual_layers} layers!")
            self.call_from_thread(self.enable_character_list)
            model_name = Path(model_path).stem
            self.status_text = f"{model_name} Ready"
        else:
            self.call_from_thread(self.notify, "Failed to load model!", severity="error")
            self.status_text = "Load Failed"

        # Setting this False triggers update_ui_state via the reactive watcher.
        # It must happen AFTER self.llm is set.
        self.call_from_thread(setattr, self, "is_model_loading", False)
        
        if self.llm:
            self.call_from_thread(self.focus_chat_input)

    @work(exclusive=True, thread=True)
    def download_default_model(self):
        if not DOWNLOAD_AVAILABLE:
            self.call_from_thread(self.notify, "requests and tqdm required for download!", severity="error")
            return

        self.call_from_thread(setattr, self, "is_downloading", True)
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Default LLM
        llm_url = "https://huggingface.co/mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF/resolve/main/MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_S.gguf?download=true"
        llm_path = models_dir / "MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_S.gguf"
        
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
    
    def action_toggle_sidebar(self) -> None:
        """Toggle both sidebars simultaneously."""
        sidebar_left = self.query_one("#sidebar")
        sidebar_right = self.query_one("#right-sidebar")
        new_state = not sidebar_left.has_class("-visible")
        sidebar_left.set_class(new_state, "-visible")
        sidebar_right.set_class(new_state, "-visible")

    async def action_stop_generation(self) -> None:
        """Gracefully stop the AI by setting the flag and waiting for the worker to exit."""
        if self.is_loading or (hasattr(self, "_inference_worker") and self._inference_worker):
            self.is_loading = False
            # Wait gracefully for the worker thread to catch the is_loading=False flag and exit its finally block
            max_waits = 40  # Increased from 20 to give more time for lock release
            while (hasattr(self, "_inference_worker") and self._inference_worker) and max_waits > 0:
                await asyncio.sleep(0.05)
                max_waits -= 1
            
            # If still stuck after graceful wait, then and only then attempt a cancel
            if hasattr(self, "_inference_worker") and self._inference_worker:
                try:
                    self._inference_worker.cancel()
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
                self._inference_worker = None
            
            # Extra delay to ensure the lock is fully released
            await asyncio.sleep(0.15)
                
            self.status_text = "Stopped"
            self.notify("Generation stopped.")

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
        # 1. Stop the AI gracefully (same method as Clear/Wipe All)
        await self.action_stop_generation()
        
        # 2. Safety gap for CUDA to settle
        await asyncio.sleep(0.2)
        
        # 3. Clear UI state
        try:
            self.query_one("#chat-input").value = ""
        except Exception:
            pass

        # 4. Reset messages
        if self.current_character:
            self.messages = create_initial_messages(self.current_character, self.user_name)
        else:
            self.messages = [{"role": "system", "content": ""}]
        
        # 5. Clear chat window
        self.query_one("#chat-scroll").query("*").remove()
        
        # 6. Apply style and print instructions
        if hasattr(self, "update_system_prompt_style"):
            # Suppress info message if restarting with a character card to keep it clean
            await self.update_system_prompt_style(self.style, suppress_info=bool(self.current_character))
        # 6. Restart the inference
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
        if self.is_loading:
            await self.action_stop_generation()

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
        await self.action_stop_generation()
        
        self.current_character = None
        self.first_user_message = None
        self.messages = [{"role": "system", "content": ""}]
        
        self.query_one("#chat-scroll").query("*").remove()
        
        if hasattr(self, "update_system_prompt_style"):
            await self.update_system_prompt_style(self.style)
            
        self.notify("Chat wiped clean.")

    async def action_continue_chat(self) -> None:
        if not self.is_loading and self.llm:
            user_text = "continue"
            await self.add_message("user", user_text)
            self.is_loading = True
            self._inference_worker = self.run_inference(user_text)

    async def action_regenerate(self) -> None:
        """Regenerate the last AI reply by removing it and re-running inference."""
        was_loading = self.is_loading
        
        # Stop generation if currently generating
        if self.is_loading:
            await self.action_stop_generation()
            # Wait a bit for the stop to complete
            await asyncio.sleep(0.1)
        
        if not self.llm:
            self.notify("No model loaded!", severity="warning")
            return
        
        if len(self.messages) <= 1:
            self.notify("Nothing to regenerate.", severity="warning")
            return
        
        # Find the user message that prompted the last assistant reply
        user_text = None
        
        # If we were loading, stop generation may have added a partial assistant message
        # to self.messages, so we need to remove it from both messages and UI
        if was_loading:
            # Remove any partial assistant message from messages if present
            if self.messages and self.messages[-1]["role"] == "assistant":
                self.messages.pop()
            
            # Find the last user message in messages
            for i in range(len(self.messages) - 1, -1, -1):
                if self.messages[i]["role"] == "user":
                    user_text = self.messages[i]["content"]
                    break
            
            # Remove any partial assistant widget from UI
            try:
                chat_scroll = self.query_one("#chat-scroll")
                widgets = [w for w in chat_scroll.children if isinstance(w, MessageWidget) and not w.is_info]
                if widgets and widgets[-1].role == "assistant":
                    widgets[-1].remove()
            except Exception:
                pass
        else:
            # Not loading - check if last message is assistant
            if self.messages[-1]["role"] != "assistant":
                self.notify("Last message is not from AI. Nothing to regenerate.", severity="warning")
                return
            
            # Find the user message that prompted this assistant reply
            for i in range(len(self.messages) - 1, -1, -1):
                if self.messages[i]["role"] == "user":
                    user_text = self.messages[i]["content"]
                    break
            
            # Remove the last assistant message from messages
            self.messages.pop()
            
            # Remove the last assistant message widget from UI
            try:
                chat_scroll = self.query_one("#chat-scroll")
                widgets = [w for w in chat_scroll.children if isinstance(w, MessageWidget) and not w.is_info]
                if widgets and widgets[-1].role == "assistant":
                    widgets[-1].remove()
            except Exception:
                pass
        
        if not user_text:
            self.notify("Could not find user message to regenerate from.", severity="warning")
            return
        
        # Re-run inference with the same user message
        self.is_loading = True
        self._inference_worker = self.run_inference(user_text)
        self.notify("Regenerating last reply...")

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
            
            # Try to get collection info to check if it exists and what dimension it uses
            try:
                collection_info = self.qdrant_instance.get_collection("chat_memory")
                # Collection exists, we're good to go
                return
            except Exception:
                # Collection doesn't exist, need to create it
                pass
            
            # Default dimension for nomic models (will be verified on first embedding)
            dim = 768
            
            try:
                self.qdrant_instance.create_collection(
                    collection_name="chat_memory",
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
                )
            except Exception as e:
                err_msg = str(e).lower()
                if "already exists" not in err_msg:
                    self.notify(f"Database initialization error: {e}", severity="error")
        except Exception as e:
            self.notify(f"Failed to initialize vector database: {e}", severity="error")
            
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
        if not self.embed_llm:
            embed_model_path = Path(__file__).parent / "models" / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
            if not embed_model_path.exists():
                self.notify("Embedding model not found! Download it first.", severity="error")
                return None
            
            try:
                from llama_cpp import Llama
                self.embed_llm = Llama(
                    model_path=str(embed_model_path),
                    embedding=True,
                    n_ctx=2048,
                    verbose=False,
                    n_gpu_layers=0 # Force CPU
                )
            except Exception as e:
                self.notify(f"Failed to load embedding model: {e}", severity="error")
                return None
        
        # Nomic 1.5 specific instructions
        prefix = "search_document: " if task == "document" else "search_query: "
        prefixed_text = prefix + text
            
        try:
            emb = self.embed_llm.create_embedding(prefixed_text)
            return emb['data'][0]['embedding']
        except Exception as e:
            self.notify(f"Embedding error: {e}", severity="error")
            return None

    def retrieve_similar_context(self, user_text: str, k=3):
        if not self.qdrant_instance:
            return []
            
        emb = self.get_embedding(user_text, task="query")
        if not emb:
            return []
            
        try:
            # Use the new query() API for qdrant-client v1.16+
            from qdrant_client.models import QueryRequest
            
            results = self.qdrant_instance.query_points(
                collection_name="chat_memory",
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
                        from utils import decrypt_data
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
                from utils import encrypt_data
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
            self.qdrant_instance.upsert(collection_name="chat_memory", points=[point])
        except Exception as e:
            self.notify(f"Failed to save vector entry: {e}", severity="error")
