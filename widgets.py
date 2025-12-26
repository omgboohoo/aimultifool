import re
import json
from rich.text import Text
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Container, Horizontal, Grid
from textual.widgets import Label, Input, Select, Button, ListView, Static, TextArea

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
        else:
            self.add_class("-assistant")

    def render(self):
        if self.role == "user":
            return Text(self.content, style="green")
        else:
            return create_styled_text(self.content)

class Sidebar(Vertical):
    """The sidebar containing settings and character info."""
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Username"),
            Input(placeholder="Enter your name", id="input-username"),
            classes="setting-group"
        )
        yield Container(
            Label("Model"),
            Select([], id="select-model", prompt="Select a model"),
            classes="setting-group"
        )
        yield Container(
            Label("Context Size"),
            Select([(str(x), x) for x in [2048, 4096, 8192, 16384, 32768]], id="select-context", value=4096),
            classes="setting-group"
        )
        yield Container(
            Label("GPU Layers"),
            Select([("All (-1)", -1), ("CPU Only (0)", 0)] + [(str(x), x) for x in range(8, 129, 8)], id="select-gpu-layers", value=-1),
            classes="setting-group"
        )
        yield Container(
            Label("Style"),
            Select([
                ("Concise", "concise"), 
                ("Descriptive", "descriptive"),
                ("Dramatic", "dramatic"),
                ("Action-Oriented", "action"),
                ("Internalized", "internalized"),
                ("Hardboiled", "hardboiled"),
                ("Creative", "creative"),
                ("Erotic", "erotic"),
                ("Flowery", "flowery"),
                ("Minimalist", "minimalist"),
                ("Humorous", "humorous"),
                ("Dark Fantasy", "dark_fantasy"),
                ("Scientific", "scientific"),
                ("Casual", "casual"),
                ("Historical", "historical"),
                ("Horror", "horror"),
                ("Surreal", "surreal"),
                ("Philosophical", "philosophical"),
                ("Gritty", "gritty"),
                ("Whimsical", "whimsical")
            ], id="select-style", value="concise", prompt=""),
            classes="setting-group"
        )
        yield Container(
            Label("Temperature (0.0-2.5)"),
            Input(value="0.80", id="input-temp"),
            classes="setting-group"
        )
        yield Container(
            Label("Top P (0.1-1.0)"),
            Input(value="0.90", id="input-topp"),
            classes="setting-group"
        )
        yield Container(
            Label("Top K (0-100)"),
            Input(value="40", id="input-topk"),
            classes="setting-group"
        )
        yield Container(
            Label("Repeat Penalty (0.8-2.0)"),
            Input(value="1.00", id="input-repeat"),
            classes="setting-group"
        )
        yield Button("Load Model", variant="default", id="btn-load-model")
        yield Container(
            Label("Character Cards"),
            classes="setting-group"
        )
        yield ListView(id="list-characters")

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

class DebugContextScreen(ModalScreen):
    """Screen for showing the current chat context."""
    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def compose(self) -> ComposeResult:
        context_text = json.dumps(self.messages, indent=2)
        yield Vertical(
            Label("Debug: Current Context", classes="dialog-title"),
            TextArea(context_text, id="debug-text", read_only=True),
            Horizontal(
                Button("Close", variant="default", id="close"),
                classes="buttons"
            ),
            id="debug-dialog",
            classes="modal-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss()
