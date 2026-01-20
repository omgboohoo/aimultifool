import os

# Disable Qdrant usage reporting for privacy
os.environ["QDRANT__TELEMETRY_DISABLED"] = "true"

import re
import json
import asyncio
import webbrowser
import copy
from pathlib import Path
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Container, Horizontal, Grid, ScrollableContainer
from textual.widgets import Label, Input, Select, Button, ListView, ListItem, Static, TextArea, Checkbox
from textual_slider import Slider
from utils import save_action_menu_data, encrypt_data, decrypt_data, copy_to_clipboard
from character_manager import extract_chara_metadata, write_chara_metadata

class ScaledSlider(Slider):
    """Slider that works with float values by scaling to integers."""
    def __init__(self, min_val: float, max_val: float, step: float, value: float, id: str = None, **kwargs):
        # Scale to integers for the underlying slider
        self.scale_factor = 1.0
        if step < 1.0:
            # Find the scale factor needed to make step an integer
            step_str = f"{step:.10f}".rstrip('0')
            if '.' in step_str:
                decimals = len(step_str.split('.')[1])
                self.scale_factor = 10 ** decimals
            else:
                self.scale_factor = 1.0
        else:
            self.scale_factor = 1.0
        
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        
        # Scale values for integer slider
        scaled_min = int(min_val * self.scale_factor)
        scaled_max = int(max_val * self.scale_factor)
        scaled_step = int(step * self.scale_factor) if step * self.scale_factor >= 1 else 1
        scaled_value = int(value * self.scale_factor)
        
        super().__init__(min=scaled_min, max=scaled_max, step=scaled_step, value=scaled_value, id=id, **kwargs)
    
    @property
    def float_value(self) -> float:
        """Get the actual float value."""
        return self.value / self.scale_factor
    
    @float_value.setter
    def float_value(self, val: float) -> None:
        """Set the float value."""
        scaled = int(val * self.scale_factor)
        self.value = scaled

class GenericPasswordModal(ModalScreen):
    """Generic modal for entering a password."""
    def __init__(self, title="Enter Password", allow_blank=False, **kwargs):
        super().__init__(**kwargs)
        self.dialog_title = title
        self.allow_blank = allow_blank

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.dialog_title, classes="dialog-title"),
            Input(placeholder="Password / Passphrase", id="input-generic-password"),
            Horizontal(
                Button("Confirm", variant="default", id="btn-confirm-pass"),
                Button("Cancel", variant="default", id="btn-cancel-pass"),
                classes="buttons"
            ),
            id="password-prompt-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        self.query_one("#input-generic-password").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_confirm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-pass":
            self.dismiss(None)
        elif event.button.id == "btn-confirm-pass":
            self.action_confirm()

    def action_confirm(self) -> None:
        password = self.query_one("#input-generic-password").value
        if not password and not self.allow_blank:
            self.app.notify("Password required!", severity="warning")
            self.query_one("#input-generic-password").focus()
            return
        self.dismiss(password)

class FileNamePrompt(ModalScreen):
    """Modal to ask for a new file name."""
    def __init__(self, initial_value: str = "", prompt_text: str = "Enter filename:"):
        super().__init__()
        self.initial_value = initial_value
        self.prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        with Vertical(id="name-prompt-dialog", classes="modal-dialog"):
            yield Label(self.prompt_text, classes="dialog-title")
            yield Input(value=self.initial_value, id="filename-input")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Confirm", id="btn-confirm", variant="default")

    def on_mount(self) -> None:
        self.query_one("#filename-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            val = self.query_one("#filename-input", Input).value
            self.dismiss(val)
        else:
            self.dismiss(None)

class CategoryNamePrompt(ModalScreen):
    """Modal to ask for a new category name."""
    def __init__(self, existing_categories: list[str] = None):
        super().__init__()
        self.existing_categories = existing_categories or []

    def compose(self) -> ComposeResult:
        with Vertical(id="category-prompt-dialog", classes="modal-dialog"):
            yield Label("Enter Category Name", classes="dialog-title")
            yield Input(placeholder="Category name", id="category-input")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="btn-cancel-cat", variant="default")
                yield Button("Confirm", id="btn-confirm-cat", variant="default")

    def on_mount(self) -> None:
        self.query_one("#category-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_confirm()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-cat":
            self.action_confirm()
        else:
            self.dismiss(None)

    def action_confirm(self) -> None:
        category_name = self.query_one("#category-input", Input).value.strip()
        if not category_name:
            self.app.notify("Category name cannot be empty!", severity="warning")
            self.query_one("#category-input").focus()
            return
        
        # Check for duplicates
        if category_name in self.existing_categories:
            self.app.notify(f"Category '{category_name}' already exists!", severity="warning")
            self.query_one("#category-input").focus()
            return
        
        self.dismiss(category_name)

class SaveChatPrompt(ModalScreen):
    """Modal to ask for filename and password when saving a chat."""
    def compose(self) -> ComposeResult:
        with Vertical(id="save-chat-prompt-dialog", classes="modal-dialog"):
            yield Label("Save Current Chat", classes="dialog-title")
            yield Label("Filename (optional)", classes="label")
            yield Input(placeholder="Filename (optional)...", id="filename-input")
            yield Label("Password / Passphrase (optional)", classes="label")
            yield Input(placeholder="Password / Passphrase (optional)...", id="password-input", password=False)
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="btn-cancel-save", variant="default")
                yield Button("Save", id="btn-confirm-save", variant="default")
    
    def on_mount(self) -> None:
        self.query_one("#filename-input").focus()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filename-input":
            self.query_one("#password-input").focus()
        elif event.input.id == "password-input":
            self.action_save()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-save":
            self.action_save()
        else:
            self.dismiss(None)
    
    def action_save(self) -> None:
        filename = self.query_one("#filename-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value
        self.dismiss({"filename": filename, "password": password})

class ConfirmationModal(ModalScreen):
    """Generic confirmation modal for yes/no questions."""
    def __init__(self, title: str = "Confirm", message: str = "Are you sure?", **kwargs):
        super().__init__(**kwargs)
        self.dialog_title = title
        self.message = message

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.dialog_title, classes="dialog-title"),
            Label(self.message, classes="dialog-subtitle"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel-confirm"),
                Button("Confirm", variant="default", id="btn-confirm-confirm"),
                classes="buttons"
            ),
            id="confirmation-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

class FilePickerModal(ModalScreen):
    """Modal for selecting a file from a directory."""
    def __init__(self, directory: Path, file_extension: str = ".json", **kwargs):
        super().__init__(**kwargs)
        self.directory = directory
        self.file_extension = file_extension

    def compose(self) -> ComposeResult:
        # Show relative path or just folder name
        try:
            rel_path = self.directory.relative_to(Path(__file__).parent)
            display_path = f"export/{rel_path.name}" if rel_path != Path(".") else "export"
        except:
            display_path = str(self.directory.name) if self.directory.name else "export"
        
        yield Vertical(
            Label("Select File to Import", classes="dialog-title"),
            Label(f"Files in: {display_path}", classes="dialog-subtitle"),
            ListView(id="list-files"),
            Horizontal(
                Button("Cancel", variant="default", id="btn-cancel-file"),
                Button("Select", variant="default", id="btn-select-file", disabled=True),
                classes="buttons"
            ),
            id="file-picker-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        self.refresh_file_list()

    def refresh_file_list(self) -> None:
        """Populate the file list with JSON files from the export directory."""
        lv = self.query_one("#list-files", ListView)
        lv.clear()
        
        if not self.directory.exists():
            lv.append(ListItem(Label("Export folder does not exist.")))
            return
        
        # Get all JSON files
        json_files = sorted(self.directory.glob(f"*{self.file_extension}"))
        
        if not json_files:
            lv.append(ListItem(Label("No JSON files found in export folder.")))
            return
        
        for file_path in json_files:
            lv.append(ListItem(Label(file_path.name), name=str(file_path)))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Enable/disable Select button based on selection."""
        try:
            has_selection = event.item is not None
            self.query_one("#btn-select-file", Button).disabled = not has_selection
        except Exception:
            pass
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle double-click or Enter key selection."""
        try:
            if event.item:
                file_path = getattr(event.item, "name", None)
                if file_path:
                    self.dismiss(file_path)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-file":
            self.dismiss(None)
        elif event.button.id == "btn-select-file":
            try:
                lv = self.query_one("#list-files", ListView)
                if lv.highlighted_child:
                    file_path = getattr(lv.highlighted_child, "name", None)
                    if file_path:
                        self.dismiss(file_path)
                    else:
                        self.dismiss(None)
                else:
                    self.dismiss(None)
            except Exception:
                self.dismiss(None)

def create_styled_text(text, speech_styling="highlight", highlight_color=None):
    """Create a rich renderable with styled quoted text
    
    Args:
        text: The text to style
        speech_styling: One of "none", "inversed", or "highlight"
        highlight_color: The highlight color to use (for "highlight" mode)
    """
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
            # Apply styling based on speech_styling mode
            if speech_styling == "none":
                # No special styling, just bold italic
                styled_text = Text(part_text, style="bold italic")
            elif speech_styling == "inversed":
                # Use Rich's "reverse" style (swaps fg/bg)
                styled_text = Text(part_text, style="bold italic reverse")
            elif speech_styling == "highlight" and highlight_color:
                # Use the actual selection/highlight color from the theme
                styled_text = Text(part_text, style=f"bold italic on {highlight_color}")
            else:
                # Fallback: use reverse if highlight color not available
                styled_text = Text(part_text, style="bold italic reverse")
            renderables.append(styled_text)
        else:
            if part_text:
                # Regular text: no background, just normal
                renderables.append(Text(part_text))
    
    if len(renderables) == 1:
        return renderables[0]
    return Text.assemble(*renderables)

class MessageWidget(Static):
    """A widget to display a single chat message."""
    def __init__(self, role: str, content: str, user_name: str = "User", is_info: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.user_name = user_name
        self.is_info = is_info

    def on_mount(self):
        if self.role == "user":
            self.add_class("-user")
        elif self.role == "system":
            self.add_class("-system")
        else:
            self.add_class("-assistant")

    def render(self):
        if self.role == "user":
            return Text(self.content, style="bold")
        elif self.role == "system":
            return Text(self.content, style="italic")
        else:
            # Get speech styling setting from app
            speech_styling = getattr(self.app, "speech_styling", "highlight")
            
            # Get selection/highlight color from Textual (matches text selection color)
            # Only needed if using "highlight" mode
            highlight_color = None
            if speech_styling == "highlight":
                try:
                    # Get the selection style from the screen - this is what TextArea uses for selections
                    # Try multiple ways to access the screen
                    screen = None
                    if hasattr(self, 'screen') and self.screen:
                        screen = self.screen
                    elif hasattr(self, 'app') and self.app and hasattr(self.app, 'screen'):
                        screen = self.app.screen
                    
                    if screen and hasattr(screen, 'get_component_rich_style'):
                        selection_style = screen.get_component_rich_style("screen--selection")
                        if selection_style and hasattr(selection_style, 'bgcolor') and selection_style.bgcolor:
                            # Convert Rich Color to string format for use in style
                            color_obj = selection_style.bgcolor
                            try:
                                from rich.color import Color
                                if isinstance(color_obj, Color):
                                    # Try to get standard color name first
                                    if hasattr(color_obj, 'name') and color_obj.name:
                                        highlight_color = color_obj.name
                                    # Fallback: use color number for 256-color terminals
                                    elif hasattr(color_obj, 'number') and color_obj.number is not None:
                                        highlight_color = f"color({color_obj.number})"
                                    else:
                                        highlight_color = str(color_obj)
                                else:
                                    highlight_color = str(color_obj)
                            except Exception:
                                highlight_color = str(color_obj)
                except Exception:
                    pass
            
            return create_styled_text(self.content, speech_styling=speech_styling, highlight_color=highlight_color)

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
                Select([
                    ("4096", 4096),
                    ("8192 (recommended)", 8192),
                    ("16384", 16384),
                    ("32768", 32768),
                    ("65536", 65536)
                ], id="select-context", value=8192),
                classes="setting-group"
            ),
            Container(
                Label("GPU Layers"),
                Select([("All (-1)", -1), ("CPU Only (0)", 0)] + [(str(x), x) for x in range(8, 129, 8)], id="select-gpu-layers", value=-1),
                classes="setting-group",
                id="gpu-layers-container"
            ),
            Container(
                Label("Ollama Server"),
                Input(placeholder="127.0.0.1:11434", id="input-ollama-url"),
                classes="setting-group",
                id="ollama-url-container"
            ),
            Horizontal(
                Button("Local Inference", variant="default", id="btn-toggle-mode"),
                Button("Test", variant="default", id="btn-connect"),
                Button("Download Models", variant="default", id="btn-download-models"),
                Button("Load Model", variant="default", id="btn-load-model"),
                classes="buttons",
                id="model-buttons-container"
            ),
            id="model-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        # Populate fields from app state
        app = self.app

        # Get inference mode from app (default to "local")
        inference_mode = getattr(app, "inference_mode", "local")
        
        # In local mode, check if models exist and disable Load Model button if none found
        if inference_mode == "local":
            try:
                from ai_engine import get_models
                models = get_models("local")
                load_btn = self.query_one("#btn-load-model", Button)
                load_btn.disabled = len(models) == 0
            except Exception:
                # If check fails, disable button to be safe (user can enable after models are found)
                load_btn = self.query_one("#btn-load-model", Button)
                load_btn.disabled = True
        
        # Update toggle button label to show what it will switch to
        toggle_btn = self.query_one("#btn-toggle-mode", Button)
        if inference_mode == "ollama":
            toggle_btn.label = "Local Inference"
        else:
            toggle_btn.label = "Ollama Inference"
        
        # Show/hide Download Models button (only in local mode)
        download_btn = self.query_one("#btn-download-models", Button)
        if inference_mode == "ollama":
            download_btn.display = False
        else:
            download_btn.display = True
            # Check if default models already exist
            try:
                from pathlib import Path
                models_dir = Path(__file__).parent / "models"
                llm_path = models_dir / "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
                embed_path = models_dir / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
                if llm_path.exists() and embed_path.exists():
                    download_btn.disabled = True
                else:
                    download_btn.disabled = False
            except Exception:
                # If check fails, leave button enabled (fallback)
                download_btn.disabled = False
        
        # Show/hide GPU Layers and Ollama URL based on inference mode
        gpu_container = self.query_one("#gpu-layers-container", Container)
        ollama_url_container = self.query_one("#ollama-url-container", Container)
        model_dialog = self.query_one("#model-dialog", Vertical)
        connect_btn = self.query_one("#btn-connect", Button)
        
        # Check if CPU mode is enabled
        cpu_mode = getattr(app, "cpu_mode", False)
        
        if inference_mode == "ollama":
            gpu_container.display = False
            ollama_url_container.display = True
            model_dialog.add_class("ollama-mode")
            connect_btn.display = True
        else:
            # Hide GPU layers container if CPU mode is enabled
            if cpu_mode:
                gpu_container.display = False
                # Force GPU layers to 0 in CPU mode
                app.gpu_layers = 0
            else:
                gpu_container.display = True
            ollama_url_container.display = False
            model_dialog.remove_class("ollama-mode")
            connect_btn.display = False

        # Validate and set Context Size
        try:
            self.query_one("#select-context").value = app.context_size
        except Exception:
            self.query_one("#select-context").value = 4096

        # Validate and set GPU Layers (only for local mode and not CPU mode)
        if inference_mode != "ollama" and not cpu_mode:
            # Ensure GPU layers defaults to -1 (all GPU layers) if it's 0
            gpu_layers_value = app.gpu_layers if app.gpu_layers != 0 else -1
            if app.gpu_layers == 0:
                app.gpu_layers = -1  # Update app state to match
            try:
                self.query_one("#select-gpu-layers").value = gpu_layers_value
            except Exception:
                self.query_one("#select-gpu-layers").value = -1
        
        # Validate and set Ollama URL (only for ollama mode)
        if inference_mode == "ollama":
            try:
                ollama_url = getattr(app, "ollama_url", None)
                if not ollama_url or ollama_url.strip() == "":
                    ollama_url = "127.0.0.1:11434"
                    app.ollama_url = ollama_url
                self.query_one("#input-ollama-url").value = ollama_url
            except Exception:
                self.query_one("#input-ollama-url").value = "127.0.0.1:11434"
        
        # Populate models based on inference mode
        self._populate_models(inference_mode)
        
        # Explicitly set Load Model button state after population
        # This ensures the button is enabled if models were found
        try:
            from ai_engine import get_models
            models = get_models(inference_mode)
            has_models = len(models) > 0
            load_btn = self.query_one("#btn-load-model", Button)
            load_btn.disabled = not has_models
        except Exception:
            # If we can't check, leave button as-is (should be enabled by default)
            pass
        
        self.app.update_ui_state()
        
        # Check download button state after update_ui_state (to avoid reset)
        if inference_mode != "ollama":
            download_btn = self.query_one("#btn-download-models", Button)
            try:
                from pathlib import Path
                models_dir = Path(__file__).parent / "models"
                llm_path = models_dir / "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
                embed_path = models_dir / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
                if llm_path.exists() and embed_path.exists():
                    download_btn.disabled = True
                else:
                    download_btn.disabled = False
            except Exception:
                download_btn.disabled = False
        
        # Ensure mod switch button is always enabled
        toggle_btn = self.query_one("#btn-toggle-mode", Button)
        toggle_btn.disabled = False
    
    def _populate_models(self, inference_mode: str):
        """Populate model list based on inference mode."""
        from ai_engine import get_models
        from ollama_client import get_ollama_models
        app = self.app
        
        try:
            if inference_mode == "ollama":
                # Use ollama_url from app settings
                ollama_url = getattr(app, "ollama_url", "127.0.0.1:11434")
                base_url = f"http://{ollama_url}" if '://' not in ollama_url else ollama_url
                models = get_ollama_models(base_url)
            else:
                models = get_models(inference_mode)
            select_model = self.query_one("#select-model", Select)
            select_context = self.query_one("#select-context", Select)
            select_gpu_layers = self.query_one("#select-gpu-layers", Select)
            
            # Check if we have any models
            has_models = len(models) > 0
            
            if has_models:
                if inference_mode == "ollama":
                    # Ollama models are strings
                    options = [(m, m) for m in models]
                else:
                    # Local models are Path objects
                    options = [(m.name, str(m)) for m in models]
                
                select_model.set_options(options)
                
                # Try to restore selected model
                if app.selected_model:
                    try:
                        if any(opt[1] == app.selected_model for opt in options):
                            select_model.value = app.selected_model
                        elif options:
                            select_model.value = options[0][1]
                    except Exception:
                        if options:
                            select_model.value = options[0][1]
                elif options:
                    select_model.value = options[0][1]
                
                # Enable controls when models are available
                select_model.disabled = False
                select_context.disabled = False
                if inference_mode != "ollama":
                    select_gpu_layers.disabled = False
                
                # Enable Load Model button when models are available
                try:
                    load_btn = self.query_one("#btn-load-model", Button)
                    load_btn.disabled = False
                except Exception:
                    pass
            else:
                # No models available - disable controls
                select_model.set_options([])
                select_model.disabled = True
                select_context.disabled = True
                select_gpu_layers.disabled = True
                
                # Disable Load Model button when no models available
                try:
                    load_btn = self.query_one("#btn-load-model", Button)
                    load_btn.disabled = True
                except Exception:
                    pass
                
                # Show helpful message
                if inference_mode == "ollama":
                    app.notify("No Ollama models found. Make sure Ollama is running and models are installed.", severity="warning")
                else:
                    app.notify("No local models found. Click 'Download Default Models' to get started.", severity="information")
        except Exception as e:
            app.notify(f"Error loading models: {e}", severity="error")
            select_model = self.query_one("#select-model", Select)
            select_context = self.query_one("#select-context", Select)
            select_gpu_layers = self.query_one("#select-gpu-layers", Select)
            select_model.set_options([])
            select_model.disabled = True
            select_context.disabled = True
            select_gpu_layers.disabled = True
            
            # Disable Load Model button on error
            try:
                load_btn = self.query_one("#btn-load-model", Button)
                load_btn.disabled = True
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle-mode":
            # Toggle between local and ollama mode
            app = self.app
            current_mode = getattr(app, "inference_mode", "local")
            new_mode = "ollama" if current_mode == "local" else "local"
            
            # If switching to local mode, always try to unload Ollama models
            if new_mode == "local":
                # First, unload any model we have a reference to
                if hasattr(app, "llm") and app.llm is not None:
                    try:
                        if hasattr(app.llm, "unload"):
                            app.llm.unload()
                        elif hasattr(app.llm, "close"):
                            app.llm.close()
                    except Exception:
                        pass
                    app.llm = None
                    import gc
                    gc.collect()
                
                # Proactively unload any Ollama models that might be loaded from previous runs
                try:
                    from devtools.control_ollama import check_ollama_running
                    import requests
                    ollama_url = getattr(app, "ollama_url", "127.0.0.1:11434")
                    base_url = f"http://{ollama_url}" if '://' not in ollama_url else ollama_url
                    if check_ollama_running(base_url):
                        # Get list of available models
                        response = requests.get(f"{base_url}/api/tags", timeout=2)
                        if response.status_code == 200:
                            data = response.json()
                            models = data.get("models", [])
                            # Try to unload each model (Ollama keeps models in memory)
                            for model_info in models:
                                model_name = model_info.get("name", "")
                                if model_name and "embed" not in model_name.lower() and "nomic" not in model_name.lower():
                                    try:
                                        # Unload by calling generate with keep_alive=0
                                        requests.post(
                                            f"{base_url}/api/generate",
                                            json={"model": model_name, "prompt": "", "keep_alive": "0"},
                                            timeout=2
                                        )
                                    except Exception:
                                        pass  # Best effort - ignore errors
                except Exception:
                    pass  # If Ollama isn't running or we can't connect, that's fine
                
                app.status_text = "Ready"
                app.notify("Ollama models unloaded from GPU. GPU resources should be available.", severity="information")
            
            # Update app state
            app.inference_mode = new_mode
            
            # Save Ollama URL if switching to Ollama mode
            if new_mode == "ollama":
                try:
                    ollama_url = self.query_one("#input-ollama-url").value.strip()
                    if ollama_url:
                        app.ollama_url = ollama_url
                except Exception:
                    pass
            
            # Save the mode change to settings
            if hasattr(app, "save_user_settings"):
                app.save_user_settings()
            
            # Update button label to show what it will switch to
            toggle_btn = self.query_one("#btn-toggle-mode", Button)
            if new_mode == "ollama":
                toggle_btn.label = "Local Inference"
            else:
                toggle_btn.label = "Ollama Inference"
            # Mod switch button is always enabled
            toggle_btn.disabled = False
            
            # Show/hide Download Models button (only in local mode)
            download_btn = self.query_one("#btn-download-models", Button)
            if new_mode == "ollama":
                download_btn.display = False
            else:
                download_btn.display = True
                # Check if default models already exist
                try:
                    from pathlib import Path
                    models_dir = Path(__file__).parent / "models"
                    llm_path = models_dir / "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
                    embed_path = models_dir / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
                    if llm_path.exists() and embed_path.exists():
                        download_btn.disabled = True
                    else:
                        download_btn.disabled = False
                except Exception:
                    # If check fails, leave button enabled (fallback)
                    download_btn.disabled = False
            
            # Show/hide GPU Layers and Ollama URL based on inference mode
            gpu_container = self.query_one("#gpu-layers-container", Container)
            ollama_url_container = self.query_one("#ollama-url-container", Container)
            model_dialog = self.query_one("#model-dialog", Vertical)
            connect_btn = self.query_one("#btn-connect", Button)
            
            # Check if CPU mode is enabled
            cpu_mode = getattr(app, "cpu_mode", False)
            
            if new_mode == "ollama":
                gpu_container.display = False
                ollama_url_container.display = True
                model_dialog.add_class("ollama-mode")
                connect_btn.display = True
                # Ensure Ollama URL input is populated with default if empty
                try:
                    ollama_url = getattr(app, "ollama_url", None)
                    if not ollama_url or ollama_url.strip() == "":
                        ollama_url = "127.0.0.1:11434"
                        app.ollama_url = ollama_url
                    self.query_one("#input-ollama-url").value = ollama_url
                except Exception:
                    self.query_one("#input-ollama-url").value = "127.0.0.1:11434"
            else:
                # Hide GPU layers container if CPU mode is enabled
                if cpu_mode:
                    gpu_container.display = False
                    # Force GPU layers to 0 in CPU mode
                    app.gpu_layers = 0
                else:
                    gpu_container.display = True
                ollama_url_container.display = False
                model_dialog.remove_class("ollama-mode")
                connect_btn.display = False
            
            # Repopulate models
            self._populate_models(new_mode)
            
            # Show notification
            mode_name = "Ollama" if new_mode == "ollama" else "Local"
            app.notify(f"Switched to {mode_name} mode", severity="information")
        elif event.button.id == "btn-download-models":
            # Trigger download of default models
            app = self.app
            if hasattr(app, "download_default_model"):
                # Disable download button while downloading
                download_btn = self.query_one("#btn-download-models", Button)
                download_btn.disabled = True
                download_btn.label = "Downloading..."
                
                # Also disable the Ollama toggle button while downloading
                toggle_btn = self.query_one("#btn-toggle-mode", Button)
                toggle_btn.disabled = True
                
                # Start download (this is async, so we'll refresh when it completes)
                app.download_default_model()
                app.notify("Downloading default models...", severity="information")
                
                # Set up a timer to check for completion and refresh model list
                def check_download_complete():
                    if not app.is_downloading:
                        # Download completed, refresh model list
                        inference_mode = getattr(app, "inference_mode", "local")
                        self._populate_models(inference_mode)
                        download_btn.label = "Download Models"
                        # Check if models exist and disable if they do
                        from pathlib import Path
                        models_dir = Path(__file__).parent / "models"
                        llm_path = models_dir / "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
                        embed_path = models_dir / "nomic-embed-text-v2-moe.Q4_K_M.gguf"
                        if llm_path.exists() and embed_path.exists():
                            download_btn.disabled = True
                        else:
                            download_btn.disabled = False
                        download_btn.label = "Download Default Models"
                        
                        # Restore GPU container visibility based on CPU mode (only in local mode)
                        if inference_mode == "local":
                            cpu_mode = getattr(app, "cpu_mode", False)
                            gpu_container = self.query_one("#gpu-layers-container", Container)
                            if cpu_mode:
                                gpu_container.display = False
                                # Force GPU layers to 0 in CPU mode
                                app.gpu_layers = 0
                            else:
                                gpu_container.display = True
                        
                        # Re-enable the Ollama toggle button after download completes
                        toggle_btn.disabled = False
                    else:
                        # Still downloading, check again in 0.5 seconds
                        self.set_timer(0.5, check_download_complete)
                
                self.set_timer(0.5, check_download_complete)
            else:
                app.notify("Download functionality not available", severity="error")
        elif event.button.id == "btn-connect":
            # Test connection to Ollama server
            app = self.app
            try:
                ollama_url = self.query_one("#input-ollama-url").value.strip()
                if not ollama_url:
                    ollama_url = getattr(app, "ollama_url", "127.0.0.1:11434")
                
                # Format URL properly
                base_url = f"http://{ollama_url}" if '://' not in ollama_url else ollama_url
                
                # Test connection
                from devtools.control_ollama import check_ollama_running
                connect_btn = self.query_one("#btn-connect", Button)
                connect_btn.disabled = True
                connect_btn.label = "Testing..."
                
                is_connected = check_ollama_running(base_url)
                
                if is_connected:
                    # Try to get model list to verify full functionality
                    import requests
                    try:
                        response = requests.get(f"{base_url}/api/tags", timeout=2)
                        if response.status_code == 200:
                            data = response.json()
                            models = data.get("models", [])
                            model_count = len(models)
                            app.notify(f"✓ Connected to Ollama! Found {model_count} model(s).", severity="success")
                            # Save the URL if connection successful
                            app.ollama_url = ollama_url
                            if hasattr(app, "save_user_settings"):
                                app.save_user_settings()
                            # Refresh model list
                            self._populate_models("ollama")
                        else:
                            app.notify(f"⚠ Connected but got unexpected response: {response.status_code}", severity="warning")
                    except Exception as e:
                        app.notify(f"⚠ Connected but error fetching models: {e}", severity="warning")
                else:
                    app.notify(f"✗ Failed to connect to Ollama at {base_url}", severity="error")
                
                connect_btn.label = "Test"
                connect_btn.disabled = False
            except Exception as e:
                app.notify(f"Error testing connection: {e}", severity="error")
                connect_btn = self.query_one("#btn-connect", Button)
                connect_btn.label = "Test"
                connect_btn.disabled = False
        elif event.button.id == "btn-load-model":
            try:
                model_path = self.query_one("#select-model").value
                ctx = int(self.query_one("#select-context").value)
                
                # Get current inference mode
                inference_mode = getattr(self.app, "inference_mode", "local")
                
                # Save Ollama URL if in Ollama mode
                if inference_mode == "ollama":
                    try:
                        ollama_url = self.query_one("#input-ollama-url").value.strip()
                        if ollama_url:
                            self.app.ollama_url = ollama_url
                            if hasattr(self.app, "save_user_settings"):
                                self.app.save_user_settings()
                    except Exception:
                        pass
                
                # GPU layers only apply to local mode
                if inference_mode == "ollama":
                    gpu = 0  # Not used for Ollama, but keep for compatibility
                else:
                    gpu = int(self.query_one("#select-gpu-layers").value)
                
                self.dismiss({
                    "action": "load",
                    "model_path": model_path,
                    "ctx": ctx,
                    "gpu": gpu,
                    "inference_mode": inference_mode
                })
            except Exception as e:
                self.app.notify(f"Error gathering settings: {e}", severity="error")
        
        # Focus title after button press (except for buttons that dismiss)
        if event.button.id not in ["btn-load-model"]:
            self.query_one(".dialog-title").focus()
        # btn-load-model is handled by the main app via bubbling or we delegate it here?
        # Standard pattern in this app is bubbling for main actions, but we need to ensure the app can read values.
        # Since on_select_changed updates app state, bubbling is fine IF app reads from app state, not widgets.


class ContextWindowScreen(ModalScreen):
    """Screen for showing the current chat context."""
    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()

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
    unsaved_card_path = None  # Track newly created cards that haven't been saved yet
    original_metadata = None  # Track original metadata to detect changes

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        self.last_search_idx = -1
        self.unsaved_card_path = None
        self.original_metadata = None
        self.app.update_ui_state()
        self.refresh_list()
        
        # Disable AI input field initially (no card selected)
        try:
            self.query_one("#ai-meta-input", Input).disabled = True
        except Exception:
            pass
        
        # Welcome message
        history = self.query_one("#ai-meta-history", ScrollableContainer)
        history.mount(Static("Assistant: Hello! I can help you edit character metadata. Ask me to change names, descriptions, or traits.", classes="ai-message"))

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Character Management", classes="dialog-title"),
            Horizontal(
                Vertical(
                    Label("Cards", classes="label"),
                    ListView(id="list-characters"),
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
                Vertical(
                    Label("AI Card Editor", classes="label"),
                    ScrollableContainer(id="ai-meta-history"),
                    Input(placeholder="Ask AI to edit...", id="ai-meta-input"),
                    classes="pane-ai"
                ),
                Vertical(
                    ScrollableContainer(
                        Button("Play - User First", variant="default", id="btn-play-card-user", disabled=True),
                        Button("Play - AI First", variant="default", id="btn-play-card-ai", disabled=True),
                        Button("New", variant="default", id="btn-new-card"),
                        Button("Duplicate", variant="default", id="btn-duplicate-card", disabled=True),
                        Button("Rename", variant="default", id="btn-rename-card", disabled=True),
                        Button("Delete", variant="default", id="btn-delete-card", disabled=True),
                        Button("Save Changes", variant="default", id="btn-save-metadata"),
                        Button("Close", variant="default", id="btn-cancel-mgmt"),
                        id="buttons-scroll"
                    ),
                    classes="pane-buttons"
                ),
                id="management-split"
            ),
            id="characters-dialog",
            classes="modal-dialog"
        )

    def refresh_list(self, select_path: str = None) -> None:
        """Explicitly refresh the character list widget."""
        cards = self.app.get_card_list()
        lv = self.query_one("#list-characters", ListView)
        lv.clear()
        
        target_idx = -1
        for i, card in enumerate(cards):
            card_str = str(card)
            
            # Check for encryption
            is_encrypted = False
            try:
                chara_json = extract_chara_metadata(card_str)
                if chara_json:
                    try:
                        # Attempt to parse as JSON; if it fails, it's probably encrypted base64
                        json.loads(chara_json)
                    except Exception:
                        is_encrypted = True
            except Exception:
                pass
                
            display_name = f"🔒 {card.name}" if is_encrypted else card.name
            lv.append(ListItem(Label(display_name), name=card_str))
            if select_path and card_str == select_path:
                target_idx = i
        
        if target_idx != -1:
            self.force_select_index(target_idx, select_path)
        else:
            # Clear metadata display when nothing is selected
            try:
                self.query_one("#metadata-text", TextArea).text = ""
            except Exception:
                pass
            # Clear unsaved flag and original metadata when nothing is selected
            self.unsaved_card_path = None
            self.original_metadata = None
            
        self.app.update_ui_state()
        self.update_button_states()

    def disable_all_buttons_except_play(self) -> None:
        """Disable all buttons except play buttons (which are already disabled during AI editing)."""
        try:
            self.query_one("#btn-new-card", Button).disabled = True
            self.query_one("#btn-duplicate-card", Button).disabled = True
            self.query_one("#btn-rename-card", Button).disabled = True
            self.query_one("#btn-delete-card", Button).disabled = True
            self.query_one("#btn-save-metadata", Button).disabled = True
            self.query_one("#btn-cancel-mgmt", Button).disabled = True
        except Exception:
            pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle metadata text area changes to enable/disable Save button."""
        if event.text_area.id == "metadata-text":
            self.update_button_states()

    def update_button_states(self) -> None:
        """Update the enabled/disabled state of the buttons based on selection."""
        try:
            list_view = self.query_one("#list-characters", ListView)
            has_selection = list_view.highlighted_child is not None
            
            # Enable/disable AI input field based on selection
            try:
                self.query_one("#ai-meta-input", Input).disabled = not has_selection
            except Exception:
                pass
            
            # Get current selected card path
            current_card_path = None
            if has_selection:
                selected_item = list_view.highlighted_child
                current_card_path = getattr(selected_item, "name", None)
            
            # Check if metadata has been edited
            metadata_changed = False
            if has_selection:
                try:
                    current_text = self.query_one("#metadata-text", TextArea).text
                    # Compare with original metadata (ignore None/empty cases)
                    if self.original_metadata is not None and current_text != self.original_metadata:
                        metadata_changed = True
                except Exception:
                    pass
            
            # Check if this is a newly created card that hasn't been edited
            is_unsaved = current_card_path == self.unsaved_card_path if current_card_path else False
            is_new_unedited = is_unsaved and not metadata_changed
            
            # Play buttons require LLM, selection, and card must be saved (not a new unsaved card)
            # Also disable if it's a new card that hasn't been edited
            can_play = has_selection and self.app.llm and not is_unsaved and not is_new_unedited
            self.query_one("#btn-play-card-user", Button).disabled = not can_play
            self.query_one("#btn-play-card-ai", Button).disabled = not can_play
            # Duplicate button disabled if there are unsaved changes OR if it's a new unedited card
            self.query_one("#btn-duplicate-card", Button).disabled = not has_selection or metadata_changed or is_new_unedited
            # Rename button disabled if there are unsaved changes OR if it's a new unedited card
            self.query_one("#btn-rename-card", Button).disabled = not has_selection or metadata_changed or is_new_unedited
            self.query_one("#btn-delete-card", Button).disabled = not has_selection
            # Save button only enabled if there's a selection AND metadata has been changed
            self.query_one("#btn-save-metadata", Button).disabled = not (has_selection and metadata_changed)
            # Close button is always enabled
            self.query_one("#btn-cancel-mgmt", Button).disabled = False
            # New button is always enabled
            self.query_one("#btn-new-card", Button).disabled = False
        except Exception:
            pass

    @work
    async def force_select_index(self, idx: int, path: str) -> None:
        # Brutal wait to ensure UI is ready
        await asyncio.sleep(0.5)
        lv = self.query_one("#list-characters", ListView)
        lv.index = idx
        lv.focus()
        self.load_metadata(path)

    def load_metadata(self, card_path: str, password_attempt: str = None) -> None:
        """Load character metadata into the editor."""
        if not card_path:
            return
        from character_manager import extract_chara_metadata
        chara_json = extract_chara_metadata(card_path)
        
        loaded_text = None
        if chara_json:
            try:
                # Check for standard JSON first
                parsed = json.loads(chara_json)
                pretty_json = json.dumps(parsed, indent=4)
                self.query_one("#metadata-text", TextArea).text = pretty_json
                loaded_text = pretty_json
            except Exception:
                # Might be encrypted
                if password_attempt:
                     try:
                        decrypted = decrypt_data(chara_json, password_attempt)
                        if decrypted:
                            try:
                                parsed = json.loads(decrypted)
                                pretty_json = json.dumps(parsed, indent=4)
                                self.query_one("#metadata-text", TextArea).text = pretty_json
                                loaded_text = pretty_json
                            except:
                                self.query_one("#metadata-text", TextArea).text = decrypted
                                loaded_text = decrypted
                        else:
                             self.app.notify("Incorrect Password!", severity="error")
                             # Don't clear text to avoid flickers, just maybe show error toast
                     except Exception:
                        self.app.notify("Decryption Failed!", severity="error")
                else:
                    self.query_one("#metadata-text", TextArea).text = "Encrypted Data (Click card in list to Unlock)"
                    loaded_text = "Encrypted Data (Click card in list to Unlock)"
        else:
            self.query_one("#metadata-text", TextArea).text = "No metadata found."
            loaded_text = "No metadata found."
        
        # Store original metadata for change detection
        self.original_metadata = loaded_text
        self.update_button_states()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "list-characters":
            if event.item:
                card_path = getattr(event.item, "name", "")
                self.load_metadata(card_path)
                # Clear unsaved flag if user selects a different card
                if self.unsaved_card_path and self.unsaved_card_path != card_path:
                    self.unsaved_card_path = None
                # original_metadata is reset in load_metadata
            else:
                # No selection - clear original metadata
                self.original_metadata = None
            self.update_button_states()
            
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "list-characters" and event.item:
            # Check if encrypted
            tas = self.query("#metadata-text")
            if not tas: return
            text_area = tas.first()
            if text_area.text.startswith("Encrypted Data"):
                 card_path = getattr(event.item, "name", "")
                 def on_pass(password):
                     if password:
                         self.load_metadata(card_path, password_attempt=password)
                     else:
                         # User cancelled - deselect the card
                         list_view = self.query_one("#list-characters", ListView)
                         list_view.index = None
                         # Clear metadata text
                         self.query_one("#metadata-text", TextArea).text = ""
                         # Update button states to disable play buttons
                         self.update_button_states()
                 
                 self.app.push_screen(GenericPasswordModal(title="Enter Password to Unlock"), on_pass)

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
        elif event.input.id == "ai-meta-input":
            user_text = event.input.value.strip()
            if user_text:
                current_meta = self.query_one("#metadata-text", TextArea).text
                # Disable all buttons when AI starts editing (handled in ask_ai_to_edit)
                self.ask_ai_to_edit(user_text, current_meta)
                event.input.value = ""

    def normalize_metadata_structure(self, metadata_str: str) -> tuple[dict, str]:
        """
        Normalize metadata to ensure it has both top-level fields and a data section.
        Returns (normalized_dict, metadata_for_ai) where metadata_for_ai is the 
        section to send to AI (data section if it exists alone, otherwise full structure).
        """
        try:
            parsed = json.loads(metadata_str)
        except json.JSONDecodeError:
            # If not valid JSON, return as-is wrapped in a dict
            return {"data": {"description": metadata_str}}, metadata_str
        
        # Check if only a data section exists (no top-level character fields)
        has_top_level_fields = any(key in parsed for key in ["name", "description", "personality", "scenario", "first_mes", "mes_example"])
        has_data_section = "data" in parsed and isinstance(parsed["data"], dict)
        
        if has_data_section and not has_top_level_fields:
            # Only data section exists - use it directly for AI
            data_section = parsed["data"]
            # Copy only core character fields to top level (not extensions, etc.)
            core_fields = ["name", "description", "personality", "scenario", "first_mes", "mes_example", "tags"]
            normalized = {
                **{k: v for k, v in data_section.items() if k in core_fields},  # Copy only core fields to top level
                "data": data_section,  # Keep full data section
                "spec": parsed.get("spec", "chara_card_v2"),
                "spec_version": parsed.get("spec_version", "2.0"),
            }
            # Preserve any other top-level fields that might exist
            for key, value in parsed.items():
                if key != "data" and key not in core_fields:
                    normalized[key] = value
            # Use data section directly for AI
            return normalized, json.dumps(data_section, indent=4)
        
        # Ensure data section exists
        if not has_data_section:
            # Create data section from top-level fields
            core_fields = ["name", "description", "personality", "scenario", "first_mes", "mes_example", "tags"]
            data_section = {}
            for field in core_fields:
                if field in parsed:
                    data_section[field] = parsed[field]
            
            # Preserve or create extensions structure
            if "extensions" in parsed and isinstance(parsed["extensions"], dict):
                data_section["extensions"] = parsed["extensions"]
            else:
                data_section["extensions"] = {
                    "talkativeness": parsed.get("talkativeness", "0.5"),
                    "fav": parsed.get("fav", False),
                    "world": parsed.get("world", ""),
                    "depth_prompt": parsed.get("depth_prompt", {"prompt": "", "depth": 4})
                }
            
            # Copy other fields that might be in data section (creator, character_version, etc.)
            optional_data_fields = ["creator", "character_version", "alternate_greetings", "creator_notes", "system_prompt", "post_history_instructions"]
            for field in optional_data_fields:
                if field in parsed:
                    data_section[field] = parsed[field]
            
            parsed["data"] = data_section
        
        # Ensure top-level fields exist (copy from data if missing)
        core_fields = ["name", "description", "personality", "scenario", "first_mes", "mes_example"]
        for field in core_fields:
            if field not in parsed and field in parsed.get("data", {}):
                parsed[field] = parsed["data"][field]
        
        # For AI, use the data section if it exists, otherwise use the full structure
        if "data" in parsed:
            metadata_for_ai = json.dumps(parsed["data"], indent=4)
        else:
            metadata_for_ai = json.dumps(parsed, indent=4)
        
        return parsed, metadata_for_ai

    @work(exclusive=True)
    async def ask_ai_to_edit(self, user_request: str, current_metadata: str) -> None:
        if not self.app.llm:
            self.app.notify("Model not loaded! Load a model first.", severity="error")
            return

        # Disable all buttons while AI is editing
        self.disable_all_buttons_except_play()
        self.query_one("#btn-play-card-user", Button).disabled = True
        self.query_one("#btn-play-card-ai", Button).disabled = True

        history = self.query_one("#ai-meta-history", ScrollableContainer)
        history.mount(Static(f"User: {user_request}", classes="ai-message user"))
        history.scroll_end()
        
        status_msg = Static("AI is thinking...", classes="ai-message system")
        history.mount(status_msg)
        history.scroll_end()

        try:
            # Normalize metadata structure and get the section to send to AI
            normalized_metadata, metadata_for_ai = self.normalize_metadata_structure(current_metadata)
            
            # Check if this looks like a new/template card to refine the prompt
            is_template = "New Character" in current_metadata and len(current_metadata) < 1000
            
            system_prompt = (
                "You are an expert character card creator for SillyTavern V2 format. "
                "Your goal is to transform the user's request into high-quality character data. "
                "\n\nINSTRUCTIONS:\n"
                "1. Provide a SINGLE flat JSON block with these keys: name, description, personality, scenario, first_mes, mes_example, tags (array).\n"
                "2. Be creative and detailed. Expand on the user's idea to make a rich, playable character.\n"
                "3. Ensure the character's voice in the 'first_mes' and 'mes_example' is distinct and consistent with their personality.\n"
                "\n\nJSON RULES:\n"
                "- ALWAYS provide the JSON in a ```json block.\n"
                "- Do NOT nest a 'data' block; provide a flat dictionary of the core fields.\n"
            )
            
            full_prompt = f"Current SillyTavern V2 JSON:\n{metadata_for_ai}\n\nUser Message: {user_request}\n\nComplete the card based on this request (include full updated JSON in ```json block):"
            
            import threading
            import queue as thread_queue
            
            token_queue = thread_queue.Queue()
            
            llm = self.app.llm
            params = {
                "temperature": self.app.temp,
                "top_p": self.app.topp,
                "top_k": self.app.topk,
                "repeat_penalty": self.app.repeat,
                "min_p": self.app.minp,
                "max_tokens": 4096,
                "stream": True,
                "stop": ["```\n", "}\n\n"] # Stop sequences to prevent trailing loop/gibberish
            }
            
            def stream_generation():
                try:
                    stream = llm.create_chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_prompt}
                        ],
                        **params
                    )
                    for chunk in stream:
                        # Handle None chunks (timeout yields)
                        if chunk is None:
                            continue
                        # Safely access delta content with proper None checks
                        choices = chunk.get("choices")
                        if choices and len(choices) > 0:
                            delta = choices[0].get("delta", {})
                            if delta:
                                content = delta.get("content", "")
                                if content:
                                    token_queue.put(content)
                    token_queue.put(None)
                except Exception as e:
                    token_queue.put(e)

            t = threading.Thread(target=stream_generation)
            t.start()
            
            answer = ""
            finished = False
            
            while not finished:
                try:
                    while True:
                        item = token_queue.get_nowait()
                        if item is None:
                            finished = True
                            break
                        if isinstance(item, Exception):
                            raise item
                        answer += item
                except thread_queue.Empty:
                    pass
                
                if answer:
                    status_msg.update(f"AI: {answer}")
                
                if finished:
                    break
                    
                history.scroll_end()
                await asyncio.sleep(0.05)
            
            # Post-processing
            json_match = re.search(r"```json\s*(.*?)\s*```", answer, re.DOTALL)
            if not json_match:
                json_match = re.search(r"({.*})", answer, re.DOTALL)
            
            # If still no match, try parsing the entire answer as JSON (might be raw JSON)
            raw_json = None
            if json_match:
                raw_json = json_match.group(1).strip()
            else:
                # Try parsing the whole answer as JSON
                try:
                    test_parsed = json.loads(answer.strip())
                    if isinstance(test_parsed, dict):
                        raw_json = answer.strip()
                except:
                    pass
                
            clean_json = None
            json_error_msg = None
            if raw_json:
                try:
                    # Try to fix common JSON issues before parsing
                    # Remove trailing commas before closing braces/brackets
                    raw_json = re.sub(r',(\s*[}\]])', r'\1', raw_json)
                    
                    parsed_ai = json.loads(raw_json)
                    
                    # Merge logic: Take the simplified AI output and apply it to the normalized V2 structure
                    # normalized_metadata already has both top-level fields and data section
                    base_v2 = normalized_metadata.copy()
                    
                    # Primary fields to clone
                    core_fields = ["name", "description", "personality", "scenario", "first_mes", "mes_example"]
                    
                    for key in core_fields:
                        if key in parsed_ai:
                            val = parsed_ai[key]
                            base_v2[key] = val
                            if "data" in base_v2:
                                base_v2["data"][key] = val
                    
                    if "tags" in parsed_ai:
                        tags = parsed_ai["tags"]
                        base_v2["tags"] = tags
                        if "data" in base_v2:
                            base_v2["data"]["tags"] = tags
                    
                    clean_json = json.dumps(base_v2, indent=4)
                except json.JSONDecodeError as e:
                    json_error_msg = f"JSON parse error: {str(e)}\nAttempted to parse: {raw_json[:200]}..."
                    # Try to extract just the fields we need even if JSON is malformed
                    try:
                        # Look for key-value pairs even in malformed JSON
                        parsed_ai = {}
                        for field in ["name", "description", "personality", "scenario", "first_mes", "mes_example", "tags"]:
                            # Try pattern that handles escaped quotes and multi-line strings
                            # Match: "field": "value" where value can contain escaped quotes
                            pattern = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"'
                            match = re.search(pattern, raw_json, re.DOTALL)
                            if match:
                                value = match.group(1)
                                # Unescape common escape sequences
                                value = value.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                                parsed_ai[field] = value
                        
                        # Try to extract tags array (handle multi-line)
                        tags_match = re.search(r'"tags"\s*:\s*\[(.*?)\]', raw_json, re.DOTALL)
                        if tags_match:
                            tags_str = tags_match.group(1)
                            tags_list = re.findall(r'"((?:[^"\\]|\\.)*)"', tags_str)
                            if tags_list:
                                parsed_ai["tags"] = [tag.replace('\\"', '"').replace('\\n', '\n') for tag in tags_list]
                        
                        if parsed_ai:
                            base_v2 = normalized_metadata.copy()
                            core_fields = ["name", "description", "personality", "scenario", "first_mes", "mes_example"]
                            for key in core_fields:
                                if key in parsed_ai:
                                    val = parsed_ai[key]
                                    base_v2[key] = val
                                    if "data" in base_v2:
                                        base_v2["data"][key] = val
                            if "tags" in parsed_ai:
                                tags = parsed_ai["tags"]
                                base_v2["tags"] = tags
                                if "data" in base_v2:
                                    base_v2["data"]["tags"] = tags
                            clean_json = json.dumps(base_v2, indent=4)
                    except Exception:
                        pass
                except Exception as e:
                    json_error_msg = f"Error processing AI response: {str(e)}"
                    # Fallback if something goes wrong
                    try:
                        clean_json = json.dumps(parsed_ai, indent=4)
                    except:
                        pass
            
            conv_text = answer
            if json_match:
                if "```json" in answer:
                    conv_text = re.sub(r"```json.*?```", "", answer, flags=re.DOTALL).strip()
                else:
                    conv_text = answer.replace(json_match.group(1), "").strip()
            elif raw_json and raw_json == answer.strip():
                # If we parsed the whole answer as JSON, there's no conversation text
                conv_text = ""

            if clean_json:
                self.query_one("#metadata-text", TextArea).text = clean_json
                # Mark card as unsaved when AI edits it and mark metadata as changed
                try:
                    list_view = self.query_one("#list-characters", ListView)
                    if list_view.highlighted_child:
                        card_path = getattr(list_view.highlighted_child, "name", None)
                        if card_path:
                            self.unsaved_card_path = card_path
                            # Don't update original_metadata here - keep it so Save button stays enabled
                            self.update_button_states()
                except Exception:
                    pass
                status_msg.update("AI: JSON Updated.")
            else:
                if json_error_msg:
                    status_msg.update(f"AI: Failed to parse JSON - {json_error_msg[:100]}...")
                else:
                    status_msg.update("AI: (No structural changes - no valid JSON found in response)")
            
            if conv_text:
                conv_text += "\n\n(Don't forget to click 'Save Changes' if you like the results!)"
                history.mount(Static(f"Assistant: {conv_text}", classes="ai-message"))
            
            # Show error details if JSON parsing failed
            if json_error_msg and not clean_json:
                history.mount(Static(f"Error: {json_error_msg}", classes="ai-message system"))
                
        except Exception as e:
            status_msg.update(f"AI error: {str(e)}")
        finally:
            # Re-enable buttons when AI editing finishes (play buttons will be handled by update_button_states)
            self.update_button_states()
        
        history.scroll_end()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        selected_item = self.query_one("#list-characters", ListView).highlighted_child
        card_path = getattr(selected_item, "name", "") if selected_item else None

        if event.button.id in ["btn-play-card-user", "btn-play-card-ai"]:
            if not self.app.llm:
                self.app.notify("Model not loaded! Load a model from the sidebar first.", severity="warning")
                return
            if card_path:
                metadata_str = self.query_one("#metadata-text", TextArea).text.strip()
                
                # Check if card is still encrypted
                if metadata_str.startswith("Encrypted Data"):
                    self.app.notify("Card is encrypted! Enter password to unlock.", severity="error")
                    self.query_one("#input-card-password").focus()
                    return
                
                force_ai = (event.button.id == "btn-play-card-ai")
                self.app.force_ai_speak_first = force_ai
                
                # We don't care if it's JSON or not, the engine now handles both
                self.dismiss({"action": "play", "path": card_path, "meta": metadata_str})
            else:
                self.app.notify("Select a card first!", severity="warning")
        elif event.button.id == "btn-new-card":
            def on_filename(filename):
                if not filename:
                    return
                # Ensure .png extension
                if not filename.lower().endswith(".png"):
                    filename += ".png"
                
                new_path = self.app.create_new_character_card(filename=filename)
                if new_path:
                    self.app.notify(f"Created new card: {os.path.basename(new_path)}")
                    # Mark as unsaved until user saves it
                    self.unsaved_card_path = str(new_path)
                    self.refresh_list(select_path=str(new_path))
                    
                    # Initiate AI Guidance
                    history = self.query_one("#ai-meta-history", ScrollableContainer)
                    history.query("*").remove()
                    history.mount(Static("Assistant: I've created a new card template! Tell me about the character you want to create (e.g., 'a 1920s detective who is obsessed with coffee'), and I'll fill out the whole card for you.", classes="ai-message"))
                    
                    # Focus the AI input
                    self.query_one("#ai-meta-input", Input).focus()
                else:
                    self.app.notify("Failed to create card (file name might exist)", severity="error")
                    self.query_one(".dialog-title").focus()

            self.app.push_screen(FileNamePrompt(initial_value="New_Character_Card", prompt_text="Name your new character file:"), on_filename)
        elif event.button.id == "btn-duplicate-card":
            if card_path:
                new_path = self.app.duplicate_character_card(card_path)
                if new_path:
                    self.app.notify(f"Duplicated: {os.path.basename(new_path)}")
                    self.refresh_list()
            else:
                self.app.notify("Select a card first!", severity="warning")
            self.query_one(".dialog-title").focus()
        elif event.button.id == "btn-rename-card":
            if card_path:
                current_name = Path(card_path).stem
                
                def on_rename(new_name):
                    if not new_name:
                        return
                    if not new_name.lower().endswith(".png"):
                        new_name += ".png"
                    
                    old_p = Path(card_path)
                    new_p = old_p.parent / new_name
                    
                    if new_p.exists() and new_p != old_p:
                        self.app.notify("File already exists!", severity="error")
                        return
                    
                    try:
                        old_p.rename(new_p)
                        self.app.notify(f"Renamed to: {new_name}")
                        self.refresh_list(select_path=str(new_p))
                    except Exception as e:
                        self.app.notify(f"Rename failed: {e}", severity="error")
                    self.query_one(".dialog-title").focus()

                self.app.push_screen(FileNamePrompt(initial_value=current_name, prompt_text="Rename character file:"), on_rename)
            else:
                self.app.notify("Select a card first!", severity="warning")
                self.query_one(".dialog-title").focus()
        elif event.button.id == "btn-delete-card":
            if card_path:
                try:
                    p = Path(card_path)
                    if p.exists():
                        p.unlink()
                        self.app.notify(f"Deleted: {p.name}")
                        # Clear metadata preview
                        self.query_one("#metadata-text", TextArea).text = ""
                        # Force refresh
                        self.refresh_list()
                        self.last_search_idx = -1
                    else:
                        self.app.notify("File not found.", severity="error")
                except Exception as e:
                    self.app.notify(f"Delete failed: {str(e)}", severity="error")
            else:
                self.app.notify("Select a card first!", severity="warning")
            
            # Focus handling
            try:
                self.query_one("#list-characters").focus()
            except Exception:
                self.query_one(".dialog-title").focus()
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
                    # Trigger button state update to enable Save button
                    self.update_button_states()
                    self.app.notify(f"Replaced occurrences of '{search_text}' (case-insensitive)")
                    self.query_one(".dialog-title").focus()
                else:
                    self.app.notify(f"'{search_text}' not found.", severity="warning")
            else:
                self.app.notify("Enter search text!", severity="warning")
            self.query_one(".dialog-title").focus()

        elif event.button.id == "btn-save-metadata":
            if card_path:
                def do_save(password):
                     if password is None: # User cancelled the password prompt
                         return
                         
                     try:
                        metadata_str = self.query_one("#metadata-text", TextArea).text.strip()
                        
                        # Prevent saving the placeholder text
                        if metadata_str.startswith("Encrypted Data"):
                            self.app.notify("Cannot save: Card is still locked. Unlock it first to save changes or remove encryption.", severity="error")
                            return
                            
                        if password:
                            final_data = encrypt_data(metadata_str, password)
                            self.app.notify("Saving encrypted metadata...")
                        else:
                            final_data = metadata_str
                            self.app.notify("Saving without encryption (encryption removed).")
                            
                        success = write_chara_metadata(card_path, final_data)
                        if success:
                            filename = Path(card_path).name
                            self.app.notify(f"Successfully updated {filename}")
                            # Card is now saved, clear unsaved flag
                            if self.unsaved_card_path == card_path:
                                self.unsaved_card_path = None
                            # Reload to refresh view state (e.g. show encrypted/decrypted)
                            # If we just encrypted it, we should probably show it in decrypted state or reload?
                            # Actually if we just saved it and we have the PW, we can reload with it?
                            # For simplicity, just reload regular. If encrypted, it will lock.
                            self.load_metadata(card_path, password_attempt=password)
                            # Deselect card after saving
                            self.refresh_list()
                        else:
                            self.app.notify("Failed to write metadata PNG! (File might be locked or invalid)", severity="error")
                     except Exception as e:
                        self.app.notify(f"Save crash: {str(e)}", severity="error")
                     self.query_one(".dialog-title").focus()

                self.app.push_screen(GenericPasswordModal(title="Encrypt Card? (Leave blank for no)", allow_blank=True), do_save)
            else:
                self.app.notify("Select a card first!", severity="warning")
                self.query_one(".dialog-title").focus()
        elif event.button.id == "btn-cancel-mgmt":
            self.dismiss(None)

class ParametersScreen(ModalScreen):
    """Modal for adjusting AI generation parameters."""
    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
    def compose(self) -> ComposeResult:
        # Fetch current values from the app
        app = self.app
        yield Vertical(
            Label("AI Parameters", classes="dialog-title"),
            Horizontal(
                Label("Temp", classes="param-label"),
                ScaledSlider(min_val=0.0, max_val=2.5, step=0.1, value=app.temp, id="input-temp"),
                Static(f"{app.temp:.2f}", id="value-temp", classes="param-value"),
                classes="setting-group"
            ),
            Horizontal(
                Label("Top P", classes="param-label"),
                ScaledSlider(min_val=0.1, max_val=1.0, step=0.01, value=app.topp, id="input-topp"),
                Static(f"{app.topp:.2f}", id="value-topp", classes="param-value"),
                classes="setting-group"
            ),
            Horizontal(
                Label("Top K", classes="param-label"),
                ScaledSlider(min_val=0, max_val=100, step=1, value=app.topk, id="input-topk"),
                Static(f"{app.topk}", id="value-topk", classes="param-value"),
                classes="setting-group"
            ),
            Horizontal(
                Label("Repeat", classes="param-label"),
                ScaledSlider(min_val=0.8, max_val=2.0, step=0.01, value=app.repeat, id="input-repeat"),
                Static(f"{app.repeat:.2f}", id="value-repeat", classes="param-value"),
                classes="setting-group"
            ),
            Horizontal(
                Label("Min P", classes="param-label"),
                ScaledSlider(min_val=0.0, max_val=1.0, step=0.01, value=app.minp, id="input-minp"),
                Static(f"{app.minp:.2f}", id="value-minp", classes="param-value"),
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

    def on_slider_changed(self, event) -> None:
        """Handle slider value changes from textual-slider."""
        # The event has slider and value attributes
        slider = event.slider
        if slider and slider.id:
            attr = slider.id.replace("input-", "")
            try:
                if isinstance(slider, ScaledSlider):
                    # Use the float_value property which converts from scaled integer
                    value = slider.float_value
                else:
                    # For regular sliders, use the event value
                    value = event.value
                value_label = self.query_one(f"#value-{attr}", Static)
                if attr == "topk":
                    value_label.update(f"{int(value)}")
                else:
                    value_label.update(f"{value:.2f}")
            except Exception as e:
                # Debug: uncomment to see errors
                # self.app.notify(f"Slider update error: {e}", severity="error")
                pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Handle parameter dialog buttons
        if event.button.id == "btn-reset-params":
            # Just reset the UI fields, don't apply to app yet
            defaults = {
                "temp": 0.8, "topp": 0.9, "topk": 40, "repeat": 1.0, "minp": 0.0
            }
            for attr, val in defaults.items():
                try:
                    slider = self.query_one(f"#input-{attr}", ScaledSlider)
                    slider.float_value = val
                    value_label = self.query_one(f"#value-{attr}", Static)
                    if attr == "topk":
                        value_label.update(f"{int(val)}")
                    else:
                        value_label.update(f"{val:.2f}")
                except Exception:
                    pass
            self.app.notify("UI values reset. Click Apply to save.")
            self.query_one(".dialog-title").focus()
            
        elif event.button.id == "btn-apply-params":
            # Read from UI and apply to app
            for attr in ["temp", "topp", "topk", "repeat", "minp"]:
                try:
                    slider = self.query_one(f"#input-{attr}", ScaledSlider)
                    if isinstance(slider, ScaledSlider):
                        val = slider.float_value
                    else:
                        val = slider.value
                    if attr == "topk":
                        val = int(val)
                    setattr(self.app, attr, val)
                except Exception:
                    pass
            
            if hasattr(self.app, "save_user_settings"):
                self.app.save_user_settings()
            self.app.notify("Parameters applied and saved.")
            self.dismiss()

        elif event.button.id == "btn-cancel-params":
            self.dismiss()


class ThemeScreen(ModalScreen):
    """Theme selection modal screen."""
    def on_mount(self) -> None:
        # Focus the title so no buttons are highlighted by default
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        
        # Set current theme in the selector
        current_theme = getattr(self.app, "theme", "textual-dark")
        try:
            self.query_one("#select-theme").value = current_theme
        except Exception:
            pass
        
        # Set current speech styling in the selector
        speech_styling = getattr(self.app, "speech_styling", "highlight")
        try:
            self.query_one("#select-speech-styling").value = speech_styling
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        # All built-in Textual themes
        # Store as instance variable so we can access it in on_select_changed
        self.available_themes = [
            ("Textual Dark", "textual-dark"),
            ("Textual Light", "textual-light"),
            ("Catppuccin Latte", "catppuccin-latte"),
            ("Catppuccin Mocha", "catppuccin-mocha"),
            ("Dracula", "dracula"),
            ("Flexoki", "flexoki"),
            ("Gruvbox", "gruvbox"),
            ("Monokai", "monokai"),
            ("Nord", "nord"),
            ("Solarized Light", "solarized-light"),
            ("Tokyo Night", "tokyo-night"),
        ]
        
        # Get current theme from app
        current_theme = getattr(self.app, "theme", "textual-dark")
        
        yield Vertical(
            Label("Theme Settings", classes="dialog-title"),
            Container(
                Label("Theme", classes="sidebar-label"),
                Select(self.available_themes, id="select-theme", value=current_theme, allow_blank=False),
                classes="sidebar-setting-group"
            ),
            Container(
                Label("Speech Styling", classes="sidebar-label"),
                Select(
                    [("None", "none"), ("Inversed", "inversed"), ("Highlight", "highlight")],
                    id="select-speech-styling",
                    value=getattr(self.app, "speech_styling", "highlight"),
                    allow_blank=False
                ),
                classes="sidebar-setting-group"
            ),
            Horizontal(
                Button("Close", variant="default", id="btn-close-theme"),
                classes="buttons"
            ),
            id="theme-dialog",
            classes="modal-dialog"
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-theme":
            try:
                # event.value returns the identifier (second value in tuple), not display name
                theme_identifier = event.value
                # Ensure we're using the identifier, not display name
                if hasattr(self.app, 'theme'):
                    self.app.theme = theme_identifier
                # Save to settings
                if hasattr(self.app, 'save_user_settings'):
                    self.app.save_user_settings()
            except Exception as e:
                self.app.notify(f"Error saving theme: {e}", severity="error")
        elif event.select.id == "select-speech-styling":
            try:
                speech_styling = event.value
                if hasattr(self.app, 'speech_styling'):
                    self.app.speech_styling = speech_styling
                # Save to settings
                if hasattr(self.app, 'save_user_settings'):
                    self.app.save_user_settings()
                # Refresh message widgets to apply new styling
                try:
                    chat_scroll = self.app.query_one("#chat-scroll")
                    for widget in chat_scroll.query(MessageWidget):
                        if widget.role == "assistant":
                            widget.refresh()
                except Exception:
                    pass
            except Exception as e:
                self.app.notify(f"Error saving speech styling: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-theme":
            self.dismiss()


class MiscScreen(ModalScreen):
    """About / Utility modal screen."""
    def on_mount(self) -> None:
        # Focus the title so no buttons are highlighted by default
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("About", classes="dialog-title"),
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
    original_data_backup: list = None # Backup of original data for cancel

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        self.current_data_idx = -1 # Reset on mount
        # Create a deep copy of the original data for cancel functionality
        self.original_data_backup = copy.deepcopy(self.app.action_menu_data)
        self.refresh_action_list()
        self.update_button_states()

    def compose(self) -> ComposeResult:
        # Clean and sort data immediately so we can populate the Select
        # ensuring it is never empty to prevent EmptySelectError
        if hasattr(self.app, "action_menu_data"):
             for item in self.app.action_menu_data:
                if "category" not in item:
                    item["category"] = "Other"
                if "isSystem" not in item:
                    item["isSystem"] = False
             
             self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))
        
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
                    Label("Item Name", classes="label"),
                    Input(id="input-action-name"),
                    Label("Prompt", classes="label"),
                    TextArea(id="input-action-prompt", classes="action-prompt-textarea"),
                    Label("Action Type", classes="label"),
                    Select([("Regular Action / User", "false"), ("System Prompt", "true")], id="select-action-type", allow_blank=False, value="false"),
                    classes="pane-right"
                ),
                Vertical(
                    ScrollableContainer(
                        Button("New Action", variant="default", id="btn-add-action-mgmt"),
                        Button("New Category", variant="default", id="btn-new-category-mgmt"),
                        Button("Duplicate", variant="default", id="btn-duplicate-action-mgmt", disabled=True),
                        Button("Delete", variant="default", id="btn-delete-action-mgmt", disabled=True),
                        Button("Delete Category", variant="default", id="btn-delete-category-mgmt"),
                        Button("Export All", variant="default", id="btn-export-all-mgmt"),
                        Button("Export Folder", variant="default", id="btn-export-folder-mgmt"),
                        Button("Import", variant="default", id="btn-import-mgmt"),
                        Button("Cancel", variant="default", id="btn-cancel-action-mgmt"),
                        Button("Apply Changes", variant="default", id="btn-apply-action-mgmt"),
                        id="buttons-scroll"
                    ),
                    classes="pane-buttons"
                ),
                id="management-split"
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
            
            display_name = act.get('name', '???')
            lv.append(ListItem(Label(f"[{cat}] {display_name}"), name=str(idx)))
        self.update_button_states()

    def update_button_states(self) -> None:
        """Update the enabled/disabled state of the buttons based on selection."""
        try:
            list_view = self.query_one("#list-actions-mgmt", ListView)
            has_selection = list_view.highlighted_child is not None
            self.query_one("#btn-duplicate-action-mgmt", Button).disabled = not has_selection
            self.query_one("#btn-delete-action-mgmt", Button).disabled = not has_selection
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-mgmt-filter":
            # Save current edit to working copy before changing filter
            if self.current_data_idx >= 0:
                self.save_current_edit()
            
            self.refresh_action_list()
            # After refreshing, the previously selected item might not exist or be at a new index.
            # Clear the edit fields and reset current_data_idx.
            self.current_data_idx = -1
            self.query_one("#input-action-name", Input).value = ""
            self.query_one("#input-action-prompt", TextArea).text = ""
            self.query_one("#select-action-type", Select).value = "false"
        elif event.select.id == "select-action-type":
            # Update working copy immediately (but not disk) when action type changes
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
        # Update working copy immediately (but not disk) when input changes
        if event.input.id == "input-action-name" and self.current_data_idx >= 0:
            self.save_current_edit()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        # Update working copy immediately (but not disk) when textarea changes
        if event.text_area.id == "input-action-prompt" and self.current_data_idx >= 0:
            self.save_current_edit()

    def save_current_edit(self) -> None:
        """Save current edit to the working copy (not to disk)."""
        idx = self.current_data_idx
        if idx < 0: return
        
        try:
            # Category is preserved from existing data, not from input field
            category = self.app.action_menu_data[idx].get('category', 'Other')
            item_name = self.query_one("#input-action-name", Input).value.strip()
            prompt = self.query_one("#input-action-prompt", TextArea).text
            is_system_val = self.query_one("#select-action-type", Select).value
            is_system = (is_system_val == "true")
            
            self.app.action_menu_data[idx]['category'] = category
            self.app.action_menu_data[idx]['name'] = item_name
            self.app.action_menu_data[idx]['prompt'] = prompt
            self.app.action_menu_data[idx]['isSystem'] = is_system
            
            # Update list label without full refresh to avoid focus/scroll jumps
            lv = self.query_one("#list-actions-mgmt", ListView)
            for child in lv.children:
                if getattr(child, "name", "") == str(idx):
                    child.query_one(Label).update(f"[{category}] {item_name}")
                    break
        except Exception:
            pass
    
    def apply_all_edits(self) -> None:
        """Save current edit field to working copy, then save all changes to disk."""
        # Save any pending edit from the current fields
        if self.current_data_idx >= 0:
            self.save_current_edit()
        
        # Save all changes to disk
        save_action_menu_data(self.app.action_menu_data)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "list-actions-mgmt":
            # Save current edit to working copy before switching items
            if self.current_data_idx >= 0:
                self.save_current_edit()
            
            self.update_button_states()
            if event.item:
                idx_str = getattr(event.item, "name", "-1")
                try:
                    self.current_data_idx = int(idx_str)
                    if self.current_data_idx >= 0 and self.current_data_idx < len(self.app.action_menu_data):
                        act = self.app.action_menu_data[self.current_data_idx]
                        
                        self.query_one("#input-action-name", Input).value = act.get('name', '')
                        self.query_one("#input-action-prompt", TextArea).text = act.get('prompt', '')
                        self.query_one("#select-action-type", Select).value = "true" if act.get('isSystem', False) else "false"
                    else:
                        self.current_data_idx = -1
                        # Clear fields if index is out of bounds (shouldn't happen with valid name)
                        self.query_one("#input-action-name", Input).value = ""
                        self.query_one("#input-action-prompt", TextArea).text = ""
                        self.query_one("#select-action-type", Select).value = "false"
                except ValueError: # if idx_str is not an int
                    self.current_data_idx = -1
                    self.query_one("#input-action-name", Input).value = ""
                    self.query_one("#input-action-prompt", TextArea).text = ""
                    self.query_one("#select-action-type", Select).value = "false"
            else:
                self.current_data_idx = -1
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
                # Update edit fields
                self.query_one("#input-action-name", Input).value = act.get('name', '')
                self.query_one("#input-action-prompt", TextArea).text = act.get('prompt', '')
                self.query_one("#select-action-type", Select).value = "true" if act.get('isSystem', False) else "false"
                break
        lv.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-action-mgmt":
            # Restore original data and close without saving
            self.app.action_menu_data = copy.deepcopy(self.original_data_backup)
            self.dismiss()
        elif event.button.id == "btn-apply-action-mgmt":
            # Save all edits and close
            self.apply_all_edits()
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
                
            new_act = {"category": cat, "name": name, "prompt": "Your instruction here...", "isSystem": is_system}
            self.app.action_menu_data.append(new_act)
            
            # Sort after adding: Category then Name
            self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))
            
            # Don't save here - will be saved when Apply is clicked
            self.update_filter_options()
            self.refresh_action_list()
            self.app.notify(f"New action added to {cat}. Click Apply to save.")
            
            # Find the new index of the added item using identity 'is'
            new_idx = -1
            for i, act in enumerate(self.app.action_menu_data):
                if act is new_act:
                    new_idx = i
                    break
            
            if new_idx != -1:
                # Use a small timer to allow the ListView to fully mount the new items
                self.set_timer(0.1, lambda: self.select_item_by_data_index(new_idx))

        elif event.button.id == "btn-new-category-mgmt":
            # Collect existing categories for validation
            existing_cats = [act.get('category', 'Other') for act in self.app.action_menu_data]
            
            def on_category_entered(category_name: str) -> None:
                if category_name is None:  # User cancelled
                    # Move focus away from the button to the dialog title
                    self.query_one(".dialog-title").focus()
                    return
                
                # Create a new action in the new category
                name = "new action"
                new_act = {"category": category_name, "name": name, "prompt": "Your instruction here...", "isSystem": False}
                self.app.action_menu_data.append(new_act)
                
                # Sort after adding: Category then Name
                self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))
                
                # Don't save here - will be saved when Apply is clicked
                
                # Update filter dropdown and select the new category
                self.update_filter_options()
                sel = self.query_one("#select-mgmt-filter", Select)
                sel.value = category_name
                
                # Refresh the list to show the new category
                self.refresh_action_list()
                self.app.notify(f"New category '{category_name}' created with action. Click Apply to save.")
                
                # Find the new index of the added item using identity 'is'
                new_idx = -1
                for i, act in enumerate(self.app.action_menu_data):
                    if act is new_act:
                        new_idx = i
                        break
                
                if new_idx != -1:
                    # Use a small timer to allow the ListView to fully mount the new items
                    self.set_timer(0.1, lambda: self.select_item_by_data_index(new_idx))
            
            # Open the category name prompt modal
            self.app.push_screen(
                CategoryNamePrompt(existing_categories=existing_cats),
                on_category_entered
            )
        
        elif event.button.id == "btn-delete-action-mgmt":
            idx = self.current_data_idx
            if idx >= 0:
                try:
                    del self.app.action_menu_data[idx]
                    self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))
                    # Don't save here - will be saved when Apply is clicked
                    self.update_filter_options()
                    self.refresh_action_list()
                    self.app.notify("Action deleted. Click Apply to save.")
                    self.current_data_idx = -1
                    self.query_one(".dialog-title").focus()
                except Exception as e:
                    self.app.notify(f"Delete error: {e}", severity="error")
                # Reset inputs if list empty
                if not self.app.action_menu_data:
                    self.query_one("#input-action-name", Input).value = ""
                    self.query_one("#input-action-prompt", TextArea).text = ""

        elif event.button.id == "btn-duplicate-action-mgmt":
            if self.current_data_idx >= 0:
                try:
                    orig_act = self.app.action_menu_data[self.current_data_idx]
                    
                    # Create copy
                    new_act = orig_act.copy()
                    base_name = new_act.get('name', 'Action')
                    
                    # Remove existing suffix if it matches _\d+
                    import re
                    clean_name = re.sub(r'_\d+$', '', base_name)
                    
                    # Find next increment
                    existing_names = [a.get('name', '') for a in self.app.action_menu_data]
                    counter = 1
                    new_name = f"{clean_name}_{counter}"
                    while new_name in existing_names:
                        counter += 1
                        new_name = f"{clean_name}_{counter}"
                    
                    new_act['name'] = new_name
                    self.app.action_menu_data.append(new_act)
                    
                    # Sort after duplicating: Category then Name
                    self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))
                    
                    # Don't save here - will be saved when Apply is clicked
                    self.update_filter_options()
                    self.refresh_action_list()
                    self.app.notify(f"Duplicated to: {new_name}. Click Apply to save.")
                    
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

        elif event.button.id == "btn-export-all-mgmt":
            self.export_actions(export_all=True)
            self.query_one(".dialog-title").focus()
        
        elif event.button.id == "btn-export-folder-mgmt":
            self.export_actions(export_all=False)
            self.query_one(".dialog-title").focus()
        
        elif event.button.id == "btn-import-mgmt":
            self.import_actions()
        
        elif event.button.id == "btn-delete-category-mgmt":
            self.delete_category()

    def delete_category(self) -> None:
        """Delete all actions in the currently selected category."""
        try:
            sel = self.query_one("#select-mgmt-filter", Select)
            if sel.value == Select.BLANK:
                self.app.notify("Please select a category filter first.", severity="warning")
                return
            
            filter_cat = sel.value
            
            # Count actions in this category
            actions_in_category = [
                act for act in self.app.action_menu_data 
                if act.get('category', 'Other') == filter_cat
            ]
            
            if not actions_in_category:
                self.app.notify(f"No actions found in category '{filter_cat}'.", severity="warning")
                return
            
            count = len(actions_in_category)
            
            # Show confirmation modal
            def on_confirm(confirmed: bool) -> None:
                if confirmed:
                    try:
                        # Remove all actions in this category
                        self.app.action_menu_data = [
                            act for act in self.app.action_menu_data 
                            if act.get('category', 'Other') != filter_cat
                        ]
                        
                        # Don't save here - will be saved when Apply is clicked
                        
                        # Update UI
                        self.update_filter_options()
                        self.refresh_action_list()
                        
                        # Clear edit fields since category is gone
                        self.current_data_idx = -1
                        self.query_one("#input-action-name", Input).value = ""
                        self.query_one("#input-action-prompt", TextArea).text = ""
                        self.query_one("#select-action-type", Select).value = "false"
                        
                        self.app.notify(f"Deleted category '{filter_cat}' ({count} action(s) removed). Click Apply to save.", severity="success")
                        self.query_one(".dialog-title").focus()
                    except Exception as e:
                        self.app.notify(f"Delete category error: {e}", severity="error")
                        self.query_one(".dialog-title").focus()
                else:
                    # User cancelled - lose focus from button
                    self.query_one(".dialog-title").focus()
            
            self.app.push_screen(
                ConfirmationModal(
                    title="Delete Category",
                    message=f"Are you sure you want to delete category '{filter_cat}'?\nThis will permanently delete {count} action(s)."
                ),
                on_confirm
            )
            
        except Exception as e:
            self.app.notify(f"Delete category error: {e}", severity="error")

    def export_actions(self, export_all: bool = True) -> None:
        """Export actions to a JSON file in the export folder."""
        try:
            # Create export directory if it doesn't exist
            export_dir = Path(__file__).parent / "export"
            export_dir.mkdir(exist_ok=True)
            
            filter_cat = None
            # Determine which actions to export
            if export_all:
                actions_to_export = self.app.action_menu_data.copy()
                filename = "actions_all.json"
            else:
                # Export only actions from the currently selected category
                try:
                    sel = self.query_one("#select-mgmt-filter", Select)
                    if sel.value == Select.BLANK:
                        self.app.notify("Please select a category filter first.", severity="warning")
                        return
                    filter_cat = sel.value
                except Exception:
                    self.app.notify("Could not determine selected category.", severity="error")
                    return
                
                actions_to_export = [
                    act.copy() for act in self.app.action_menu_data 
                    if act.get('category', 'Other') == filter_cat
                ]
                
                if not actions_to_export:
                    self.app.notify(f"No actions found in category '{filter_cat}'.", severity="warning")
                    return
                
                # Sanitize category name for filename
                safe_cat = "".join(c for c in filter_cat if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_cat = safe_cat.replace(' ', '_')
                filename = f"actions_{safe_cat}.json"
            
            # Write to file
            export_path = export_dir / filename
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(actions_to_export, f, indent=4, ensure_ascii=False)
            
            count = len(actions_to_export)
            scope = "all actions" if export_all else f"category '{filter_cat}'"
            self.app.notify(f"Exported {count} {scope} to {export_path.name}", severity="success")
            
        except Exception as e:
            self.app.notify(f"Export error: {e}", severity="error")

    def import_actions(self) -> None:
        """Import actions from a JSON file."""
        def on_file_selected(file_path: str) -> None:
            if not file_path:
                self.query_one(".dialog-title").focus()
                return
            
            try:
                import_path = Path(file_path)
                if not import_path.exists():
                    self.app.notify(f"File not found: {file_path}", severity="error")
                    self.query_one(".dialog-title").focus()
                    return
                
                # Read and parse JSON
                with open(import_path, "r", encoding="utf-8") as f:
                    imported_data = json.load(f)
                
                # Validate format
                if not isinstance(imported_data, list):
                    self.app.notify("Invalid format: Expected a JSON array.", severity="error")
                    self.query_one(".dialog-title").focus()
                    return
                
                # Validate each action has required fields
                valid_actions = []
                for idx, act in enumerate(imported_data):
                    if not isinstance(act, dict):
                        continue
                    if 'name' not in act or 'prompt' not in act:
                        continue
                    # Ensure required fields exist
                    if 'category' not in act:
                        act['category'] = 'Other'
                    if 'isSystem' not in act:
                        act['isSystem'] = False
                    valid_actions.append(act)
                
                if not valid_actions:
                    self.app.notify("No valid actions found in file.", severity="warning")
                    self.query_one(".dialog-title").focus()
                    return
                
                # Merge with existing actions (avoid duplicates by name+category)
                existing_names = {
                    (act.get('name', ''), act.get('category', 'Other'))
                    for act in self.app.action_menu_data
                }
                
                added_count = 0
                skipped_count = 0
                for act in valid_actions:
                    key = (act.get('name', ''), act.get('category', 'Other'))
                    if key not in existing_names:
                        self.app.action_menu_data.append(act)
                        existing_names.add(key)
                        added_count += 1
                    else:
                        skipped_count += 1
                
                # Sort after importing
                self.app.action_menu_data.sort(key=lambda x: (x.get("category", "Other").lower(), x.get("name", "").lower()))
                
                # Don't save here - will be saved when Apply is clicked
                
                # Refresh UI
                self.update_filter_options()
                self.refresh_action_list()
                
                msg = f"Imported {added_count} action(s)"
                if skipped_count > 0:
                    msg += f", skipped {skipped_count} duplicate(s)"
                msg += ". Click Apply to save."
                self.app.notify(msg, severity="success")
                self.query_one(".dialog-title").focus()
                
            except json.JSONDecodeError as e:
                self.app.notify(f"Invalid JSON file: {e}", severity="error")
                self.query_one(".dialog-title").focus()
            except Exception as e:
                self.app.notify(f"Import error: {e}", severity="error")
                self.query_one(".dialog-title").focus()
        
        # Show file picker for export folder
        export_dir = Path(__file__).parent / "export"
        export_dir.mkdir(exist_ok=True)
        
        self.app.push_screen(
            FilePickerModal(directory=export_dir, file_extension=".json"),
            on_file_selected
        )

class PasswordPromptScreen(ModalScreen):
    """Modal for entering a password to decrypt a chat."""
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Encrypted Chat Detected", classes="dialog-title"),
            Input(placeholder="Password / Passphrase", id="input-password", password=False),
            Horizontal(
                Button("Unlock & Load", variant="default", id="btn-unlock"),
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
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if it's already JSON (not encrypted) or needs decryption
            try:
                # If this succeeds, it was NOT encrypted
                data = json.loads(content)
                self.dismiss(data)
                return
            except json.JSONDecodeError:
                # Needs decryption
                decrypted_json = decrypt_data(content, password)
                data = json.loads(decrypted_json)
                self.dismiss(data)
        except Exception as e:
            self.app.notify(str(e), severity="error")
            self.query_one("#input-password").focus()

class ChatManagerScreen(ModalScreen):
    """Screen for managing saved chats (loading/saving)."""
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Chat Manager", classes="dialog-title"),
            Horizontal(
                Vertical(
                    Label("Saved Chats", classes="label"),
                    ListView(id="list-saved-chats"),
                    classes="pane-left"
                ),
                Vertical(
                    ScrollableContainer(
                        Button("Save Current Chat", variant="default", id="btn-save-chat"),
                        Button("Load Selected", variant="default", id="btn-load-chat", disabled=True),
                        Button("Delete", variant="default", id="btn-delete-chat", disabled=True),
                        Button("Close", variant="default", id="btn-close-chat"),
                        id="buttons-scroll"
                    ),
                    classes="pane-buttons"
                ),
                id="management-split"
            ),
            id="chat-manager-dialog",
            classes="modal-dialog"
        )

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        self.refresh_chat_list()
        self.update_button_states()

    def refresh_chat_list(self) -> None:
        chats_dir = Path(self.app.root_path) / "chats"
        if not chats_dir.exists():
            chats_dir.mkdir(parents=True, exist_ok=True)
        
        lv = self.query_one("#list-saved-chats", ListView)
        lv.clear()
        
        chats = sorted(list(chats_dir.glob("*.json")))
        for chat_file in chats:
            is_encrypted = False
            try:
                with open(chat_file, "r", encoding="utf-8") as f:
                    # Check first chunk for JSON structure; if missing, it's likely encrypted base64
                    chunk = f.read(100).strip()
                    if chunk and not (chunk.startswith("{") or chunk.startswith("[")):
                        is_encrypted = True
            except Exception:
                pass
            
            display_name = f"🔒 {chat_file.name}" if is_encrypted else chat_file.name
            lv.append(ListItem(Label(display_name), name=str(chat_file)))
        self.update_button_states()

    def update_button_states(self) -> None:
        """Update the enabled/disabled state of the buttons based on selection."""
        try:
            list_view = self.query_one("#list-saved-chats", ListView)
            has_selection = list_view.highlighted_child is not None
            self.query_one("#btn-load-chat", Button).disabled = not has_selection
            self.query_one("#btn-delete-chat", Button).disabled = not has_selection
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "list-saved-chats":
            self.update_button_states()

    def save_chat_callback(self, result) -> None:
        """Handle the result from SaveChatPrompt modal."""
        if not result:
            # User cancelled - return focus to title
            title = self.query_one(".dialog-title")
            title.focus()
            return
        
        save_name = result.get("filename", "").strip()
        password = result.get("password", "")
        
        if not save_name:
            import datetime
            save_name = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not save_name.endswith(".json"):
            save_name += ".json"
        
        chats_dir = Path(self.app.root_path) / "chats"
        file_path = chats_dir / save_name
        
        try:
            # Save messages only (model settings are not saved with chats)
            chat_data_json = json.dumps(self.app.messages, indent=2)
            if password:
                encrypted_data = encrypt_data(chat_data_json, password)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(encrypted_data)
                self.app.notify(f"Encrypted chat saved to {save_name}")
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(chat_data_json)
                self.app.notify(f"Chat saved to {save_name}")
            self.refresh_chat_list()
            # Return focus to title after saving
            title = self.query_one(".dialog-title")
            title.focus()
        except Exception as e:
            self.app.notify(f"Error saving chat: {e}", severity="error")
            # Return focus to title even on error
            title = self.query_one(".dialog-title")
            title.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-chat":
            self.dismiss()
        elif event.button.id == "btn-save-chat":
            self.app.push_screen(SaveChatPrompt(), self.save_chat_callback)

        elif event.button.id == "btn-load-chat":
            selected = self.query_one("#list-saved-chats", ListView).highlighted_child
            if selected:
                file_path = getattr(selected, "name", "")
                if file_path:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        try:
                            # Try loading as plain JSON first
                            data = json.loads(content)
                            # Handle both old format (just messages list) and legacy format (dict with messages and model_settings)
                            if isinstance(data, list):
                                # Current format: just messages list
                                messages = data
                            elif isinstance(data, dict) and "messages" in data:
                                # Legacy format: dict with messages and model_settings (ignore model_settings)
                                messages = data["messages"]
                            else:
                                # Fallback: treat as messages
                                messages = data
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

    def password_prompt_callback(self, result):
        if result:
            # result can be either messages (current format) or dict with messages and model_settings (legacy format)
            if isinstance(result, list):
                # Current format: just messages list
                messages = result
            elif isinstance(result, dict) and "messages" in result:
                # Legacy format: dict with messages and model_settings (ignore model_settings)
                messages = result["messages"]
            else:
                # Fallback: treat as messages
                messages = result
            self.dismiss({"action": "load", "messages": messages})
        else:
            # User cancelled the password prompt - return focus to title
            title = self.query_one(".dialog-title")
            title.focus()

class VectorChatScreen(ModalScreen):
    """The modal for managing vector chats (RAG)."""
    def compose(self) -> ComposeResult:
        with Vertical(id="vector-chat-dialog", classes="modal-dialog"):
            yield Label("Vector Chat (RAG)", classes="dialog-title")
            
            yield Label("Manage your vector chat databases.", classes="dialog-subtitle")
            yield Label("Conversations are stored locally and retrieved based on similarity.", classes="dialog-subtitle")
            
            with Horizontal(id="management-split"):
                with Vertical(classes="pane-left-vector"):
                    with Horizontal(id="vector-input-container"):
                        yield Input(placeholder="New Vector Chat Name", id="input-vector-name")
                        yield Button("Create", id="btn-vector-create")
                    
                    yield Label("Password (Optional - for encryption):", classes="label")
                    yield Input(placeholder="Password / Passphrase", id="input-vector-password", password=False)
                    
                    yield Label("Existing Vector Chats:", classes="section-label")
                    yield ListView(id="list-vector-chats")
                
                with Vertical(classes="pane-buttons"):
                    with ScrollableContainer(id="buttons-scroll"):
                        yield Button("Load", variant="default", id="btn-vector-load", disabled=True)
                        yield Button("Inspect", variant="default", id="btn-vector-inspect", disabled=True)
                        yield Button("Duplicate", variant="default", id="btn-vector-duplicate", disabled=True)
                        yield Button("Rename", variant="default", id="btn-vector-rename", disabled=True)
                        yield Button("Delete", variant="default", id="btn-vector-delete", disabled=True)
                        yield Button("Disable Vector Chat", variant="default", id="btn-vector-disable")
                        yield Button("Close", variant="default", id="btn-close")

    def on_mount(self) -> None:
        title = self.query_one(".dialog-title")
        title.can_focus = True
        title.focus()
        self.update_vector_list()
        # Disable the 'Disable' button if vector chat is not currently enabled
        self.query_one("#btn-vector-disable").disabled = not getattr(self.app, "enable_vector_chat", False)
        self.update_button_states()

    def update_button_states(self):
        """Enable or disable management buttons based on selection."""
        try:
            list_view = self.query_one("#list-vector-chats", ListView)
            has_selection = list_view.highlighted_child is not None
            
            for btn_id in ["btn-vector-load", "btn-vector-inspect", "btn-vector-duplicate", "btn-vector-rename", "btn-vector-delete"]:
                self.query_one(f"#{btn_id}").disabled = not has_selection
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "#list-vector-chats" or event.list_view.id == "list-vector-chats":
            self.update_button_states()

    def update_vector_list(self):
        vectors_dir = Path(__file__).parent / "vectors"
        if not vectors_dir.exists():
            vectors_dir.mkdir(parents=True, exist_ok=True)
            
        chats = [d.name for d in vectors_dir.iterdir() if d.is_dir()]
        list_view = self.query_one("#list-vector-chats", ListView)
        list_view.clear()
        for chat in sorted(chats):
            is_encrypted = (vectors_dir / chat / ".encrypted").exists()
            display_name = f"🔒 {chat}" if is_encrypted else chat
            item = ListItem(Label(display_name))
            item.chat_name = chat  # Custom attribute for reliability
            item.is_encrypted = is_encrypted
            list_view.append(item)
        self.update_button_states()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-vector-create":
            name = self.query_one("#input-vector-name", Input).value.strip()
            password = self.query_one("#input-vector-password", Input).value
            if name:
                self.dismiss({"action": "create", "name": name, "password": password})
            else:
                self.app.notify("Please enter a name for the new vector chat.", severity="error")
        elif event.button.id == "btn-vector-load":
            try:
                selected = self.query_one("#list-vector-chats", ListView).highlighted_child
                if selected and hasattr(selected, "chat_name"):
                    password = self.query_one("#input-vector-password", Input).value
                    if selected.is_encrypted and not password:
                        self.app.notify("This vector chat is encrypted! Please enter the password below.", severity="warning")
                        self.query_one("#input-vector-password").focus()
                        return
                    
                    # Validate password before dismissing modal
                    if selected.is_encrypted:
                        try:
                            self.app.validate_vector_password(selected.chat_name, password)
                        except Exception as e:
                            self.app.notify(str(e), severity="error")
                            self.query_one("#input-vector-password").value = ""
                            self.query_one("#input-vector-password").focus()
                            return

                    self.dismiss({"action": "load", "name": selected.chat_name, "password": password})
                else:
                    self.app.notify("No vector chat selected.", severity="warning")
            except Exception as e:
                self.app.notify(f"Load error: {e}", severity="error")
        elif event.button.id == "btn-vector-inspect":
            try:
                item = self.query_one("#list-vector-chats", ListView).highlighted_child
                if item and hasattr(item, "chat_name"):
                    password = self.query_one("#input-vector-password", Input).value
                    if item.is_encrypted and not password:
                         self.app.notify("This vector chat is encrypted. Provide a password to see plaintext.", severity="information")
                    self.app.push_screen(VectorInspectScreen(item.chat_name, password=password), lambda _: self.query_one(".dialog-title").focus())
                else:
                    self.app.notify("No vector chat selected.", severity="warning")
            except Exception as e:
                self.app.notify(f"Inspect error: {e}", severity="error")
        elif event.button.id == "btn-vector-duplicate":
            item = self.query_one("#list-vector-chats", ListView).highlighted_child
            if item and hasattr(item, "chat_name"):
                def on_duplicate(new_name):
                    if new_name:
                        import shutil
                        old_name = item.chat_name
                        old_path = Path(__file__).parent / "vectors" / old_name
                        new_path = Path(__file__).parent / "vectors" / new_name
                        if new_path.exists():
                            self.app.notify("A vector chat with that name already exists.", severity="error")
                        else:
                            try:
                                # Ignore lock files which might be open and cause copy errors
                                shutil.copytree(old_path, new_path, ignore=shutil.ignore_patterns('.lock', 'LOCK', '*.lock'))
                                self.app.notify(f"Duplicated {old_name} to {new_name}")
                                self.update_vector_list()
                            except Exception as e:
                                self.app.notify(f"Duplicate error: {e}", severity="error")
                        self.query_one(".dialog-title").focus()
                self.app.push_screen(FileNamePrompt(initial_value=f"{item.chat_name}_copy", prompt_text="Name for duplicate:"), on_duplicate)
            else:
                self.app.notify("No vector chat selected.", severity="warning")
        elif event.button.id == "btn-vector-rename":
            item = self.query_one("#list-vector-chats", ListView).highlighted_child
            if item and hasattr(item, "chat_name"):
                if getattr(self.app, "vector_chat_name", None) == item.chat_name:
                    self.app.notify("Cannot rename the currently active vector chat.", severity="error")
                    return
                def on_rename(new_name):
                    if new_name and new_name != item.chat_name:
                        import shutil
                        old_name = item.chat_name
                        old_path = Path(__file__).parent / "vectors" / old_name
                        new_path = Path(__file__).parent / "vectors" / new_name
                        if new_path.exists():
                            self.app.notify("A vector chat with that name already exists.", severity="error")
                        else:
                            try:
                                old_path.rename(new_path)
                                self.app.notify(f"Renamed {old_name} to {new_name}")
                                self.update_vector_list()
                            except Exception as e:
                                self.app.notify(f"Rename error: {e}", severity="error")
                        self.query_one(".dialog-title").focus()
                self.app.push_screen(FileNamePrompt(initial_value=item.chat_name, prompt_text="New name:"), on_rename)
            else:
                self.app.notify("No vector chat selected.", severity="warning")
        elif event.button.id == "btn-vector-delete":
            try:
                item = self.query_one("#list-vector-chats", ListView).highlighted_child
                if item and hasattr(item, "chat_name"):
                    chat_name = item.chat_name
                    
                    # If this is the active vector chat, we must stop/close it first
                    if getattr(self.app, "vector_chat_name", None) == chat_name:
                        if hasattr(self.app, "close_vector_db"):
                            self.app.close_vector_db()
                        self.app.enable_vector_chat = False
                        self.app.vector_chat_name = None
                        self.app.notify(f"Deactivating '{chat_name}' before deletion...")

                    import shutil
                    vectors_dir = Path(__file__).parent / "vectors" / chat_name
                    if vectors_dir.exists():
                        try:
                            shutil.rmtree(vectors_dir)
                            self.app.notify(f"Deleted vector chat: {chat_name}", severity="warning")
                            self.update_vector_list()
                        except Exception as e:
                            self.app.notify(f"Delete failed: {e}. Is the database still in use?", severity="error")
                else:
                    self.app.notify("No vector chat selected.", severity="warning")
            except Exception as e:
                self.app.notify(f"Delete error: {e}", severity="error")
        elif event.button.id == "btn-vector-disable":
            if hasattr(self.app, "action_disable_vector_chat"):
                await self.app.action_disable_vector_chat()
                event.button.disabled = True
            else:
                self.app.notify("Disable action not found.", severity="error")
        elif event.button.id == "btn-close":
            self.dismiss()

        # Reset focus to title for buttons that don't dismiss
        if event.button.id not in ["btn-close", "btn-vector-create", "btn-vector-load"]:
            try:
                self.query_one(".dialog-title").focus()
            except Exception:
                pass

class VectorInspectScreen(ModalScreen):
    """Screen for inspecting vectors in a database."""
    def __init__(self, chat_name: str, password: str = None):
        super().__init__()
        self.chat_name = chat_name
        self.password = password

    def compose(self) -> ComposeResult:
        with Container(id="vector-inspect-dialog", classes="modal-dialog"):
            yield Label(f"Inspect Vectors: {self.chat_name}", classes="dialog-title")
            from textual.widgets import TextArea
            yield TextArea("Loading...", id="vector-content", read_only=True)
            with Horizontal(classes="buttons"):
                yield Button("Close", id="btn-close", variant="default")

    def on_mount(self) -> None:
        self.load_vectors()

    @work(exclusive=True, thread=True)
    def load_vectors(self):
        try:
            import qdrant_client
        except ImportError:
            self.app.call_from_thread(self.update_content, "qdrant-client not installed!")
            return
            
        vectors_dir = Path(__file__).parent / "vectors" / self.chat_name
        
        new_client = False
        if getattr(self.app, "vector_chat_name", None) == self.chat_name and getattr(self.app, "qdrant_instance", None):
            client = self.app.qdrant_instance
        else:
            try:
                client = qdrant_client.QdrantClient(path=str(vectors_dir))
                new_client = True
            except Exception as e:
                self.app.call_from_thread(self.update_content, f"Failed to open database: {e}\n(Is it open in another window?)")
                return
        
        try:
            # Detect available collections - name may be 'chat_memory' or 'chat_memory_768' etc.
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            target_collection = "chat_memory"
            if target_collection not in collection_names:
                # Look for suffixed version
                for name in collection_names:
                    if name.startswith("chat_memory"):
                        target_collection = name
                        break
            else:
                # If 'chat_memory' exists but is empty, and a suffixed one exists, use the suffixed one
                try:
                    count = client.count(collection_name="chat_memory").count
                    if count == 0:
                        for name in collection_names:
                            if name.startswith("chat_memory_"):
                                target_collection = name
                                break
                except Exception:
                    pass

            scroll_result = client.scroll(
                collection_name=target_collection,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            points = scroll_result[0]
            if not points:
                content = f"No vectors found in collection '{target_collection}'."
            else:
                lines = []
                lines.append(f"Total Vectors: {len(points)}")
                lines.append("=" * 80)
                lines.append("")
                for i, point in enumerate(points):
                    text = point.payload.get("text", "No text")
                    is_encrypted = point.payload.get("encrypted", False)
                    
                    if is_encrypted:
                        if self.password:
                            try:
                                from utils import decrypt_data
                                text = decrypt_data(text, self.password)
                            except Exception:
                                text = "[FAILED TO DECRYPT - INCORRECT PASSWORD]"
                        else:
                            text = "[ENCRYPTED CONTENT - PROVIDE PASSWORD TO VIEW]"

                    lines.append(f"[Vector #{i+1}]")
                    lines.append(f"ID: {point.id}")
                    lines.append("")
                    # Format the text nicely
                    if "\nAssistant: " in text:
                        parts = text.split("\nAssistant: ")
                        user_part = parts[0].replace("User: ", "")
                        assistant_part = parts[1] if len(parts) > 1 else ""
                        lines.append(f"👤 User: {user_part}")
                        lines.append(f"🤖 Assistant: {assistant_part}")
                    else:
                        lines.append(text)
                    lines.append("")
                    lines.append("-" * 80)
                    lines.append("")
                content = "\n".join(lines)
            self.app.call_from_thread(self.update_content, content)
        except Exception as e:
            self.app.call_from_thread(self.update_content, f"Error inspecting vectors: {e}")
        finally:
            if new_client:
                try:
                    client.close()
                except Exception:
                    pass

    def update_content(self, content: str):
        try:
            from textual.widgets import TextArea
            widget = self.query_one("#vector-content", TextArea)
            widget.load_text(content)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss()

