#!/usr/bin/env python3
"""
aiMultiFool - Textual TUI chat app with llama-cpp-python
"""

import os
import sys
import faulthandler

# Windows safety: enable fault handler to debug hangs
if sys.platform == "win32":
    faulthandler.enable()
    # Fix Windows event loop policy for threading compatibility
    # Windows 10+ defaults to ProactorEventLoop which doesn't work well with Textual's threading
    import asyncio
    if sys.version_info >= (3, 8):
        # Ensure we use SelectorEventLoop for better threading compatibility with Textual's @work decorator
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Disable Qdrant telemetry for total session privacy
os.environ["QDRANT__TELEMETRY_DISABLED"] = "true"

import gc
import asyncio
import re
import webbrowser
import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer, Container
from textual.widgets import Header, Input, Static, Label, Button, Select, ListView, ListItem, Collapsible
from textual.reactive import reactive
from textual.binding import Binding
import llama_cpp

# Modular Logic Mixins
from logic_mixins import InferenceMixin, ActionsMixin, VectorMixin
from ui_mixin import UIMixin

# Module Functions
from utils import _get_action_menu_data, load_settings, save_settings, DOWNLOAD_AVAILABLE, get_style_prompt, save_action_menu_data, encrypt_data
from character_manager import extract_chara_metadata, process_character_metadata, create_initial_messages, write_chara_metadata
from ai_engine import get_models
from widgets import MessageWidget, CharactersScreen, ParametersScreen, MiscScreen, ThemeScreen, ActionsManagerScreen, ModelScreen, ChatManagerScreen, VectorChatScreen

class AiMultiFoolApp(App, InferenceMixin, ActionsMixin, UIMixin, VectorMixin):
    """The main aiMultiFool application."""
    
    TITLE = "aiMultiFool v0.2.1"
    
    # Load CSS from external file (absolute path to prevent 'File Not Found' errors)
    CSS_PATH = str(Path(__file__).parent / "styles.tcss")

    BINDINGS = [
        Binding("ctrl+r", "reset_chat", "Restart from first prompt"),
        Binding("ctrl+z", "rewind", "Rewind last exchange"),
        Binding("ctrl+shift+w", "wipe_all", "Clear Chat"),
        Binding("ctrl+s", "stop_generation", "Stop AI"),
        Binding("ctrl+enter", "continue_chat", "Continue AI"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    llm = None
    root_path = Path(__file__).parent
    action_menu_data = []
    messages = reactive([])
    user_name = reactive("User")
    context_size = reactive(8192)
    gpu_layers = reactive(-1)
    style = reactive("descriptive")
    temp = reactive(0.8)
    topp = reactive(0.9)
    topk = reactive(40)
    repeat = reactive(1.0)
    minp = reactive(0.0)
    selected_model = reactive("")
    current_character = reactive(None)
    first_user_message = reactive(None)
    status_text = reactive("Ready")
    is_loading = reactive(False)
    is_model_loading = reactive(False)
    is_downloading = reactive(False)
    is_char_edit_mode = reactive(False)
    vector_chat_name = reactive(None)
    enable_vector_chat = reactive(False)
    force_ai_speak_first = reactive(True)
    _inference_worker = None
    _last_action_list = None
    _emotional_dynamics_content = reactive("")

    def notify(self, message: str, *, title: str = "", severity: str = "information", timeout: float = 1.5) -> None:
        """Override notify to halve the default display time."""
        super().notify(message, title=title, severity=severity, timeout=timeout)

    def compose(self) -> ComposeResult:
        # yield Header()  # Disabled default Textual header
        yield Horizontal(
            Button("File", id="btn-file", variant="default"),
            Button("Model", id="btn-model-settings", variant="default"),
            Button("Parameters", id="btn-parameters", variant="default"),
            Button("Cards", id="btn-cards", variant="default"),
            Button("Actions", id="btn-manage-actions", variant="default"),
            Button("Vector Chat", id="btn-vector-chat", variant="default"),
            Button("Theme", id="btn-theme", variant="default"),
            Button("About", id="btn-misc", variant="default"),
            id="top-menu-bar"
        )
        yield Horizontal(
            Vertical(
                ScrollableContainer(id="chat-scroll"),
                Container(
                    Input(placeholder="Type your message here...", id="chat-input"),
                    Horizontal(
                        Button("Stop", id="btn-stop", variant="default"),
                        Button("Continue", id="btn-continue", variant="default"),
                        Button("Regenerate", id="btn-regenerate", variant="default"),
                        Button("Rewind", id="btn-rewind", variant="default"),
                        Button("Restart", id="btn-restart", variant="default"),
                        Button("Clear", id="btn-clear-chat", variant="default"),
                        id="action-buttons"
                    ),
                    id="input-container"
                ),
                id="main-container"
            ),
            Vertical(
                Container(
                    Label("User Name", classes="sidebar-label"),
                    Input(placeholder="Name", id="input-username"),
                    classes="sidebar-setting-group username-group"
                ),
                Container(
                    Label("Style", classes="sidebar-label"),
                    Select([
                        ("Default", "Default"),
                        ("Action-Oriented", "action"),
                        ("Apocalyptic", "apocalyptic"),
                        ("Arcane", "arcane"),
                        ("Biblical", "biblical"),
                        ("Brutal", "brutal"),
                        ("Casual", "casual"),
                        ("Cerebral", "cerebral"),
                        ("Concise", "concise"),
                        ("Creative", "creative"),
                        ("Cyberpunk", "cyberpunk"),
                        ("Dark Fantasy", "dark_fantasy"),
                        ("Decadent", "decadent"),
                        ("Degenerate", "degenerate"),
                        ("Descriptive", "descriptive"),
                        ("Dramatic", "dramatic"),
                        ("Eldritch", "eldritch"),
                        ("Epic", "epic"),
                        ("Erotic", "erotic"),
                        ("Flowery", "flowery"),
                        ("Frenzied", "frenzied"),
                        ("Gritty", "gritty"),
                        ("Hardboiled", "hardboiled"),
                        ("Historical", "historical"),
                        ("Horror", "horror"),
                        ("Humorous", "humorous"),
                        ("Idiosyncratic", "idiosyncratic"),
                        ("Internalized", "internalized"),
                        ("Lovecraftian", "lovecraftian"),
                        ("Melancholic", "melancholic"),
                        ("Minimalist", "minimalist"),
                        ("Nihilistic", "nihilistic"),
                        ("Noir", "noir"),
                        ("Philosophical", "philosophical"),
                        ("Psycho Thriller", "psycho_thriller"),
                        ("Raw", "raw"),
                        ("Savage", "savage"),
                        ("Scientific", "scientific"),
                        ("Shakespearean", "shakespearean"),
                        ("Sinister", "sinister"),
                        ("Slang Heavy", "slang_heavy"),
                        ("Surreal", "surreal"),
                        ("Twisted", "twisted"),
                        ("Victorian", "victorian"),
                        ("Whimsical", "whimsical")
                    ], id="select-style", value="descriptive", allow_blank=False),
                    classes="sidebar-setting-group style-group"
                ),
                Horizontal(
                    Input(placeholder="Search actions...", id="input-action-search"),
                    Button("Clear", id="btn-clear-search", variant="default", disabled=True),
                    id="search-container"
                ),
                Vertical(id="action-sections"),
                Container(
                    Label("Emotion Dynamics", classes="sidebar-label"),
                    ScrollableContainer(
                        Static("", id="emotional-dynamics-content", classes="emotional-dynamics"),
                        id="emotional-dynamics-scroll"
                    ),
                    classes="sidebar-setting-group emotional-dynamics-group"
                ),
                id="right-sidebar"
            ),
            id="main-layout"
        )
        with Horizontal(id="status-bar"):
            yield Static("Ready", id="status-text")
            yield Static("aiMultiFool v0.2.1", id="status-version")

    async def on_mount(self) -> None:
        # Load persisted settings
        settings = load_settings()
        self.user_name = settings.get("user_name", "User")
        self.context_size = settings.get("context_size", 8192)
        self.gpu_layers = settings.get("gpu_layers", -1)
        self.style = settings.get("style", "descriptive")
        self.temp = settings.get("temp", 0.8)
        self.topp = settings.get("topp", 0.9)
        self.topk = settings.get("topk", 40)
        self.repeat = settings.get("repeat", 1.0)
        self.minp = settings.get("minp", 0.0)
        self.selected_model = settings.get("selected_model", "")
        self.theme = settings.get("theme", "textual-dark")
        self.speech_styling = settings.get("speech_styling", "highlight")
        self.force_ai_speak_first = settings.get("force_ai_speak_first", True)
        
        # Defer character list update until Cards screen is opened
        
        self.action_menu_data = _get_action_menu_data()
        self.populate_right_sidebar()
        
        # Apply UI values
        self.query_one("#input-username").value = self.user_name
        # self.query_one("#select-context").value = self.context_size
        # self.query_one("#select-gpu-layers").value = self.gpu_layers
        self.query_one("#select-style").value = self.style

        if self.selected_model:
            # We don't set the widget value here anymore as the modal handles it
            pass

        self.title = "aiMultiFool"
        # Sidebar is gone
        self.query_one("#right-sidebar").add_class("-visible")
        self.watch_is_loading(self.is_loading)
        self.watch_is_downloading(self.is_downloading)
        self.watch_is_model_loading(self.is_model_loading)
        
        # Re-apply Focus styling for inputs (sometimes gets lost in dynamic CSS loading?)
        # Actually it's handled by CSS, but good to ensure everything mounted.
        
        models = get_models()
        nomic_path = self.root_path / "models" / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
        if not models or not nomic_path.exists():
            self.notify("Setting up default models...", severity="information")
            self.download_default_model()
        
        new_content = get_style_prompt(self.style)
        self.messages = [{"role": "system", "content": new_content}]
        self.disable_character_list() # Start disabled
        self.show_footer = True
        
        self.push_screen(ModelScreen(), self.model_screen_callback)

    def watch_is_loading(self, is_loading: bool) -> None:
        """Called when is_loading (inference) changes."""
        # Allow typing while loading
        self.query_one("#chat-input").disabled = False
        self.query_one("#btn-stop").disabled = not is_loading
        
        # Sync visibility
        try:
            self.query_one("#btn-stop").display = is_loading
            self.query_one("#btn-continue").display = not is_loading
            # Regenerate button stays visible during generation so user can stop and regen
            self.query_one("#btn-regenerate").display = True
        except Exception:
            pass
        
        # Update action menu state when loading state changes
        # This disables action menu, top menus, regenerate, and rewind while AI is generating
        self.update_ui_state()

    def watch_is_downloading(self, is_downloading: bool) -> None:
        """Called when is_downloading changes."""
        self.update_ui_state()

    def watch_is_model_loading(self, is_model_loading: bool) -> None:
        """Called when is_model_loading changes."""
        self.update_ui_state()

        
    def watch_is_char_edit_mode(self, is_char_edit_mode: bool) -> None:
        """Called when is_char_edit_mode changes."""
        self.update_ui_state()

    def watch_enable_vector_chat(self, enable_vector_chat: bool) -> None:
        """Called when enable_vector_chat changes."""
        try:
            btn = self.query_one("#btn-vector-chat", Button)
            if enable_vector_chat:
                btn.add_class("vector-active")
            else:
                btn.remove_class("vector-active")
        except Exception:
            pass

    async def on_focus(self, event) -> None:
        if hasattr(self, 'show_footer'):
            self.show_footer = True

    def update_ui_state(self):
        """Disable or enable UI elements based on app state."""
        is_busy = self.is_model_loading or self.is_downloading
        # Also disable action menu while AI is actively generating
        is_ai_generating = self.is_loading
        
        # Query both the main app and the active screen to ensure modals are covered
        all_buttons = list(self.query(Button))
        if self.screen:
            all_buttons.extend(list(self.screen.query(Button)))

        for btn in all_buttons:
            if btn.id == "btn-load-model":
                btn.disabled = is_busy
                btn.loading = self.is_model_loading
                continue

            # Disable top menu buttons when AI is generating
            if btn.id in ["btn-file", "btn-misc", "btn-theme", "btn-cards", "btn-parameters", "btn-model-settings", "btn-manage-actions", "btn-vector-chat"]:
                btn.disabled = is_ai_generating
            elif btn.id in ["btn-continue", "btn-regenerate", "btn-rewind", "btn-restart", "btn-clear-chat"]:
                # Disable if busy OR if no model is loaded OR if AI is generating
                # Regenerate and rewind are always disabled while AI is speaking
                btn.disabled = is_busy or not self.llm or is_ai_generating
            elif btn.id == "btn-clear-search":
                # Only enabled if there is text in the search box
                try:
                    search_val = self.query_one("#input-action-search").value
                    btn.disabled = not bool(search_val.strip())
                except Exception:
                    btn.disabled = True
            else:
                btn.disabled = is_busy
            
        all_selects = list(self.query(Select))
        if self.screen:
            all_selects.extend(list(self.screen.query(Select)))
        for select in all_selects:
            select.disabled = is_busy
            
        all_inputs = list(self.query(Input))
        if self.screen:
            all_inputs.extend(list(self.screen.query(Input)))
        for inp in all_inputs:
            if inp.id == "chat-input":
                inp.disabled = is_busy or not self.llm
            elif inp.id == "input-username":
                # Disable username field while AI is generating
                inp.disabled = is_busy or is_ai_generating
            else:
                inp.disabled = is_busy
            
        try:
            # Check app and screen for these specific widgets
            for root in [self, self.screen]:
                chars = root.query("#list-characters")
                if chars:
                    chars.first().disabled = is_busy or (not self.llm and not self.is_char_edit_mode)
                
                edit_btn = root.query("#btn-char-edit-mode")
                if edit_btn:
                    edit_btn.first().disabled = is_busy
        except Exception:
            pass

        # Action lists and collapsibles on both
        # Disable action menu while AI is actively generating to prevent conflicts
        for root in [self, self.screen]:
            for lv in root.query(".action-list"):
                lv.disabled = is_busy or not self.llm or is_ai_generating
            for collapsible in root.query(Collapsible):
                collapsible.disabled = is_busy or is_ai_generating

    def update_model_list(self):
        """Update model list on the active ModelScreen if it's open."""
        models = get_models()
        
        # Check if ModelScreen is the current screen
        if isinstance(self.screen, ModelScreen):
            try:
                select_model = self.screen.query_one("#select-model", Select)
                options = [(m.name, str(m)) for m in models]
                select_model.set_options(options)
                
                # If nothing is selected or current selection is invalid, select the first one
                if options and (select_model.value == Select.BLANK or not any(opt[1] == select_model.value for opt in options)):
                    select_model.value = options[0][1]
            except Exception:
                pass


    def get_card_list(self):
        cards_dir = Path(__file__).parent / "cards"
        if not cards_dir.exists():
            cards_dir.mkdir(parents=True, exist_ok=True)
        return sorted(list(cards_dir.glob("*.png")))

    def update_character_list(self):
        cards = self.get_card_list()
        # Try to find the list-characters widget on the current screen
        lvs = self.query("#list-characters")
        if lvs:
            list_view = lvs.first()
            list_view.clear()
            for card in cards:
                list_view.append(ListItem(Label(card.name), name=str(card)))
    
    def enable_character_list(self):
        try:
            self.query_one("#list-characters").disabled = False
        except Exception:
            pass
        for lv in self.query(".action-list"):
            lv.disabled = False
    
    def disable_character_list(self):
        try:
            self.query_one("#list-characters").disabled = True
        except Exception:
            pass
        for lv in self.query(".action-list"):
            lv.disabled = True
    
    def focus_chat_input(self):
        try:
            self.query_one("#chat-input").focus()
        except Exception:
            pass

    def save_user_settings(self):
        settings = {
            "user_name": self.user_name,
            "context_size": self.context_size,
            "gpu_layers": self.gpu_layers,
            "style": self.style,
            "temp": self.temp,
            "topp": self.topp,
            "topk": self.topk,
            "repeat": self.repeat,
            "minp": self.minp,
            "selected_model": self.selected_model,
            "theme": self.theme,
            "speech_styling": self.speech_styling
        }
        save_settings(settings)

    def populate_right_sidebar(self, filter_text="", highlight_item_name=None):
        filter_text = filter_text.lower()
        right_sidebar = self.query_one("#right-sidebar", Vertical)
        action_sections = self.query_one("#action-sections", Vertical)
        
        # Clear existing sections
        action_sections.query("*").remove()
        
        right_sidebar.add_class("-visible")

        if not self.action_menu_data:
            return
            

        
        # Format and categorize data
        if isinstance(self.action_menu_data, list) and len(self.action_menu_data) > 0:
            first_item = self.action_menu_data[0]
            if isinstance(first_item, dict) and "sectionName" in first_item:
                flattened = []
                for section in self.action_menu_data:
                    section_name = section.get("sectionName", "")
                    items = section.get("items", [])
                    for item in items:
                        if item.get("name") != "-":
                            item["category"] = section_name
                            if section_name == "System Prompts":
                                item["isSystem"] = True
                            else:
                                item["isSystem"] = item.get("isSystem", False)
                            flattened.append(item)
                self.action_menu_data = flattened

        for item in self.action_menu_data:
            # Migration: if category is missing or 'Other', try to parse from name
            if ":" in item.get("name", "") and (item.get("category", "Other") == "Other"):
                parts = item["name"].split(":", 1)
                item["category"] = parts[0].strip()
                item["name"] = parts[1].strip()
            
            if "category" not in item:
                item["category"] = "Other"
            if "isSystem" not in item:
                item["isSystem"] = False

        # Sort all data: Category (A-Z) then Item Name (A-Z)
        self.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))

        # Group by category
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in self.action_menu_data:
            category = item.get("category", "Other")
            grouped[category].append(item)

        # Create collapsibles for each category
        for cat in sorted(grouped.keys()):
            items = grouped[cat]
            # Determine if this category contains any matching items
            list_items = []
            for item in items:
                item_name = item.get("name", "None")
                display_name = item_name
                prompt = item.get("prompt", "")
                
                # Filter logic
                if filter_text and filter_text not in item_name.lower() and filter_text not in prompt.lower():
                    continue
                
                is_system = item.get("isSystem", False)
                data_packed = f"{item_name}:::{prompt}:::{is_system}"
                # Create ListItem with tooltip showing the prompt on hover
                li = ListItem(Label(display_name), name=data_packed)
                if prompt:
                    max_len = 200
                    li.tooltip = prompt[:max_len] + "..." if len(prompt) > max_len else prompt
                list_items.append(li)
            
            if not list_items:
                continue

            list_view = ListView(*list_items, classes="action-list")
            list_view.can_focus = True 
            
            # Highlight logic (just to expand the category)
            is_highlighted_cat = False
            if highlight_item_name:
                for li in list_items:
                    if li.name.startswith(f"{highlight_item_name}:::"):
                        is_highlighted_cat = True
                        break

            # Collapse if no filter and not the highlighted category
            is_collapsed = not bool(filter_text) and not is_highlighted_cat
            collapsible = Collapsible(list_view, title=cat, collapsed=is_collapsed)
            action_sections.mount(collapsible)
            
            if is_highlighted_cat:
                self._last_action_list = list_view
            
        # Refresh UI state to disable items if no model is loaded
        self.update_ui_state()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Track which action list was last interacted with."""
        if event.list_view.has_class("action-list"):
            self._last_action_list = event.list_view

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        """Allow multiple sections to stay open during search."""
        # Only enforce single-open behavior if NOT searching
        search_val = self.query_one("#input-action-search").value
        if not search_val:
            for collapsible in self.query(Collapsible):
                if collapsible != event.collapsible:
                    collapsible.collapsed = True
        
        # Remove auto-highlight from the ListView when collapsible expands
        try:
            list_view = event.collapsible.query_one(ListView)
            if list_view:
                list_view.index = None
        except Exception:
            pass

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item:
            return

        try:
            if event.list_view.id == "list-characters":
                # Character loading is now handled by the Play button in CharactersScreen.
                # Selection here doesn't trigger AI, only highlights and loads metadata (handled in on_list_view_highlighted).
                pass
            elif event.list_view.has_class("action-list"):
                # Prevent action menu usage while AI is actively generating
                if self.is_loading:
                    self.notify("Please wait for AI to finish speaking before using actions.", severity="warning")
                    return
                
                data_packed = getattr(event.item, "name", "")
                if ":::" in data_packed:
                    parts = data_packed.split(":::", 2)
                    if len(parts) == 3:
                        item_name, prompt, is_system_str = parts
                        is_system = is_system_str == "True"
                        

                        section = "System Prompts" if is_system else "Actions"
                        await self.handle_menu_action(section, item_name, prompt)
                self.focus_chat_input()
        except Exception as e:
            self.notify(f"Selection error: {e}", severity="error")

    async def load_character_from_path(self, card_path, chara_json_obj=None):
        # Serialize with actions lock to prevent race conditions
        async with self._get_actions_lock():
            if self.is_loading:
                await self._stop_generation_unlocked()
            
            # Wait for cleanup to finish if it's in progress
            await self._wait_for_cleanup_if_needed()

            try:
                if chara_json_obj:
                    chara_json = json.dumps(chara_json_obj)
                else:
                    chara_json = extract_chara_metadata(card_path)
                
                if not chara_json:
                    self.notify("No metadata found in PNG!", severity="error")
                    return
                chara_obj, talk_prompt, depth_prompt = process_character_metadata(chara_json, self.user_name)
                if not chara_obj:
                    self.notify("Failed to process metadata!", severity="error")
                    return
                self.current_character = chara_obj
                self.messages = create_initial_messages(chara_obj, self.user_name)
                await self.update_system_prompt_style(self.style)
                self.query_one("#chat-scroll").query("*").remove()
                self.notify(f"Loaded character: {Path(card_path).name}")
                if self.llm and self.force_ai_speak_first:
                    # Final safety check before starting inference
                    if not await self._can_start_inference():
                        await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                        if not await self._can_start_inference():
                            self.notify("Please wait for current operation to finish.", severity="warning")
                            return
                    
                    if len(self.messages) > 1 and self.messages[-1]["role"] == "user":
                        self.messages[-1]["content"] = "continue"
                    else:
                        self.messages.append({"role": "user", "content": "continue"})
                    self.is_loading = True
                    self._inference_worker = self.run_inference("continue")
            except Exception as e:
                self.notify(f"Error loading character: {e}", severity="error")

    async def handle_menu_action(self, section_name: str, item_name: str, prompt: str):
        # Serialize with actions lock to prevent race conditions
        async with self._get_actions_lock():
            if self.is_loading:
                await self._stop_generation_unlocked()
            
            # Wait for cleanup to finish if it's in progress
            await self._wait_for_cleanup_if_needed()
            
            # Replace {{user}} with the user's name
            prompt = re.sub(r'\{\{user\}\}', self.user_name, prompt, flags=re.IGNORECASE)

            if section_name == "System Prompts":
                await self.set_system_prompt(prompt, item_name)
            else:
                # Final safety check before starting inference
                if not await self._can_start_inference():
                    await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                    if not await self._can_start_inference():
                        self.notify("Please wait for current operation to finish.", severity="warning")
                        return
                
                if not self.current_character and self.first_user_message is None:
                    self.first_user_message = prompt
                    
                self.notify(f"Action: {item_name}")
                await self.add_message("user", prompt)
                self.is_loading = True
                self._inference_worker = self.run_inference(prompt)

    async def set_system_prompt(self, prompt: str, name: str):
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = prompt
            self.notify(f"System prompt set to: {name}")
        else:
            self.messages = [{"role": "system", "content": prompt}, *self.messages]
            self.notify(f"System prompt added: {name}")
        
        # Check if chat window is empty (only system message exists)
        has_started = len(self.messages) > 1
        if not has_started:
            # If chat hasn't started, clear previous info messages 
            # to prevent multiple instruction blocks in an empty chat.
            self.query_one("#chat-scroll").query("*").remove()
        
        await self.add_info_message(f"[System Prompt: {name}]\n\n{prompt}")

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-style":
            self.style = event.value
            await self.update_system_prompt_style(event.value)
            self.save_user_settings()
        
        if len(self.screen_stack) <= 1: 
             self.focus_chat_input()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "input-username":
            self.user_name = event.value
            self.save_user_settings()
        elif event.input.id == "chat-input":
            if self.is_loading and event.value.strip():
                await self.action_stop_generation()
        elif event.input.id == "input-action-search":
            self.populate_right_sidebar(event.value)
            self.query_one("#btn-clear-search").disabled = not bool(event.value.strip())

    async def update_system_prompt_style(self, style: str, suppress_info: bool = False) -> None:
        if not self.messages: return
        has_started = len(self.messages) > 1
        
        # If a character is active and style is Default, we don't want the "Helpful Assistant" persona.
        # We only want the basic procedural constraints.
        if self.current_character and style.lower() == "default":
            style_instruction = "Do not reply on behalf of user."
        else:
            style_instruction = get_style_prompt(style)
        
        if self.current_character:
            # We must re-import here to avoid circular imports if any, 
            # and to safely re-generate the base prompt without style pollution.
            from character_manager import create_initial_messages
            temp_msgs = create_initial_messages(self.current_character, self.user_name)
            base_prompt = temp_msgs[0]["content"]
            new_content = f"{base_prompt}\n\n[Style Instruction: {style_instruction}]"
        else:
            new_content = style_instruction

        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = new_content
            if has_started and not suppress_info: 
                self.notify(f"Style updated: {style.capitalize()}")
            elif not has_started and not suppress_info:
                # If chat hasn't started, clear previous style info messages 
                # to prevent multiple instruction blocks in an empty chat.
                self.query_one("#chat-scroll").query("*").remove()

        if not suppress_info:
            await self.add_info_message(f"[Style: {style.capitalize()}]\n\n{new_content}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            # Serialize with actions lock to prevent race conditions
            async with self._get_actions_lock():
                # If currently loading OR if status is "Stopping..." (from typing while AI speaks), stop first
                if self.is_loading or getattr(self, "status_text", "") == "Stopping...":
                    await self._stop_generation_unlocked()
                
                # Wait for cleanup to finish if it's in progress
                await self._wait_for_cleanup_if_needed()
                
                # Ensure status is not stuck on "Stopping..."
                if getattr(self, "status_text", "") == "Stopping...":
                    # Wait a bit more for cleanup to complete
                    await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                    # Force status update if still stuck
                    if getattr(self, "status_text", "") == "Stopping...":
                        self.status_text = "Ready"
                
                # Final safety check before starting
                if not await self._can_start_inference():
                    # Still not ready, wait a bit more
                    await self._wait_for_cleanup_if_needed(max_wait_seconds=1.0)
                    if not await self._can_start_inference():
                        self.notify("Please wait for current operation to finish.", severity="warning")
                        self.status_text = "Ready"
                        return

                # Set flag to prevent rapid typing from starting multiple inferences
                if getattr(self, "_inference_starting", False):
                    # Another submission is already starting inference, ignore this one
                    return
                
                setattr(self, "_inference_starting", True)
                try:
                    user_text = event.value.strip() or "continue"
                    event.input.value = ""
                    if not self.current_character and self.first_user_message is None:
                        self.first_user_message = user_text
                    await self.add_message("user", user_text)
                    
                    # Set loading state and start inference
                    # Note: run_inference() will set status to "Thinking..." after acquiring lock
                    # If lock acquisition fails, it will reset is_loading and status
                    self.is_loading = True
                    self._inference_worker = self.run_inference(user_text)
                finally:
                    # Clear flag after a brief delay to allow inference to actually start
                    # This prevents rapid submissions from interfering
                    await asyncio.sleep(0.1)
                    setattr(self, "_inference_starting", False)

    def start_model_load(self, model_path, ctx, gpu):
        """Helper to safely start model loading from modals."""
        if not model_path:
            self.notify("Please select a model first!", severity="warning")
            return

        # Update app state and persist settings
        self.selected_model = str(model_path)
        self.context_size = int(ctx)
        self.gpu_layers = int(gpu)
        self.save_user_settings()

        # Set loading state and status BEFORE starting worker (Windows needs reactive updates on main thread)
        self.is_model_loading = True
        self.status_text = "Loading model..."
        
        # Store if we need to clean up existing model (do this in thread, not main thread)
        needs_cleanup = bool(self.llm)
        old_llm = None
        if needs_cleanup:
            self.disable_character_list()
            old_llm = self.llm
            self.llm = None  # Clear reference immediately
        
        # Start manual threading (completely bypasses Textual's @work decorator for Windows compatibility)
        # Pass cleanup flag so thread can handle it
        self.load_model_task(model_path, ctx, gpu, needs_cleanup=needs_cleanup, old_llm=old_llm if needs_cleanup else None)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-stop": await self.action_stop_generation()
        elif event.button.id == "btn-continue": await self.action_continue_chat()
        elif event.button.id == "btn-regenerate": await self.action_regenerate()
        # elif event.button.id == "btn-toggle-sidebar": self.action_toggle_sidebar() # Sidebar is gone
        elif event.button.id == "btn-model-settings":
             self.push_screen(ModelScreen(), self.model_screen_callback)
        elif event.button.id == "btn-restart": await self.action_reset_chat()
        elif event.button.id == "btn-rewind": await self.action_rewind()
        elif event.button.id == "btn-clear-chat": await self.action_wipe_all()
        elif event.button.id == "btn-manage-actions":
            self.push_screen(ActionsManagerScreen(), self.actions_mgmt_callback)
        elif event.button.id == "btn-cards":
            self.push_screen(CharactersScreen(), self.cards_screen_callback)
        elif event.button.id == "btn-parameters":
            self.push_screen(ParametersScreen())
        elif event.button.id == "btn-theme":
            self.push_screen(ThemeScreen())
        elif event.button.id == "btn-misc":
            self.push_screen(MiscScreen())
        elif event.button.id == "btn-file":
            self.push_screen(ChatManagerScreen(), self.chat_manager_callback)
        elif event.button.id == "btn-vector-chat":
            self.push_screen(VectorChatScreen(), self.vector_chat_callback)
        elif event.button.id == "btn-clear-search":
            search_input = self.query_one("#input-action-search", Input)
            search_input.value = ""
            # The on_input_changed will trigger the re-population
            search_input.focus()
        elif event.button.id == "btn-char-edit-mode":
            self.is_char_edit_mode = not self.is_char_edit_mode
            btn = self.query_one("#btn-char-edit-mode", Button)
            btn.label = "Exit Edit Mode" if self.is_char_edit_mode else "Enter Edit Mode"
            
            if self.is_char_edit_mode:
                self.notify("Character Edit Mode: Click a card to edit its metadata")
        
        # Only focus if not in a modal
        # Check current screen. If it is the App (Screen), then focus.
        if len(self.screen_stack) <= 1: 
             self.focus_chat_input()

    async def cards_screen_callback(self, result):
        if not result:
            return
        
        action = result.get("action")
        path = result.get("path")
        
        if action == "play":
            meta = result.get("meta")
            await self.load_character_from_path(path, chara_json_obj=meta)
        
    async def actions_mgmt_callback(self, result):
        # Always refresh sidebar after mgmt modal
        self.populate_right_sidebar()
        
        self.focus_chat_input()

    async def chat_manager_callback(self, result):
        if not result:
            return
        
        action = result.get("action")
        if action == "load":
            messages = result.get("messages")
            model_settings = result.get("model_settings")
            
            if messages:
                # Clear and repopulate chat scroll robustly
                await self.action_stop_generation()
                
                # Restore model settings if available
                if model_settings:
                    # Check if model or critical settings need to change
                    saved_model = model_settings.get("selected_model", "")
                    saved_context = model_settings.get("context_size", self.context_size)
                    saved_gpu_layers = model_settings.get("gpu_layers", self.gpu_layers)
                    
                    needs_reload = False
                    if saved_model and (
                        not self.llm or 
                        self.selected_model != saved_model or
                        self.context_size != saved_context or
                        self.gpu_layers != saved_gpu_layers
                    ):
                        needs_reload = True
                    
                    # Update all model settings
                    self.selected_model = saved_model if saved_model else self.selected_model
                    self.context_size = saved_context
                    self.gpu_layers = saved_gpu_layers
                    self.temp = model_settings.get("temp", self.temp)
                    self.topp = model_settings.get("topp", self.topp)
                    self.topk = model_settings.get("topk", self.topk)
                    self.repeat = model_settings.get("repeat", self.repeat)
                    self.minp = model_settings.get("minp", self.minp)
                    
                    self.save_user_settings()
                    
                    # Reload model if needed
                    if needs_reload and self.selected_model:
                        self.notify("Reloading model with saved settings...", severity="information")
                        self.is_model_loading = True
                        await asyncio.sleep(0.1)
                        self.start_model_load(self.selected_model, self.context_size, self.gpu_layers)
                        
                        # Wait for model loading to complete before allowing input
                        max_wait = 300  # 30 seconds max wait
                        wait_count = 0
                        while self.is_model_loading and wait_count < max_wait:
                            await asyncio.sleep(0.1)
                            wait_count += 1
                        
                        if not self.llm:
                            self.notify("Model failed to load. Please load a model manually.", severity="error")
                            return
                        
                        # Small safety delay to ensure CUDA is fully initialized
                        await asyncio.sleep(0.2)
                        
                        self.notify("Model loaded successfully. Chat restored.")
                    else:
                        self.notify("Chat loaded successfully. Model settings restored.")
                else:
                    self.notify("Chat loaded successfully. (No model settings found in saved chat)")
                
                # Only set messages and sync UI after model is ready
                self.messages = messages
                await self.full_sync_chat_ui()
                self.focus_chat_input()

    async def vector_chat_callback(self, result):
        if not result:
            return
        
        try:
            action = result.get("action")
            name = result.get("name")
            password = result.get("password")
            
            if action == "load" or action == "create":
                if not name:
                    self.notify("Error: No chat name provided.", severity="error")
                    return
                
                # Normalize password: empty strings should be None
                password = password.strip() if password else None
                    
                await self.action_stop_generation()
                self.vector_password = password
                
                if action == "create" and password:
                    # Create marker file if password provided for a new chat
                    vectors_dir = self.root_path / "vectors" / name
                    vectors_dir.mkdir(parents=True, exist_ok=True)
                    (vectors_dir / ".encrypted").touch()
                    
                    # Create password verification file
                    try:
                        verify_data = encrypt_data("verification_string", password)
                        with open(vectors_dir / "verify.bin", "w") as f:
                            f.write(verify_data)
                    except Exception:
                        pass
                
                # Initialize DB with error handling
                try:
                    self.initialize_vector_db(name)
                except Exception as e:
                    self.notify(f"Failed to initialize vector database: {e}", severity="error")
                    self.enable_vector_chat = False
                    self.vector_chat_name = None
                    self.vector_password = None
                    return
                
                # SUCCESS: Set active state only after successful initialization
                self.vector_chat_name = name
                self.enable_vector_chat = True
                
                self.query_one("#chat-scroll").query("*").remove()
                self.messages = [{"role": "system", "content": "Vector Chat enabled."}]
                enc_suffix = " (Encrypted)" if password else ""
                self.notify(f"Vector Chat '{name}'{enc_suffix} loaded.")
            elif action == "disable":
                await self.action_disable_vector_chat()
            
            self.save_user_settings()
        except Exception as e:
            self.notify(f"Vector chat error: {e}", severity="error")
            import traceback
            traceback.print_exc()

    async def action_disable_vector_chat(self):
        self.enable_vector_chat = False
        self.vector_chat_name = None
        self.vector_password = None
        self.close_vector_db()
        self.notify("Vector Chat disabled.")
        # Normal chat reset
        await self.action_wipe_all()
        self.save_user_settings()

    def get_character_names(self):
        """Extract character names from current character and user name."""
        names = []
        if self.current_character:
            char_name = self.current_character.get("name") or self.current_character.get("data", {}).get("name")
            if char_name:
                names.append(char_name)
        if self.user_name:
            names.append(self.user_name)
        return names if names else ["Character", "User"]
    
    def analyze_emotions(self, assistant_content: str):
        """Analyze emotions of each character after AI reply. Called from worker thread."""
        if not self.llm or not assistant_content:
            return
        
        try:
            # Get character names and messages from main thread
            character_names = self.call_from_thread(self.get_character_names)
            messages_snapshot = self.call_from_thread(lambda: list(self.messages))
            
            # Build prompt for emotion analysis
            recent_messages = messages_snapshot[-6:] if len(messages_snapshot) > 6 else messages_snapshot
            conversation_context = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content'][:500]}"
                for msg in recent_messages
            ])
            
            emotion_prompt = f"""Analyze the emotional state of each character based on the recent conversation. Be concise and specific.

IMPORTANT: Use the exact character names provided below. Do NOT refer to characters as "assistant", "user", "AI", or any other generic terms.

Characters: {', '.join(character_names)}

Recent conversation:
{conversation_context}

Provide a brief summary (one sentence per character) of how each character feels right now. Format as:
[Character Name]: [one sentence emotional summary]

Use the exact character names from the list above. If a character hasn't appeared or spoken, you can skip them."""
            
            # Use the same LLM to analyze emotions
            messages_for_analysis = [
                {"role": "system", "content": "You are an expert at analyzing emotional states from dialogue. Always use the exact character names provided by the user. Never refer to characters as 'assistant', 'user', 'AI', or other generic terms. Provide concise, accurate summaries."},
                {"role": "user", "content": emotion_prompt}
            ]
            
            # Get sampling parameters from main thread
            temp = self.call_from_thread(lambda: self.temp)
            topp = self.call_from_thread(lambda: self.topp)
            topk = self.call_from_thread(lambda: self.topk)
            repeat = self.call_from_thread(lambda: self.repeat)
            minp = self.call_from_thread(lambda: self.minp)
            
            # Run non-streaming inference for emotion analysis
            response = self.llm.create_chat_completion(
                messages=messages_for_analysis,
                max_tokens=200,
                temperature=temp,
                top_p=topp,
                top_k=topk,
                repeat_penalty=repeat,
                min_p=minp,
                stream=False
            )
            
            emotion_summary = response["choices"][0]["message"]["content"].strip()
            
            # Update UI from thread
            self.call_from_thread(self._update_emotional_dynamics, emotion_summary)
        except Exception as e:
            # Log error for debugging but don't crash
            import traceback
            try:
                self.call_from_thread(self.notify, f"Emotion analysis failed: {str(e)}", severity="warning")
            except:
                pass
            traceback.print_exc()
    
    def _update_emotional_dynamics(self, content: str):
        """Update the emotional dynamics display. Clears old content and shows new."""
        try:
            self._emotional_dynamics_content = content
            widget = self.query_one("#emotional-dynamics-content", Static)
            if widget:
                # Clear old content and update with new
                widget.update(content)
            else:
                self.notify("Emotional dynamics widget not found!", severity="warning")
        except Exception as e:
            # Log error for debugging
            import traceback
            traceback.print_exc()
            try:
                self.notify(f"Failed to update emotional dynamics: {e}", severity="warning")
            except:
                pass
    
    def clear_emotional_dynamics(self):
        """Clear the emotional dynamics display."""
        try:
            self._emotional_dynamics_content = ""
            widget = self.query_one("#emotional-dynamics-content", Static)
            widget.update("")
        except Exception:
            pass

    async def model_screen_callback(self, result):
        if not result:
            return
        
        if result.get("action") == "load":
            self.is_model_loading = True
            await asyncio.sleep(0.1)
            self.start_model_load(result["model_path"], result["ctx"], result["gpu"])

    async def add_message(self, role: str, content: str, sync_only: bool = False):
        """Helper to add a message to state and UI."""
        if not sync_only:
            self.messages.append({"role": role, "content": content})
        
        chat_scroll = self.query_one("#chat-scroll")
        new_widget = MessageWidget(role, content, self.user_name)
        await chat_scroll.mount(new_widget)
        chat_scroll.scroll_end(animate=False)

    def duplicate_character_card(self, original_path):
        import shutil
        orig = Path(original_path)
        base = orig.stem
        ext = orig.suffix
        parent = orig.parent
        
        counter = 2
        new_path = parent / f"{base}_{counter}{ext}"
        while new_path.exists():
            counter += 1
            new_path = parent / f"{base}_{counter}{ext}"
        
        try:
            shutil.copy2(orig, new_path)
            return new_path
        except Exception as e:
            self.notify(f"Duplication failed: {e}", severity="error")
            return None

    def create_new_character_card(self, filename: str = None):
        """Create a new placeholder character card by copying aimultifool.png and injecting template metadata."""
        cards_dir = self.root_path / "cards"
        cards_dir.mkdir(exist_ok=True)
        
        # Determine filename
        if not filename:
            filename = "New_Character.png"
            counter = 2
            while (cards_dir / filename).exists():
                filename = f"New_Character_{counter}.png"
                counter += 1
        
        new_path = cards_dir / filename
        
        # Check explicit collision
        if new_path.exists():
            return None
            
        source_image = self.root_path / "aimultifool.png"
        if not source_image.exists():
            self.notify("Error: aimultifool.png not found in root directory!", severity="error")
            return None

        import shutil
        try:
            # Copy the source image
            shutil.copy2(source_image, new_path)
            
            # Prepare template metadata
            template = {
                "name": "New Character",
                "description": "",
                "personality": "",
                "scenario": "",
                "first_mes": "",
                "mes_example": "",
                "creatorcomment": "Created with aiMultiFool.",
                "avatar": "none",
                "chat": "",
                "talkativeness": "0.5",
                "fav": False,
                "tags": [],
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    "name": "New Character",
                    "description": "",
                    "personality": "",
                    "scenario": "",
                    "first_mes": "",
                    "mes_example": "",
                    "creator_notes": "",
                    "system_prompt": "",
                    "post_history_instructions": "",
                    "tags": [],
                    "creator": "aiMultiFool",
                    "character_version": "1.0",
                    "alternate_greetings": [],
                    "extensions": {
                        "talkativeness": "0.5",
                        "fav": False,
                        "world": "",
                        "depth_prompt": {
                            "prompt": "",
                            "depth": 4
                        }
                    }
                },
                "create_date": "2024-01-01"
            }
            
            # Write metadata to the PNG using character_manager
            from character_manager import write_chara_metadata
            if write_chara_metadata(str(new_path), template):
                return new_path
            else:
                if new_path.exists(): new_path.unlink()
                return None
        except Exception as e:
            self.notify(f"Failed to create new card: {e}", severity="error")
            if new_path.exists(): new_path.unlink()
            return None

    def edit_character_callback(self, result):
        if not result:
            return
        
        # Result is the new metadata object
        selected_item = self.query_one("#list-characters", ListView).highlighted_child
        if not selected_item:
            return
        
        card_path = getattr(selected_item, "name", "")
        if not card_path:
            return
            
        success = write_chara_metadata(card_path, result)
        if success:
            self.notify(f"Successfully updated metadata in {Path(card_path).name}")
            # If this is the current character, we might want to reload it, 
            # but usually the user would just click it again to start a new chat.
        else:
            self.notify("Failed to write metadata to PNG!", severity="error")

    def add_action_callback(self, result):
        if not result:
            return
            
        new_data = result.get("new")
        original_data = result.get("original")
        
        if original_data:
            # Check if name changed - if so create new, otherwise update
            if new_data.get("name") != original_data.get("name"):
                self.action_menu_data.append(new_data)
                self.notify(f"Added new action (keeping original): {new_data['name']}")
            else:
                # Edit mode: Find and replace
                found = False
                for i, item in enumerate(self.action_menu_data):
                    if item.get("name") == original_data["name"] and item.get("prompt") == original_data["prompt"]:
                         self.action_menu_data[i] = new_data
                         found = True
                         break
                if not found:
                     self.action_menu_data.append(new_data) # Fallback if not found
                self.notify(f"Updated action: {new_data['name']}")
        else:
            # Add mode
            self.action_menu_data.append(new_data)
            self.notify(f"Added action: {new_data['name']}")
            
        save_action_menu_data(self.action_menu_data)
        self.populate_right_sidebar(highlight_item_name=new_data.get("name"))

    def delete_selected_action(self):
        # Find which ListView has the highlighted child
        selected_item = None
        if self._last_action_list and self._last_action_list.highlighted_child:
            selected_item = self._last_action_list.highlighted_child
        else:
            # Fallback
            for lv in self.query(".action-list"):
                if lv.highlighted_child:
                    selected_item = lv.highlighted_child
                    break
                
        if not selected_item:
             self.notify("No action selected to delete!", severity="warning")
             return

        data_packed = getattr(selected_item, "name", "")
        if ":::" in data_packed:
            item_name, prompt, is_system_str = data_packed.split(":::", 2)
            
            # Find and remove from data
            found = False
            for i, item in enumerate(self.action_menu_data):
                if item.get("name") == item_name and item.get("prompt") == prompt:
                    del self.action_menu_data[i]
                    save_action_menu_data(self.action_menu_data)
                    found = True
                    self.notify(f"Deleted action: {item_name}")
                    break
            
            if found:
                self.populate_right_sidebar()
            else:
                self.notify("Could not find action in data!", severity="error")

if __name__ == "__main__":
    try:
        app = AiMultiFoolApp()
        app.run()
    except Exception as e:
        # Catch-all for Windows weirdness or silent crashes
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        if sys.platform == "win32":
            input("Press Enter to close window...")
