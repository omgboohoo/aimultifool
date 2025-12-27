import time
import gc
import asyncio
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

class InferenceMixin:
    """Mixin for handling AI inference and model loading tasks."""
    
    @work(exclusive=True, thread=True)
    def run_inference(self, user_text: str):
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
                
                total_tokens = prompt_tokens + token_count
                ctx_pct = (total_tokens / self.context_size) * 100
                self.call_from_thread(setattr, self, "status_text", f"TPS: {tps:.1f} | Context: {ctx_pct:.1f}% | Tokens: {token_count}")

            if assistant_content:
                try:
                    messages_to_use.append({"role": "assistant", "content": assistant_content})
                    messages_to_use = prune_messages_if_needed(self.llm, messages_to_use, self.context_size)
                    self.call_from_thread(self._update_messages_safely, messages_to_use)
                    
                    final_tokens = count_tokens_in_messages(self.llm, messages_to_use)
                    final_pct = (final_tokens / self.context_size) * 100
                    
                    self.call_from_thread(setattr, self, "status_text", f"{'Stopped' if was_cancelled else 'Finished'}. {token_count} tokens generated. Context: {final_pct:.1f}%")
                except Exception:
                    pass
            
        except Exception as e:
            self.call_from_thread(self.notify, f"Error during inference: {e}", severity="error")
        finally:
            self.call_from_thread(setattr, self, "is_loading", False)
            self._inference_worker = None

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
            self.status_text = "Model Ready"
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
        url = "https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf"
        file_path = models_dir / "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
        
        try:
            self.status_text = "Downloading default model..."
            import requests
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size_str = response.headers.get('content-length')
            total_size = int(total_size_str) if total_size_str else None
            
            downloaded = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size and total_size > 0:
                            pct = (downloaded / total_size) * 100
                            self.status_text = f"Downloading: {pct:.1f}% ({downloaded / 1024 / 1024:.1f} MB)"
                        else:
                            self.status_text = f"Downloading: {downloaded / 1024 / 1024:.1f} MB"
            
            self.call_from_thread(self.notify, "Model downloaded successfully!")
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
            max_waits = 20
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
                
            self.status_text = "Stopped"
            self.notify("Generation stopped.")

    def action_clear_history(self) -> None:
        if self.current_character:
            self.messages = create_initial_messages(self.current_character, self.user_name)
        else:
            style = self.query_one("#select-style").value
            content = get_style_prompt(style)
            self.messages = [{"role": "system", "content": content}]
        
        self.query_one("#chat-scroll").remove_children()
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
        self.query_one("#chat-scroll").remove_children()
        
        # 6. Apply style and print instructions
        if hasattr(self, "update_system_prompt_style"):
            await self.update_system_prompt_style(self.style)
        # 6. Restart the inference
        if self.current_character:
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

        chat_scroll = self.query_one("#chat-scroll")
        widgets = list(chat_scroll.children)
        
        if self.messages[-1]["role"] == "assistant":
            self.messages.pop()
            if widgets:
                widgets.pop().remove()
        
        if len(self.messages) > 1 and self.messages[-1]["role"] == "user":
            user_msg = self.messages.pop()
            if widgets:
                widgets.pop().remove()
            if self.first_user_message == user_msg["content"]:
                self.first_user_message = None

        self.notify("Rewound last interaction.")
        self.focus_chat_input()

    async def action_wipe_all(self) -> None:
        await self.action_stop_generation()
        
        self.current_character = None
        self.first_user_message = None
        self.messages = [{"role": "system", "content": ""}]
        
        self.query_one("#chat-scroll").remove_children()
        
        if hasattr(self, "update_system_prompt_style"):
            await self.update_system_prompt_style(self.style)
            
        self.notify("Chat wiped clean.")

    async def action_continue_chat(self) -> None:
        if not self.is_loading and self.llm:
            user_text = "continue"
            await self.add_message("user", user_text)
            self.is_loading = True
            self._inference_worker = self.run_inference(user_text)

    def save_user_settings(self):
        settings = {
            "user_name": self.user_name,
            "context_size": self.context_size,
            "selected_model": self.selected_model,
            "temp": self.temp,
            "topp": self.topp,
            "topk": self.topk,
            "repeat": self.repeat,
            "minp": self.minp
        }
        save_settings(settings)
