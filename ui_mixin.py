from textual.widgets import Select, Button
from widgets import MessageWidget

class UIMixin:
    """Mixin for UI-related helper methods."""
    
    async def add_message(self, role: str, content: str):
        self.messages = [*self.messages, {"role": role, "content": content}]
        chat_scroll = self.query_one("#chat-scroll")
        msg_widget = MessageWidget(role, content, user_name=self.user_name)
        await chat_scroll.mount(msg_widget)
        chat_scroll.scroll_end(animate=False)
        return msg_widget

    async def add_info_message(self, content: str):
        """Displays a message in the chat that is NOT added to the LLM context."""
        chat_scroll = self.query_one("#chat-scroll")
        msg_widget = MessageWidget("system", content, user_name=self.user_name)
        await chat_scroll.mount(msg_widget)
        chat_scroll.scroll_end(animate=False)
        return msg_widget

    def sync_add_assistant_widget(self, content):
        chat_scroll = self.query_one("#chat-scroll")
        msg_widget = MessageWidget("assistant", content, user_name=self.user_name)
        chat_scroll.mount(msg_widget)
        chat_scroll.scroll_end(animate=False)
        return msg_widget

    def sync_update_assistant_widget(self, widget, content):
        widget.content = content
        widget.refresh()
        self.query_one("#chat-scroll").scroll_end(animate=False)
    
    def _update_messages_safely(self, new_messages):
        """Safely update messages list and sync UI if pruned."""
        old_len = len(self.messages)
        new_len = len(new_messages)
        
        if old_len > 0 and new_len > 0 and new_len < old_len:
            diff = old_len - new_len
            try:
                scroll = self.query_one("#chat-scroll")
                widgets = list(scroll.children)
                for i in range(min(diff, len(widgets))):
                    widgets[i].remove()
            except Exception:
                pass

        self.messages = list(new_messages)

    def watch_status_text(self, new_status):
        self.query_one("#status-bar").update(new_status)

    def watch_is_loading(self, is_loading: bool) -> None:
        try:
            self.query_one("#btn-stop").display = is_loading
            self.query_one("#btn-continue").display = not is_loading
        except Exception:
            pass

    def watch_user_name(self, name):
        if hasattr(self, "title"):
            self.title = f"aiMultiFool v0.1.7 - {name}"

    def watch_is_model_loading(self, loading: bool) -> None:
        try:
            btn = self.query_one("#btn-load-model", Button)
            btn.loading = loading
            btn.disabled = loading
        except Exception:
            pass
