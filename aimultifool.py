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
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer, Container
from textual.widgets import Header, Input, Static, Label, Button, Select, ListView, ListItem
from textual.reactive import reactive
from textual.binding import Binding
import llama_cpp

# Modular Logic Mixins
from logic_mixins import InferenceMixin, ActionsMixin
from ui_mixin import UIMixin

# Module Functions
from utils import _get_action_menu_data, load_settings, save_settings, DOWNLOAD_AVAILABLE, get_style_prompt, save_action_menu_data
from character_manager import extract_chara_metadata, process_character_metadata, create_initial_messages
from ai_engine import get_models
from widgets import MessageWidget, Sidebar, AddActionScreen

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
    selected_model = reactive("")
    current_character = reactive(None)
    first_user_message = reactive(None)
    status_text = reactive("Ready")
    is_loading = reactive(False)
    is_model_loading = reactive(False)
    is_downloading = reactive(False)
    is_edit_mode = reactive(False)
    _inference_worker = None

    def notify(self, message: str, *, title: str = "", severity: str = "information", timeout: float = 1.5) -> None:
        """Override notify to halve the default display time."""
        super().notify(message, title=title, severity=severity, timeout=timeout)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Sidebar(id="sidebar"),
            Vertical(
                ScrollableContainer(id="chat-scroll"),
                Container(
                    Input(placeholder="Type your message here...", id="chat-input"),
                    Horizontal(
                        Button("Stop [^S]", id="btn-stop", variant="default"),
                        Button("Continue [^Enter]", id="btn-continue", variant="default"),
                        Button("Sidebar [^B]", id="btn-toggle-sidebar", variant="default"),
                        Button("Rewind [^Z]", id="btn-rewind", variant="default"),
                        Button("Restart [^R]", id="btn-restart", variant="default"),
                        Button("Clear [^W]", id="btn-clear-chat", variant="default"),
                        Button("Quit [^Q]", id="btn-quit", variant="default"),
                        Button("Buy Coffee", id="btn-coffee", variant="default"),
                        Button("Discord", id="btn-discord", variant="default"),
                        id="action-buttons"
                    ),
                    id="input-container"
                ),
                id="main-container"
            ),
            Vertical(
                Select([], id="select-action-category", prompt="Filter Category"),
                ListView(id="list-actions"),
                Button("Enter Edit Mode", id="btn-edit-mode", variant="default"),
                Horizontal(
                    Button("Add New", id="btn-add-action", variant="default", disabled=True),
                    Button("Delete", id="btn-delete-action", variant="default", disabled=True),
                    classes="action-control-buttons"
                ),
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
        self.temp = 0.8
        self.topp = 0.9
        self.topk = 40
        self.repeat = 1.0
        self.selected_model = settings.get("selected_model", "")

        self.update_model_list()
        self.update_character_list()
        
        self.action_menu_data = _get_action_menu_data()
        self.populate_right_sidebar()
        
        # Apply UI values
        self.query_one("#input-username").value = self.user_name
        self.query_one("#select-context").value = self.context_size
        self.query_one("#select-gpu-layers").value = self.gpu_layers
        self.query_one("#select-style").value = self.style
        
        self.query_one("#input-temp").value = f"{self.temp:.2f}"
        self.query_one("#input-topp").value = f"{self.topp:.2f}"
        self.query_one("#input-topk").value = str(self.topk)
        self.query_one("#input-repeat").value = f"{self.repeat:.2f}"

        if self.selected_model:
            try:
                self.query_one("#select-model").value = self.selected_model
            except Exception:
                self.selected_model = ""

        self.title = f"aiMultiFool v0.1.2"
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

    async def on_focus(self, event) -> None:
        if hasattr(self, 'show_footer'):
            self.show_footer = True

    def update_ui_state(self):
        """Disable or enable UI elements based on app state."""
        is_busy = self.is_model_loading or self.is_downloading
        
        # Disable/Enable all interactive elements
        for btn in self.query(Button):
            # Always keep Quit, Coffee, and Discord buttons enabled
            if btn.id in ["btn-quit", "btn-coffee", "btn-discord"]:
                btn.disabled = False
            else:
                btn.disabled = is_busy
            
        for select in self.query(Select):
            select.disabled = is_busy
            
        for inp in self.query(Input):
            # is_busy (loading model/downloading) always disables.
            # is_loading (inference) no longer disables chat-input.
            inp.disabled = is_busy
            
        self.query_one("#list-characters").disabled = is_busy or not self.llm
        self.query_one("#list-actions").disabled = is_busy or (not self.llm and not self.is_edit_mode)

    def update_model_list(self):
        models = get_models()
        select = self.query_one("#select-model", Select)
        options = [(m.name, str(m)) for m in models]
        select.set_options(options)
        if options:
            select.value = options[0][1]

    def update_character_list(self):
        cards_dir = Path(__file__).parent / "cards"
        if not cards_dir.exists():
            cards_dir.mkdir(parents=True, exist_ok=True)
        cards = list(cards_dir.glob("*.png"))
        list_view = self.query_one("#list-characters", ListView)
        list_view.clear()
        for card in sorted(cards):
            list_view.append(ListItem(Label(card.name), name=str(card)))
    
    def enable_character_list(self):
        self.query_one("#list-characters").disabled = False
        self.query_one("#list-actions").disabled = False
    
    def disable_character_list(self):
        self.query_one("#list-characters").disabled = True
        self.query_one("#list-actions").disabled = True
    
    def focus_chat_input(self):
        try:
            self.query_one("#chat-input").focus()
        except Exception:
            pass

    def populate_right_sidebar(self, filter_category: str = None):
        right_sidebar = self.query_one("#right-sidebar", Vertical)
        list_view = self.query_one("#list-actions", ListView)
        list_view.clear()
        
        if not self.action_menu_data:
            right_sidebar.remove_class("-visible")
            return
            
        right_sidebar.add_class("-visible")
        
        if isinstance(self.action_menu_data, list) and len(self.action_menu_data) > 0:
            first_item = self.action_menu_data[0]
            if isinstance(first_item, dict) and "sectionName" in first_item:
                # Handle legacy nested format
                flattened = []
                for section in self.action_menu_data:
                    section_name = section.get("sectionName", "")
                    items = section.get("items", [])
                    for item in items:
                        if item.get("itemName") != "-":
                            if section_name == "System Prompts":
                                item["isSystem"] = True
                            # Extract category from name if possible (e_g_ "Action: Describe" -> "Action")
                            name = item.get("itemName", "")
                            if ":" in name:
                                item["category"] = name.split(":", 1)[0].strip()
                            flattened.append(item)
                self.action_menu_data = flattened

        # Ensure all items have categories extracted
        categories = set()
        for item in self.action_menu_data:
            name = item.get("itemName", "")
            if ":" in name:
                cat = name.split(":", 1)[0].strip()
                item["category"] = cat
                categories.add(cat)
            else:
                cat = "Other"
                item["category"] = cat
                categories.add(cat)

        # Update category select if not already set or if data changed
        cat_select = self.query_one("#select-action-category", Select)
        if not cat_select._options or len(cat_select._options) <= 1:
            cat_options = [("All", "All")] + sorted([(c, c) for c in categories])
            cat_select.set_options(cat_options)
            cat_select.set_options(cat_options)
            cat_select.value = "All"

        # Sort data alphabetically by itemName
        self.action_menu_data.sort(key=lambda x: x.get("itemName", "").lower())

        for item in self.action_menu_data:
            item_name = item.get("itemName", "None")
            prompt = item.get("prompt", "")
            is_system = item.get("isSystem", False)
            category = item.get("category", "Other")
            
            if filter_category and filter_category != "All" and category != filter_category:
                continue

            # Pack all data into name attribute to avoid querying children
            data_packed = f"{item_name}:::{prompt}:::{is_system}"
            list_view.append(ListItem(Label(item_name), name=data_packed))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item:
            return

        try:
            if event.list_view.id == "list-characters":
                card_path = getattr(event.item, "name", "")
                if card_path:
                    await self.load_character_from_path(card_path)
                    self.focus_chat_input()
            elif event.list_view.id == "list-actions":
                data_packed = getattr(event.item, "name", "")
                if ":::" in data_packed:
                    parts = data_packed.split(":::", 2)
                    if len(parts) == 3:
                        item_name, prompt, is_system_str = parts
                        is_system = is_system_str == "True"
                        
                        if self.is_edit_mode:
                            # Open edit modal
                            edit_data = {"itemName": item_name, "prompt": prompt, "isSystem": is_system}
                            self.push_screen(AddActionScreen(edit_data), self.add_action_callback)
                            return

                        section = "System Prompts" if is_system else "Actions"
                        await self.handle_menu_action(section, item_name, prompt)
                self.focus_chat_input()
        except Exception as e:
            self.notify(f"Selection error: {e}", severity="error")

    async def load_character_from_path(self, card_path):
        if self.is_loading:
            await self.action_stop_generation()

        try:
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
        if event.select.id == "select-action-category":
            self.populate_right_sidebar(event.value)
            return

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
        elif event.input.id == "input-temp" or event.input.id == "input-topp" or event.input.id == "input-topk" or event.input.id == "input-repeat":
            try:
                val = float(event.value) if "." in event.value else int(event.value)
                setattr(self, event.input.id.replace("input-", ""), val)
                self.save_user_settings()
            except ValueError: pass
        elif event.input.id == "chat-input":
            if self.is_loading and event.value.strip():
                await self.action_stop_generation()

    def update_system_prompt_style(self, style: str) -> None:
        if not self.messages: return
        has_started = len(self.messages) > 1
        if self.current_character:
            if has_started: self.notify("Style changes don't affect character cards.", severity="information")
            return
        new_content = get_style_prompt(style)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = new_content
            if has_started: self.notify(f"System style updated to: {style.capitalize()}")

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
        elif event.button.id == "btn-quit": self.exit()
        elif event.button.id == "btn-coffee": webbrowser.open("https://ko-fi.com/aimultifool")
        elif event.button.id == "btn-discord": webbrowser.open("https://discord.com/invite/J5vzhbmk35")
        elif event.button.id == "btn-add-action":
            self.push_screen(AddActionScreen(), self.add_action_callback)
        elif event.button.id == "btn-delete-action":
            self.delete_selected_action()
        elif event.button.id == "btn-edit-mode":
            self.is_edit_mode = not self.is_edit_mode
            btn_edit = self.query_one("#btn-edit-mode", Button)
            btn_add = self.query_one("#btn-add-action", Button)
            btn_del = self.query_one("#btn-delete-action", Button)
            list_actions = self.query_one("#list-actions")
            
            if self.is_edit_mode:
                btn_edit.label = "Exit Edit Mode"
                btn_add.disabled = False
                btn_del.disabled = False
                if not self.llm:
                    list_actions.disabled = False
            else:
                btn_edit.label = "Enter Edit Mode"
                btn_add.disabled = True
                btn_del.disabled = True
                if not self.llm:
                    list_actions.disabled = True
        self.focus_chat_input()

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
            
        self.action_menu_data.sort(key=lambda x: x.get("itemName", "").lower())
        save_action_menu_data(self.action_menu_data)
        self.populate_right_sidebar(self.query_one("#select-action-category").value)

    def delete_selected_action(self):
        list_view = self.query_one("#list-actions", ListView)
        selected_item = list_view.highlighted_child
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
                self.populate_right_sidebar(self.query_one("#select-action-category").value)
            else:
                self.notify("Could not find action in data!", severity="error")

if __name__ == "__main__":
    app = AiMultiFoolApp()
    app.run()
