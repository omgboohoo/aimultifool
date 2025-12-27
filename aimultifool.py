#!/usr/bin/env python3
"""
aiMultiFool - Textual TUI chat app with llama-cpp-python
"""

import os
import sys
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
from logic_mixins import InferenceMixin, ActionsMixin
from ui_mixin import UIMixin

# Module Functions
from utils import _get_action_menu_data, load_settings, save_settings, DOWNLOAD_AVAILABLE, get_style_prompt, save_action_menu_data
from character_manager import extract_chara_metadata, process_character_metadata, create_initial_messages, write_chara_metadata
from ai_engine import get_models
from widgets import MessageWidget, Sidebar, AddActionScreen, EditCharacterScreen, CharactersScreen, ParametersScreen, AboutScreen, ActionsManagerScreen

class AiMultiFoolApp(App, InferenceMixin, ActionsMixin, UIMixin):
    """The main aiMultiFool application."""
    
    # Load CSS from external file (absolute path to prevent 'File Not Found' errors)
    CSS_PATH = str(Path(__file__).parent / "styles.tcss")

    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Toggle Sidebars"),
        Binding("ctrl+r", "reset_chat", "Restart from first prompt"),
        Binding("ctrl+z", "rewind", "Rewind last exchange"),
        Binding("ctrl+shift+w", "wipe_all", "Clear Chat"),
        Binding("ctrl+s", "stop_generation", "Stop AI"),
        Binding("ctrl+enter", "continue_chat", "Continue AI"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    llm = None
    action_menu_data = []
    messages = reactive([])
    user_name = reactive("Dan")
    context_size = reactive(4096)
    gpu_layers = reactive(-1)
    style = reactive("concise")
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
    _inference_worker = None
    _last_action_list = None

    def notify(self, message: str, *, title: str = "", severity: str = "information", timeout: float = 1.5) -> None:
        """Override notify to halve the default display time."""
        super().notify(message, title=title, severity=severity, timeout=timeout)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Button("Sidebar", id="btn-toggle-sidebar", variant="default"),
            Button("Cards", id="btn-cards", variant="default"),
            Button("Parameters", id="btn-parameters", variant="default"),
            Button("Actions", id="btn-manage-actions", variant="default"),
            Button("About", id="btn-about", variant="default"),
            id="top-menu-bar"
        )
        yield Horizontal(
            Sidebar(id="sidebar"),
            Vertical(
                ScrollableContainer(id="chat-scroll"),
                Container(
                    Input(placeholder="Type your message here...", id="chat-input"),
                    Horizontal(
                        Button("Stop", id="btn-stop", variant="default"),
                        Button("Continue", id="btn-continue", variant="default"),
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
                Horizontal(
                    Input(placeholder="Search actions...", id="input-action-search"),
                    Button("Clear", id="btn-clear-search", variant="default", disabled=True),
                    id="search-container"
                ),
                Vertical(id="action-sections"),
                id="right-sidebar"
            ),
            id="main-layout"
        )
        yield Static("Ready", id="status-bar")

    async def on_mount(self) -> None:
        # Load persisted settings
        settings = load_settings()
        self.user_name = settings.get("user_name", "Dan")
        self.context_size = settings.get("context_size", 4096)
        self.gpu_layers = -1
        self.style = settings.get("style", "concise")
        self.temp = settings.get("temp", 0.8)
        self.topp = settings.get("topp", 0.9)
        self.topk = settings.get("topk", 40)
        self.repeat = settings.get("repeat", 1.0)
        self.minp = settings.get("minp", 0.0)
        self.selected_model = settings.get("selected_model", "")

        self.update_model_list()
        # Defer character list update until Cards screen is opened
        
        self.action_menu_data = _get_action_menu_data()
        self.populate_right_sidebar()
        
        # Apply UI values
        self.query_one("#input-username").value = self.user_name
        self.query_one("#select-context").value = self.context_size
        self.query_one("#select-gpu-layers").value = self.gpu_layers
        self.query_one("#select-style").value = self.style

        if self.selected_model:
            try:
                self.query_one("#select-model").value = self.selected_model
            except Exception:
                self.selected_model = ""

        self.title = f"aiMultiFool v0.1.5"
        self.query_one("#sidebar").add_class("-visible")
        self.query_one("#right-sidebar").add_class("-visible")
        self.watch_is_loading(self.is_loading)
        self.watch_is_downloading(self.is_downloading)
        self.watch_is_model_loading(self.is_model_loading)
        
        models = get_models()
        if not models:
            self.notify("No models found! Downloading default...", severity="information")
            self.download_default_model()
        
        new_content = get_style_prompt(self.style)
        self.messages = [{"role": "system", "content": new_content}]
        self.disable_character_list() # Start disabled
        self.show_footer = True

    def watch_is_loading(self, is_loading: bool) -> None:
        """Called when is_loading (inference) changes."""
        # Allow typing while loading
        self.query_one("#chat-input").disabled = False
        self.query_one("#btn-stop").disabled = not is_loading
        
        # Sync visibility
        try:
            self.query_one("#btn-stop").display = is_loading
            self.query_one("#btn-continue").display = not is_loading
        except Exception:
            pass

    def watch_is_downloading(self, is_downloading: bool) -> None:
        """Called when is_downloading changes."""
        self.update_ui_state()

    def watch_is_model_loading(self, is_model_loading: bool) -> None:
        """Called when is_model_loading changes."""
        self.update_ui_state()

        
    def watch_is_char_edit_mode(self, is_char_edit_mode: bool) -> None:
        """Called when is_char_edit_mode changes."""
        self.update_ui_state()

    async def on_focus(self, event) -> None:
        if hasattr(self, 'show_footer'):
            self.show_footer = True

    def update_ui_state(self):
        """Disable or enable UI elements based on app state."""
        is_busy = self.is_model_loading or self.is_downloading
        
        for btn in self.query(Button):
            # Always keep these top menu buttons enabled
            if btn.id in ["btn-about", "btn-cards", "btn-parameters", "btn-toggle-sidebar", "btn-manage-actions"]:
                btn.disabled = False
            elif btn.id in ["btn-continue", "btn-rewind", "btn-restart", "btn-clear-chat"]:
                # Disable if busy OR if no model is loaded
                btn.disabled = is_busy or not self.llm
            elif btn.id == "btn-clear-search":
                # Only enabled if there is text in the search box
                search_val = self.query_one("#input-action-search").value
                btn.disabled = not bool(search_val.strip())
            else:
                btn.disabled = is_busy
            
        for select in self.query(Select):
            select.disabled = is_busy
            
        for inp in self.query(Input):
            if inp.id == "chat-input":
                inp.disabled = is_busy or not self.llm
            else:
                inp.disabled = is_busy
            
        try:
            self.query_one("#list-characters").disabled = is_busy or (not self.llm and not self.is_char_edit_mode)
            self.query_one("#btn-char-edit-mode").disabled = is_busy
        except Exception:
            pass
        for lv in self.query(".action-list"):
            lv.disabled = is_busy or not self.llm
        for collapsible in self.query(Collapsible):
            collapsible.disabled = is_busy

    def update_model_list(self):
        models = get_models()
        select = self.query_one("#select-model", Select)
        options = [(m.name, str(m)) for m in models]
        select.set_options(options)
        if options:
            select.value = options[0][1]

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

    def populate_right_sidebar(self, filter_text="", highlight_item_name=None):
        filter_text = filter_text.lower()
        right_sidebar = self.query_one("#right-sidebar", Vertical)
        action_sections = self.query_one("#action-sections", Vertical)
        
        # Clear existing sections
        action_sections.remove_children()
        
        if not self.action_menu_data:
            right_sidebar.remove_class("-visible")
            return
            
        right_sidebar.add_class("-visible")
        
        # Format and categorize data
        if isinstance(self.action_menu_data, list) and len(self.action_menu_data) > 0:
            first_item = self.action_menu_data[0]
            if isinstance(first_item, dict) and "sectionName" in first_item:
                flattened = []
                for section in self.action_menu_data:
                    section_name = section.get("sectionName", "")
                    items = section.get("items", [])
                    for item in items:
                        if item.get("itemName") != "-":
                            if section_name == "System Prompts":
                                item["isSystem"] = True
                            name = item.get("itemName", "")
                            if ":" in name:
                                parts = name.split(":", 1)
                                item["category"] = parts[0].strip()
                                item["itemName"] = parts[1].strip()
                            flattened.append(item)
                self.action_menu_data = flattened

        categories = set()
        for item in self.action_menu_data:
            name = item.get("itemName", "")
            if ":" in name:
                parts = name.split(":", 1)
                item["category"] = parts[0].strip()
                item["itemName"] = parts[1].strip()
            elif "category" not in item:
                item["category"] = "Other"
            
            categories.add(item.get("category", "Other"))

        # Sort all data: Category (A-Z) then Item Name (A-Z)
        self.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("itemName", "").lower()))

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
                item_name = item.get("itemName", "None")
                display_name = item_name
                if ":" in display_name:
                    display_name = display_name.split(":", 1)[1].strip()
                
                prompt = item.get("prompt", "")
                
                # Filter logic
                if filter_text and filter_text not in item_name.lower() and filter_text not in prompt.lower():
                    continue
                
                is_system = item.get("isSystem", False)
                data_packed = f"{item_name}:::{prompt}:::{is_system}"
                list_items.append(ListItem(Label(display_name), name=data_packed))
            
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

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item:
            return

        try:
            if event.list_view.id == "list-characters":
                # Character loading is now handled by the Play button in CharactersScreen.
                # Selection here doesn't trigger AI, only highlights and loads metadata (handled in on_list_view_highlighted).
                pass
            elif event.list_view.has_class("action-list"):
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
        if self.is_loading:
            await self.action_stop_generation()

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
            self.update_system_prompt_style(self.style)
            self.query_one("#chat-scroll").remove_children()
            self.notify(f"Loaded character: {Path(card_path).name}")
            if self.llm:
                if len(self.messages) > 1 and self.messages[-1]["role"] == "user":
                    self.messages[-1]["content"] = "continue"
                else:
                    self.messages.append({"role": "user", "content": "continue"})
                self.is_loading = True
                self._inference_worker = self.run_inference("continue")
        except Exception as e:
            self.notify(f"Error loading character: {e}", severity="error")

    async def handle_menu_action(self, section_name: str, item_name: str, prompt: str):
        if self.is_loading:
            await self.action_stop_generation()

        # Replace {{user}} with the user's name
        prompt = re.sub(r'\{\{user\}\}', self.user_name, prompt, flags=re.IGNORECASE)

        if section_name == "System Prompts":
            self.set_system_prompt(prompt, item_name)
        else:
            if not self.current_character and self.first_user_message is None:
                self.first_user_message = prompt
                
            self.notify(f"Action: {item_name}")
            await self.add_message("user", prompt)
            self.is_loading = True
            self._inference_worker = self.run_inference(prompt)

    def set_system_prompt(self, prompt: str, name: str):
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = prompt
            self.notify(f"System prompt set to: {name}")
        else:
            self.messages = [{"role": "system", "content": prompt}, *self.messages]
            self.notify(f"System prompt added: {name}")

    async def on_select_changed(self, event: Select.Changed) -> None:
        has_started = len(self.messages) > 1
        if event.select.id == "select-style":
            self.style = event.value
            self.update_system_prompt_style(event.value)
        elif event.select.id == "select-context":
            self.context_size = int(event.value)
            if has_started: self.notify(f"Context size set to: {event.value}")
        elif event.select.id == "select-gpu-layers":
            self.gpu_layers = int(event.value)
            if has_started: self.notify(f"GPU layers set to: {event.value}")
        elif event.select.id == "select-model":
            self.selected_model = str(event.value)
            if has_started: self.notify(f"Model selected: {Path(event.value).name}")
        self.save_user_settings()
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

    def update_system_prompt_style(self, style: str) -> None:
        if not self.messages: return
        has_started = len(self.messages) > 1
        
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
            if has_started: self.notify(f"Style updated: {style.capitalize()}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            if self.is_loading:
                await self.action_stop_generation()

            user_text = event.value.strip() or "continue"
            event.input.value = ""
            if not self.current_character and self.first_user_message is None:
                self.first_user_message = user_text
            await self.add_message("user", user_text)
            self.is_loading = True
            self._inference_worker = self.run_inference(user_text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-load-model":
            model_path = self.query_one("#select-model").value
            if not model_path:
                self.notify("Please select a model first!", severity="warning")
                return
            ctx = int(self.query_one("#select-context").value)
            gpu = int(self.query_one("#select-gpu-layers").value)
            self.user_name = self.query_one("#input-username").value
            if self.llm:
                self.disable_character_list()
                llama_cpp.llama_backend_free()
                del self.llm
                gc.collect()
                llama_cpp.llama_backend_init()
            self.is_model_loading = True
            self.load_model_task(model_path, ctx, gpu)
        elif event.button.id == "btn-stop": await self.action_stop_generation()
        elif event.button.id == "btn-continue": await self.action_continue_chat()
        elif event.button.id == "btn-toggle-sidebar": self.action_toggle_sidebar()
        elif event.button.id == "btn-restart": await self.action_reset_chat()
        elif event.button.id == "btn-rewind": await self.action_rewind()
        elif event.button.id == "btn-clear-chat": await self.action_wipe_all()
        elif event.button.id == "btn-manage-actions":
            self.push_screen(ActionsManagerScreen(), self.actions_mgmt_callback)
        elif event.button.id == "btn-cards":
            self.push_screen(CharactersScreen(), self.cards_screen_callback)
        elif event.button.id == "btn-parameters":
            self.push_screen(ParametersScreen())
        elif event.button.id == "btn-about":
            self.push_screen(AboutScreen())
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
        self.focus_chat_input()

    async def cards_screen_callback(self, result):
        if not result:
            return
        
        action = result.get("action")
        path = result.get("path")
        
        if action == "play":
            meta = result.get("meta")
            await self.load_character_from_path(path, chara_json_obj=meta)
        elif action == "duplicate":
            new_path = self.duplicate_character_card(path)
            if new_path:
                self.notify(f"Duplicated: {os.path.basename(new_path)}")
        
    async def actions_mgmt_callback(self, result):
        # Always refresh sidebar after mgmt modal
        self.populate_right_sidebar()
        
        self.focus_chat_input()

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
            if new_data.get("itemName") != original_data.get("itemName"):
                self.action_menu_data.append(new_data)
                self.notify(f"Added new action (keeping original): {new_data['itemName']}")
            else:
                # Edit mode: Find and replace
                found = False
                for i, item in enumerate(self.action_menu_data):
                    if item.get("itemName") == original_data["itemName"] and item.get("prompt") == original_data["prompt"]:
                         self.action_menu_data[i] = new_data
                         found = True
                         break
                if not found:
                     self.action_menu_data.append(new_data) # Fallback if not found
                self.notify(f"Updated action: {new_data['itemName']}")
        else:
            # Add mode
            self.action_menu_data.append(new_data)
            self.notify(f"Added action: {new_data['itemName']}")
            
        save_action_menu_data(self.action_menu_data)
        self.populate_right_sidebar(highlight_item_name=new_data.get("itemName"))

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
                if item.get("itemName") == item_name and item.get("prompt") == prompt:
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
    app = AiMultiFoolApp()
    app.run()
