import re
import json
import webbrowser
from rich.text import Text
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Container, Horizontal, Grid, ScrollableContainer
from textual.widgets import Label, Input, Select, Button, ListView, ListItem, Static, TextArea
from pathlib import Path
from utils import save_action_menu_data, encrypt_data, decrypt_data, copy_to_clipboard

def create_styled_text(text):
    """Create a rich renderable with styled quoted text"""
    pattern = r'"([^"\\]*(\\.[^"\\]*)*)"'
    parts = []
    last_end = 0
    
    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            parts.append(('text', text[last_end:match.start()]))
        quoted_text = match.group(0)
        parts.append(('styled', quoted_text))
        last_end = match.end()
    
    if last_end < len(text):
        parts.append(('text', text[last_end:]))
    
    if not parts:
        return Text(text)
    
    renderables = []
    for i, (part_type, part_text) in enumerate(parts):
        if part_type == 'styled':
            styled_text = Text(part_text, style="italic #FFDB58")
            renderables.append(styled_text)
        else:
            if part_text:
                renderables.append(Text(part_text))
    
    if len(renderables) == 1:
        return renderables[0]
    return Text.assemble(*renderables)

class MessageWidget(Static):
    """A widget to display a single chat message."""
    def __init__(self, role: str, content: str, user_name: str = "User", **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.user_name = user_name

    def on_mount(self):
        if self.role == "user":
            self.add_class("-user")
        elif self.role == "system":
            self.add_class("-system")
        else:
            self.add_class("-assistant")

    def render(self):
        if self.role == "user":
            return Text(self.content, style="green")
        elif self.role == "system":
            return Text(self.content, style="italic #888888")
        else:
            return create_styled_text(self.content)

class ModelScreen(ModalScreen):
    """The modal for model selection and settings."""
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Model Settings", classes="dialog-title"),
            Container(
                Label("Model"),
                Select([], id="select-model", prompt="Select a model"),
                classes="setting-group"
            ),
            Container(
                Label("Context Size"),
                Select([(str(x), x) for x in [2048, 4096, 8192, 16384, 32768]], id="select-context", value=4096),
                classes="setting-group"
            ),
            Container(
                Label("GPU Layers"),
                Select([("All (-1)", -1), ("CPU Only (0)", 0)] + [(str(x), x) for x in range(8, 129, 8)], id="select-gpu-layers", value=-1),
                classes="setting-group"
            ),
            Horizontal(
                Button("Load Model", variant="default", id="btn-load-model"),
                Button("Close", variant="default", id="btn-close-model"),
                classes="buttons"
            ),
            id="model-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        # Populate fields from app state
        app = self.app

        # Validate and set Context Size
        try:
            self.query_one("#select-context").value = app.context_size
        except Exception:
            self.query_one("#select-context").value = 4096

        # Validate and set GPU Layers
        try:
            self.query_one("#select-gpu-layers").value = app.gpu_layers
        except Exception:
            self.query_one("#select-gpu-layers").value = -1
        
        # Populate models
        from ai_engine import get_models
        models = get_models()
        select_model = self.query_one("#select-model", Select)
        options = [(m.name, str(m)) for m in models]
        select_model.set_options(options)
        
        if app.selected_model:
            try:
                # check if selected model is in options
                if any(opt[1] == app.selected_model for opt in options):
                    select_model.value = app.selected_model
                elif options:
                    select_model.value = options[0][1]
            except Exception:
                pass
        elif options:
            select_model.value = options[0][1]
        
        self.app.update_ui_state()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-model":
            self.dismiss()
        elif event.button.id == "btn-load-model":
            try:
                model_path = self.query_one("#select-model").value
                ctx = int(self.query_one("#select-context").value)
                gpu = int(self.query_one("#select-gpu-layers").value)
                
                self.dismiss({
                    "action": "load",
                    "model_path": model_path,
                    "ctx": ctx,
                    "gpu": gpu
                })
            except Exception as e:
                self.app.notify(f"Error gathering settings: {e}", severity="error")
        # btn-load-model is handled by the main app via bubbling or we delegate it here?
        # Standard pattern in this app is bubbling for main actions, but we need to ensure the app can read values.
        # Since on_select_changed updates app state, bubbling is fine IF app reads from app state, not widgets.

class AddActionScreen(ModalScreen):
    """Screen for adding or editing an action."""

    def __init__(self, edit_data=None):
        super().__init__()
        self.edit_data = edit_data

    def compose(self) -> ComposeResult:
        title = "Edit Action" if self.edit_data else "Add New Action"
        yield Vertical(
            Label(title, classes="dialog-title"),
            Label("Name", classes="label"),
            Input(placeholder="e.g. Category: Action Name", id="name"),
            Label("Prompt", classes="label"),
            TextArea(id="prompt"),
            Label("Type", classes="label"),
            Select([("Action", False), ("System Prompt", True)], id="type", value=False, allow_blank=False),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Save", variant="default", id="save"),
                classes="buttons"
            ),
            id="dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        if self.edit_data:
            self.query_one("#name").value = self.edit_data.get("itemName", "")
            self.query_one("#prompt").text = self.edit_data.get("prompt", "") # TextArea uses .text
            self.query_one("#type").value = self.edit_data.get("isSystem", False)
        self.query_one("#name").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            name = self.query_one("#name").value
            prompt = self.query_one("#prompt").text
            is_system = self.query_one("#type").value
            if name and prompt:
                new_data = {"itemName": name, "prompt": prompt, "isSystem": is_system}
                self.dismiss({"original": self.edit_data, "new": new_data})
        elif event.button.id == "cancel":
            self.dismiss(None)

class EditCharacterScreen(ModalScreen):
    """Screen for editing character PNG metadata."""
    def __init__(self, chara_json, chara_path):
        super().__init__()
        self.chara_json = chara_json
        self.chara_path = chara_path

    def compose(self) -> ComposeResult:
        try:
            # Try to pretty print the JSON
            parsed = json.loads(self.chara_json)
            pretty_json = json.dumps(parsed, indent=4)
        except Exception:
            pretty_json = self.chara_json

        yield Vertical(
            Label(f"Edit Character: {self.chara_path.name}", classes="dialog-title"),
            Label("Metadata (JSON)", classes="label"),
            TextArea(pretty_json, id="metadata-text"),
            Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Save to PNG", variant="default", id="save"),
                classes="buttons"
            ),
            id="edit-character-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        self.query_one("#metadata-text").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            metadata_str = self.query_one("#metadata-text").text
            try:
                # Validate JSON
                metadata_obj = json.loads(metadata_str)
                self.dismiss(metadata_obj)
            except json.JSONDecodeError as e:
                self.app.notify(f"Invalid JSON: {e}", severity="error")
                pass
        elif event.button.id == "cancel":
            self.dismiss(None)

class ContextWindowScreen(ModalScreen):
    """Screen for showing the current chat context."""
    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def compose(self) -> ComposeResult:
        context_text = json.dumps(self.messages, indent=2)
        yield Vertical(
            Label("Context Window", classes="dialog-title"),
            TextArea(context_text, id="context-text", read_only=True),
            Horizontal(
                Button("Copy", variant="default", id="copy"),
                Button("Close", variant="default", id="close"),
                classes="buttons"
            ),
            id="context-window-dialog",
            classes="modal-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss()
        elif event.button.id == "copy":
            context_text = self.query_one("#context-text", TextArea).text
            # Try our robust Linux copy first (uses xclip/xsel)
            if not copy_to_clipboard(context_text):
                # Fallback to Textual's OSC 52 method
                self.app.copy_to_clipboard(context_text)
            self.app.notify("Context copied to clipboard!")

class CharactersScreen(ModalScreen):
    """Integrated character list and metadata editor."""
    last_search_idx = -1

    def on_mount(self) -> None:
        self.last_search_idx = -1
        self.app.update_ui_state()

    def compose(self) -> ComposeResult:
        cards = self.app.get_card_list()
        items = [ListItem(Label(card.name), name=str(card)) for card in cards]
        
        yield Vertical(
            Label("Character Management", classes="dialog-title"),
            Horizontal(
                Vertical(
                    Label("Cards", classes="label"),
                    ListView(*items, id="list-characters"),
                    classes="pane-left"
                ),
                Vertical(
                    Label("Metadata (JSON)", classes="label"),
                    Horizontal(
                        Input(placeholder="Search...", id="input-search-meta"),
                        Input(placeholder="Replace...", id="input-replace-meta"),
                        Button("Replace", id="btn-replace-all", variant="default"),
                        id="search-replace-container"
                    ),
                    TextArea(id="metadata-text"),
                    classes="pane-right"
                ),
                id="management-split"
            ),
            Horizontal(
                Button("Play", variant="default", id="btn-play-card", disabled=not self.app.llm),
                Button("Duplicate", variant="default", id="btn-duplicate-card"),
                Button("Save Changes", variant="default", id="btn-save-metadata"),
                Button("Cancel", variant="default", id="btn-cancel-mgmt"),
                classes="buttons"
            ),
            id="characters-dialog",
            classes="modal-dialog"
        )

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "list-characters" and event.item:
            card_path = getattr(event.item, "name", "")
            if card_path:
                from character_manager import extract_chara_metadata
                chara_json = extract_chara_metadata(card_path)
                if chara_json:
                    try:
                        parsed = json.loads(chara_json)
                        pretty_json = json.dumps(parsed, indent=4)
                    except Exception:
                        pretty_json = chara_json
                    self.query_one("#metadata-text", TextArea).text = pretty_json
                else:
                    self.query_one("#metadata-text", TextArea).text = "No metadata found."

    def perform_search(self, search_text, start_from=0):
        if not search_text:
            return

        # Use query() instead of query_one() to avoid NoMatches crash
        tas = self.query("#metadata-text")
        if not tas:
            return
        text_area = tas.first()
        
        content = text_area.text
        content_lower = content.lower()
        query_lower = search_text.lower()
        
        # Try finding from the current position
        idx = content_lower.find(query_lower, start_from)
        
        # If not found and we didn't start at the beginning, cycle back to top
        if idx == -1 and start_from > 0:
            idx = content_lower.find(query_lower, 0)
            
        if idx != -1:
            self.last_search_idx = idx
            try:
                # Convert index to line/column for Textual's selection
                lines = content[:idx].split('\n')
                line_idx = len(lines) - 1
                col_idx = len(lines[-1])
                
                # We use the actual match length
                actual_match = content[idx:idx + len(search_text)]
                end_lines = content[:idx + len(actual_match)].split('\n')
                end_line_idx = len(end_lines) - 1
                end_col_idx = len(end_lines[-1])
                
                # Selection assignment can vary by Textual version; try common methods
                try:
                    text_area.selection = ((line_idx, col_idx), (end_line_idx, end_col_idx))
                except Exception:
                    # Fallback for other versions
                    if hasattr(text_area, "select_range"):
                        text_area.select_range((line_idx, col_idx), (end_line_idx, end_col_idx))
                
                text_area.scroll_to_line(line_idx)
            except Exception:
                pass
        else:
            self.last_search_idx = -1

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "input-search-meta":
            self.perform_search(event.value, start_from=0)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-search-meta":
            # Search from the next character to find the NEXT occurrence
            self.perform_search(event.value, start_from=self.last_search_idx + 1)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        selected_item = self.query_one("#list-characters", ListView).highlighted_child
        card_path = getattr(selected_item, "name", "") if selected_item else None

        if event.button.id == "btn-play-card":
            if not self.app.llm:
                self.app.notify("Model not loaded! Load a model from the sidebar first.", severity="warning")
                return
            if card_path:
                metadata_str = self.query_one("#metadata-text", TextArea).text.strip()
                # We don't care if it's JSON or not, the engine now handles both
                self.dismiss({"action": "play", "path": card_path, "meta": metadata_str})
            else:
                self.app.notify("Select a card first!", severity="warning")
        elif event.button.id == "btn-duplicate-card":
            if card_path:
                self.dismiss({"action": "duplicate", "path": card_path})
            else:
                self.app.notify("Select a card first!", severity="warning")
        elif event.button.id == "btn-replace-all":
            search_text = self.query_one("#input-search-meta", Input).value
            replace_text = self.query_one("#input-replace-meta", Input).value
            if search_text:
                text_area = self.query_one("#metadata-text", TextArea)
                old_content = text_area.text
                # Use regex for case-insensitive replacement
                import re
                new_content = re.sub(re.escape(search_text), replace_text, old_content, flags=re.IGNORECASE)
                
                if old_content != new_content:
                    text_area.text = new_content
                    self.app.notify(f"Replaced occurrences of '{search_text}' (case-insensitive)")
                else:
                    self.app.notify(f"'{search_text}' not found.", severity="warning")
            else:
                self.app.notify("Enter search text!", severity="warning")
        elif event.button.id == "btn-save-metadata":
            if card_path:
                metadata_str = self.query_one("#metadata-text", TextArea).text.strip()
                from character_manager import write_chara_metadata
                success = write_chara_metadata(card_path, metadata_str)
                if success:
                    self.app.notify(f"Successfully updated {Path(card_path).name}")
                else:
                    self.app.notify("Failed to write metadata!", severity="error")
            else:
                self.app.notify("Select a card first!", severity="warning")
        elif event.button.id == "btn-cancel-mgmt":
            self.dismiss(None)

class ParametersScreen(ModalScreen):
    """Modal for adjusting AI generation parameters."""
    def compose(self) -> ComposeResult:
        # Fetch current values from the app
        app = self.app
        yield Vertical(
            Label("AI Parameters", classes="dialog-title"),
            Container(
                Label("Temperature (0.0-2.5)"),
                Input(value=str(app.temp), id="input-temp"),
                classes="setting-group"
            ),
            Container(
                Label("Top P (0.1-1.0)"),
                Input(value=str(app.topp), id="input-topp"),
                classes="setting-group"
            ),
            Container(
                Label("Top K (0-100)"),
                Input(value=str(app.topk), id="input-topk"),
                classes="setting-group"
            ),
            Container(
                Label("Repeat Penalty (0.8-2.0)"),
                Input(value=str(app.repeat), id="input-repeat"),
                classes="setting-group"
            ),
            Container(
                Label("Min P (0.0-1.0)"),
                Input(value=str(app.minp), id="input-minp"),
                classes="setting-group"
            ),
            Horizontal(
                Button("Defaults", variant="default", id="btn-reset-params"),
                Button("Apply", variant="default", id="btn-apply-params"),
                Button("Cancel", variant="default", id="btn-cancel-params"),
                classes="buttons"
            ),
            id="parameters-dialog",
            classes="modal-dialog"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        # We no longer apply changes live to support Cancel behavior
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-reset-params":
            # Just reset the UI fields, don't apply to app yet
            defaults = {
                "temp": 0.8, "topp": 0.9, "topk": 40, "repeat": 1.0, "minp": 0.0
            }
            for attr, val in defaults.items():
                try: self.query_one(f"#input-{attr}", Input).value = str(val)
                except Exception: pass
            self.app.notify("UI values reset. Click Apply to save.")
            
        elif event.button.id == "btn-apply-params":
            # Read from UI and apply to app
            for attr in ["temp", "topp", "topk", "repeat", "minp"]:
                try:
                    val_str = self.query_one(f"#input-{attr}", Input).value
                    if attr == "topk": val = int(val_str)
                    else: val = float(val_str)
                    setattr(self.app, attr, val)
                except Exception: pass
            
            if hasattr(self.app, "save_user_settings"):
                self.app.save_user_settings()
            self.app.notify("Parameters applied and saved.")
            self.dismiss()

        elif event.button.id == "btn-cancel-params":
            self.dismiss()

class AboutScreen(ModalScreen):
    """About / Utility modal screen."""
    def on_mount(self) -> None:
        # Focus the title so no buttons are highlighted by default
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("About aiMultiFool", classes="dialog-title"),
            Vertical(
                Button("Context Window", id="btn-about-context", variant="default", classes="about-btn"),
                Button("aiMultiFool Website", id="btn-about-website", variant="default", classes="about-btn"),
                Button("aiMultiFool Discord", id="btn-about-discord", variant="default", classes="about-btn"),
                Button("Buy me a Coffee", id="btn-about-coffee", variant="default", classes="about-btn"),
                classes="about-buttons-list"
            ),
            Horizontal(
                Button("Close", variant="default", id="btn-close-about"),
                classes="buttons"
            ),
            id="about-dialog",
            classes="modal-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-about":
            self.dismiss()
        elif event.button.id == "btn-about-context":
            self.dismiss() # Dismiss about first
            from widgets import ContextWindowScreen
            self.app.push_screen(ContextWindowScreen(self.app.messages))
        elif event.button.id == "btn-about-discord":
            webbrowser.open("https://discord.com/invite/J5vzhbmk35")
        elif event.button.id == "btn-about-website":
            webbrowser.open("https://aimultifool.com/")
        elif event.button.id == "btn-about-coffee":
            webbrowser.open("https://ko-fi.com/aimultifool")

class ActionsManagerScreen(ModalScreen):
    """Integrated Action Management Screen."""
    current_data_idx: int = -1 # Explicitly type-hinted for clarity

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        self.current_data_idx = -1 # Reset on mount
        self.refresh_action_list()

    def compose(self) -> ComposeResult:
        # Clean and sort data immediately so we can populate the Select
        # ensuring it is never empty to prevent EmptySelectError
        if hasattr(self.app, "action_menu_data"):
             for item in self.app.action_menu_data:
                name = item.get("itemName", "")
                if ":" in name:
                    parts = name.split(":", 1)
                    item["category"] = parts[0].strip()
                    item["itemName"] = parts[1].strip()
                elif "category" not in item:
                    item["category"] = "Other"
             
             self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("itemName", "").lower()))
        
        # Build options
        cats = set()
        if hasattr(self.app, "action_menu_data"):
            for act in self.app.action_menu_data:
                cats.add(act.get('category', 'Other'))
        
        options = [(c, c) for c in sorted(list(cats))]
        if not options:
            options = [("Other", "Other")]
            
        default_val = options[0][1]

        yield Vertical(
            Label("Action Management", classes="dialog-title"),
            Horizontal(
                Vertical(
                    Label("Filter Category", classes="label"),
                    Select(options, id="select-mgmt-filter", allow_blank=False, value=default_val),
                    Label("Actions", classes="label"),
                    ListView(id="list-actions-mgmt"),
                    classes="pane-left"
                ),
                Vertical(
                    Label("Edit Action", classes="label"),
                    Label("Category", classes="label"),
                    Input(id="input-action-category"),
                    Label("Item Name", classes="label"),
                    Input(id="input-action-name"),
                    Label("Prompt", classes="label"),
                    TextArea(id="input-action-prompt"),
                    Label("Action Type", classes="label"),
                    Select([("Regular Action / User", "false"), ("System Prompt", "true")], id="select-action-type", allow_blank=False, value="false"),
                    classes="pane-right"
                ),
                id="management-split"
            ),
            Horizontal(
                Button("Add New", variant="default", id="btn-add-action-mgmt"),
                Button("Duplicate", variant="default", id="btn-duplicate-action-mgmt"),
                Button("Delete", variant="error", id="btn-delete-action-mgmt"),
                Button("Close", variant="default", id="btn-close-action-mgmt"),
                classes="buttons"
            ),
            id="actions-dialog",
            classes="modal-dialog"
        )

    def refresh_action_list(self) -> None:
        lv = self.query_one("#list-actions-mgmt", ListView)
        lv.clear()
        
        # Get filter value
        filter_cat = None
        try:
            sel = self.query_one("#select-mgmt-filter", Select)
            if sel.value != Select.BLANK:
                filter_cat = sel.value
        except Exception:
            pass

        actions = self.app.action_menu_data
        for idx, act in enumerate(actions):
            cat = act.get('category', 'Other')
            if filter_cat and cat != filter_cat:
                continue
            
            display_name = act.get('itemName', '???')
            if ":" in display_name:
                display_name = display_name.split(":", 1)[1].strip()
            
            lv.append(ListItem(Label(f"[{cat}] {display_name}"), name=str(idx)))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-mgmt-filter":
            self.refresh_action_list()
            # After refreshing, the previously selected item might not exist or be at a new index.
            # Clear the edit fields and reset current_data_idx.
            self.current_data_idx = -1
            self.query_one("#input-action-category", Input).value = ""
            self.query_one("#input-action-name", Input).value = ""
            self.query_one("#input-action-prompt", TextArea).text = ""
            self.query_one("#select-action-type", Select).value = "false"
        elif event.select.id == "select-action-type":
             if self.current_data_idx >= 0:
                self.save_current_edit()


    # on_show logic moved to on_mount

    def update_filter_options(self) -> None:
        sel = self.query_one("#select-mgmt-filter", Select)
        current_val = sel.value
        
        # Populate category filter
        cats = set()
        for act in self.app.action_menu_data:
            cats.add(act.get('category', 'Other'))
        
        options = [(c, c) for c in sorted(list(cats))]
        sel.set_options(options)
        
        # Restore selection if it still exists
        if current_val != Select.BLANK and any(current_val == o[1] for o in options):
            sel.value = current_val
        elif options:
            sel.value = options[0][1]

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in ["input-action-category", "input-action-name"]:
            if self.current_data_idx >= 0:
                self.save_current_edit()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "input-action-prompt":
            if self.current_data_idx >= 0:
                self.save_current_edit()

    def save_current_edit(self) -> None:
        idx = self.current_data_idx
        if idx < 0: return
        
        try:
            category = self.query_one("#input-action-category", Input).value.strip()
            item_name = self.query_one("#input-action-name", Input).value.strip()
            prompt = self.query_one("#input-action-prompt", TextArea).text
            is_system_val = self.query_one("#select-action-type", Select).value
            is_system = (is_system_val == "true")
            
            self.app.action_menu_data[idx]['category'] = category
            self.app.action_menu_data[idx]['itemName'] = item_name
            self.app.action_menu_data[idx]['prompt'] = prompt
            self.app.action_menu_data[idx]['isSystem'] = is_system
            save_action_menu_data(self.app.action_menu_data)
            
            # Update list label without full refresh to avoid focus/scroll jumps
            lv = self.query_one("#list-actions-mgmt", ListView)
            for child in lv.children:
                if getattr(child, "name", "") == str(idx):
                    child.query_one(Label).update(f"[{category}] {item_name}")
                    break
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "list-actions-mgmt":
            if event.item:
                idx_str = getattr(event.item, "name", "-1")
                try:
                    self.current_data_idx = int(idx_str)
                    if self.current_data_idx >= 0 and self.current_data_idx < len(self.app.action_menu_data):
                        act = self.app.action_menu_data[self.current_data_idx]
                        
                        act_name = act.get('itemName', '')
                        if ":" in act_name:
                            act_name = act_name.split(":", 1)[1].strip()
                            
                        self.query_one("#input-action-category", Input).value = act.get('category', 'Other')
                        self.query_one("#input-action-name", Input).value = act_name
                        self.query_one("#input-action-prompt", TextArea).text = act.get('prompt', '')
                        self.query_one("#select-action-type", Select).value = "true" if act.get('isSystem', False) else "false"
                    else:
                        self.current_data_idx = -1
                        # Clear fields if index is out of bounds (shouldn't happen with valid name)
                        self.query_one("#input-action-category", Input).value = ""
                        self.query_one("#input-action-name", Input).value = ""
                        self.query_one("#input-action-prompt", TextArea).text = ""
                        self.query_one("#select-action-type", Select).value = "false"
                except ValueError: # if idx_str is not an int
                    self.current_data_idx = -1
                    self.query_one("#input-action-category", Input).value = ""
                    self.query_one("#input-action-name", Input).value = ""
                    self.query_one("#input-action-prompt", TextArea).text = ""
                    self.query_one("#select-action-type", Select).value = "false"
            else:
                self.current_data_idx = -1
                self.query_one("#input-action-category", Input).value = ""
                self.query_one("#input-action-name", Input).value = ""
                self.query_one("#input-action-prompt", TextArea).text = ""
                self.query_one("#select-action-type", Select).value = "false"

    def select_item_by_data_index(self, data_idx: int) -> None:
        """Helper to reliably select a list item after a refresh."""
        if data_idx < 0: return
        lv = self.query_one("#list-actions-mgmt", ListView)
        items = list(lv.query(ListItem))
        for i, item in enumerate(items):
            if getattr(item, "name", "") == str(data_idx):
                lv.index = i
                self.current_data_idx = data_idx
                # Force sync fields
                act = self.app.action_menu_data[data_idx]
                
                # Strip colon for display if still present
                act_name = act.get('itemName', '')
                if ":" in act_name:
                    act_name = act_name.split(":", 1)[1].strip()
                
                self.query_one("#input-action-category", Input).value = act.get('category', 'Other')
                self.query_one("#input-action-name", Input).value = act_name
                self.query_one("#input-action-prompt", TextArea).text = act.get('prompt', '')
                self.query_one("#select-action-type", Select).value = "true" if act.get('isSystem', False) else "false"
                break
        lv.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-action-mgmt":
            self.dismiss()
        elif event.button.id == "btn-add-action-mgmt":
            # Get current filter category
            sel = self.query_one("#select-mgmt-filter", Select)
            cat = "custom"
            if sel.value != Select.BLANK:
                cat = str(sel.value)
            
            name = "new action"
            
            # Auto-detect system prompt category
            is_system = False
            if "system" in cat.lower():
                is_system = True
                
            new_act = {"category": cat, "itemName": name, "prompt": "Your instruction here...", "isSystem": is_system}
            self.app.action_menu_data.append(new_act)
            
            # Sort after adding: Category then Name
            self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("itemName", "").lower()))
            
            save_action_menu_data(self.app.action_menu_data)
            self.update_filter_options()
            self.refresh_action_list()
            self.app.notify(f"New action added to {cat}.")
            
            # Find the new index of the added item using identity 'is'
            new_idx = -1
            for i, act in enumerate(self.app.action_menu_data):
                if act is new_act:
                    new_idx = i
                    break
            
            if new_idx != -1:
                # Use a small timer to allow the ListView to fully mount the new items
                self.set_timer(0.1, lambda: self.select_item_by_data_index(new_idx))

        
        elif event.button.id == "btn-delete-action-mgmt":
            idx = self.current_data_idx
            if idx >= 0:
                try:
                    del self.app.action_menu_data[idx]
                    self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("itemName", "").lower()))
                    save_action_menu_data(self.app.action_menu_data)
                    self.update_filter_options()
                    self.refresh_action_list()
                    self.app.notify("Action deleted.")
                    self.current_data_idx = -1
                except Exception as e:
                    self.app.notify(f"Delete error: {e}", severity="error")
                # Reset inputs if list empty
                if not self.app.action_menu_data:
                    self.query_one("#input-action-category", Input).value = ""
                    self.query_one("#input-action-name", Input).value = ""
                    self.query_one("#input-action-prompt", TextArea).text = ""

        elif event.button.id == "btn-duplicate-action-mgmt":
            if self.current_data_idx >= 0:
                try:
                    orig_act = self.app.action_menu_data[self.current_data_idx]
                    
                    # Create copy
                    new_act = orig_act.copy()
                    base_name = new_act.get('itemName', 'Action')
                    
                    # Remove existing suffix if it matches _\d+
                    import re
                    clean_name = re.sub(r'_\d+$', '', base_name)
                    
                    # Find next increment
                    existing_names = [a.get('itemName', '') for a in self.app.action_menu_data]
                    counter = 1
                    new_name = f"{clean_name}_{counter}"
                    while new_name in existing_names:
                        counter += 1
                        new_name = f"{clean_name}_{counter}"
                    
                    new_act['itemName'] = new_name
                    self.app.action_menu_data.append(new_act)
                    
                    # Sort after duplicating: Category then Name
                    self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("itemName", "").lower()))
                    
                    save_action_menu_data(self.app.action_menu_data)
                    self.update_filter_options()
                    self.refresh_action_list()
                    self.app.notify(f"Duplicated to: {new_name}")
                    
                    # Find the new index using identity 'is'
                    new_idx = -1
                    for i, act in enumerate(self.app.action_menu_data):
                        if act is new_act:
                            new_idx = i
                            break
                    
                    if new_idx != -1:
                        # Use a small timer to allow the ListView to fully mount the new items
                        self.set_timer(0.1, lambda: self.select_item_by_data_index(new_idx))
                except Exception as e:
                    self.app.notify(f"Duplicate error: {e}", severity="error")

class PasswordPromptScreen(ModalScreen):
    """Modal for entering a password to decrypt a chat."""
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Encrypted Chat Detected", classes="dialog-title"),
            Input(placeholder="Password / Passphrase", id="input-password", password=True),
            Horizontal(
                Button("Unlock & Load", variant="primary", id="btn-unlock"),
                Button("Cancel", variant="default", id="btn-cancel-unlock"),
                classes="buttons"
            ),
            id="password-prompt-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        self.query_one("#input-password").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-password":
            self.action_unlock()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-unlock":
            self.dismiss(None)
        elif event.button.id == "btn-unlock":
            self.action_unlock()

    def action_unlock(self) -> None:
        password = self.query_one("#input-password").value
        if not password:
            self.app.notify("Password required!", severity="warning")
            self.query_one("#input-password").focus()
            return
        
        try:
            with open(self.file_path, "r") as f:
                content = f.read()
            
            # Check if it's already JSON (not encrypted) or needs decryption
            try:
                # If this succeeds, it was NOT encrypted
                messages = json.loads(content)
                self.dismiss(messages)
                return
            except json.JSONDecodeError:
                # Needs decryption
                decrypted_json = decrypt_data(content, password)
                messages = json.loads(decrypted_json)
                self.dismiss(messages)
        except Exception as e:
            self.app.notify(str(e), severity="error")
            self.query_one("#input-password").focus()

class ChatManagerScreen(ModalScreen):
    """Screen for managing saved chats (loading/saving)."""
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Chat Manager - AES-256-GCM + Argon2id", classes="dialog-title"),
            Horizontal(
                Vertical(
                    Label("Saved Chats", classes="label"),
                    ListView(id="list-saved-chats"),
                    classes="pane-left"
                ),
                Vertical(
                    Label("Save Current Chat", classes="label"),
                    Input(placeholder="Filename (optional)...", id="input-save-name"),
                    Label("Password / Passphrase", classes="label"),
                    Input(placeholder="Password / Passphrase (optional)..", id="input-save-password", password=True),
                    Horizontal(
                        Button("Save Current Chat", variant="primary", id="btn-save-chat"),
                        classes="buttons"
                    ),
                    classes="pane-right"
                ),
                id="management-split"
            ),
            Horizontal(
                Button("Load Selected", variant="default", id="btn-load-chat"),
                Button("Delete", variant="error", id="btn-delete-chat"),
                Button("Close", variant="default", id="btn-close-chat"),
                classes="buttons"
            ),
            id="chat-manager-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        self.refresh_chat_list()

    def refresh_chat_list(self) -> None:
        chats_dir = Path(self.app.root_path) / "chats"
        if not chats_dir.exists():
            chats_dir.mkdir(parents=True, exist_ok=True)
        
        lv = self.query_one("#list-saved-chats", ListView)
        lv.clear()
        
        chats = sorted(list(chats_dir.glob("*.json")))
        for chat_file in chats:
            lv.append(ListItem(Label(chat_file.name), name=str(chat_file)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-chat":
            self.dismiss()
        elif event.button.id == "btn-save-chat":
            save_name = self.query_one("#input-save-name", Input).value.strip()
            password = self.query_one("#input-save-password", Input).value
            
            if not save_name:
                import datetime
                save_name = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if not save_name.endswith(".json"):
                save_name += ".json"
            
            chats_dir = Path(self.app.root_path) / "chats"
            file_path = chats_dir / save_name
            
            try:
                chat_data = json.dumps(self.app.messages, indent=2)
                if password:
                    encrypted_data = encrypt_data(chat_data, password)
                    with open(file_path, "w") as f:
                        f.write(encrypted_data)
                    self.app.notify(f"Encrypted chat saved to {save_name}")
                else:
                    with open(file_path, "w") as f:
                        f.write(chat_data)
                    self.app.notify(f"Chat saved to {save_name}")
                self.refresh_chat_list()
                self.query_one("#input-save-password", Input).value = ""
                self.query_one("#input-save-name").focus()
            except Exception as e:
                self.app.notify(f"Error saving chat: {e}", severity="error")

        elif event.button.id == "btn-load-chat":
            selected = self.query_one("#list-saved-chats", ListView).highlighted_child
            if selected:
                file_path = getattr(selected, "name", "")
                if file_path:
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                        
                        try:
                            # Try loading as plain JSON first
                            messages = json.loads(content)
                            self.dismiss({"action": "load", "messages": messages})
                        except json.JSONDecodeError:
                            # If not JSON, it's likely encrypted. Prompt for password.
                            self.app.push_screen(PasswordPromptScreen(file_path), self.password_prompt_callback)
                    except Exception as e:
                        self.app.notify(f"Error loading chat: {e}", severity="error")
                        self.query_one("#list-saved-chats").focus()
            else:
                self.app.notify("Select a chat to load first!", severity="warning")
                self.query_one("#list-saved-chats").focus()

        elif event.button.id == "btn-delete-chat":
            selected = self.query_one("#list-saved-chats", ListView).highlighted_child
            if selected:
                file_path = getattr(selected, "name", "")
                if file_path:
                    try:
                        Path(file_path).unlink()
                        self.app.notify("Chat deleted.")
                        self.refresh_chat_list()
                    except Exception as e:
                        self.app.notify(f"Error deleting chat: {e}", severity="error")
            else:
                self.app.notify("Select a chat to delete first!", severity="warning")
            self.query_one("#list-saved-chats").focus()

    def password_prompt_callback(self, messages):
        if messages:
            self.dismiss({"action": "load", "messages": messages})


