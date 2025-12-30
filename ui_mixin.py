from textual.widgets import Select, Button
from widgets import MessageWidget

class UIMixin:
    """Mixin for UI-related helper methods."""
    
    async def add_message(self, role: str, content: str):
        self.messages = [*self.messages, {"role": role, "content": content}]
        chat_scroll = self.query_one("#chat-scroll")
        msg_widget = MessageWidget(role, content, user_name=self.user_name, is_info=False)
        await chat_scroll.mount(msg_widget)
        chat_scroll.scroll_end(animate=False)
        return msg_widget

    async def add_info_message(self, content: str):
        """Displays a message in the chat that is NOT added to the LLM context."""
        chat_scroll = self.query_one("#chat-scroll")
        msg_widget = MessageWidget("system", content, user_name=self.user_name, is_info=True)
        await chat_scroll.mount(msg_widget)
        chat_scroll.scroll_end(animate=False)
        return msg_widget

    def sync_add_assistant_widget(self, content):
        chat_scroll = self.query_one("#chat-scroll")
        msg_widget = MessageWidget("assistant", content, user_name=self.user_name, is_info=False)
        chat_scroll.mount(msg_widget)
        chat_scroll.scroll_end(animate=False)
        return msg_widget

    def sync_update_assistant_widget(self, widget, content):
        widget.content = content
        widget.refresh()
        self.query_one("#chat-scroll").scroll_end(animate=False)
    
    async def full_sync_chat_ui(self):
        """Robustly rebuild the entire chat UI from self.messages."""
        chat_scroll = self.query_one("#chat-scroll")
        chat_scroll.remove_children()
        
        # We don't usually show the first system prompt (index 0) in the UI 
        # unless it was explicitly added via set_system_prompt which calls add_info_message.
        # But for robustness, let's just make sure UI reflects what's in context if we want "sync".
        # Actually, the app's style is to NOT show the system prompt in the scroll area as a regular message.
        for i, msg in enumerate(self.messages):
            if i == 0 and msg.get("role") == "system":
                continue # Skip the base system prompt
            
            role = msg.get("role")
            content = msg.get("content")
            if content:
                new_widget = MessageWidget(role, content, self.user_name, is_info=False)
                await chat_scroll.mount(new_widget)
        
        chat_scroll.scroll_end(animate=False)

    def _update_messages_safely(self, new_messages):
        """Safely update messages list and sync UI if pruned."""
        old_len = len(self.messages)
        new_len = len(new_messages)
        
        if old_len > 0 and new_len > 0 and new_len < old_len:
            diff = old_len - new_len
            try:
                scroll = self.query_one("#chat-scroll")
                # When pruning, we remove from index 1 onwards in self.messages.
                # So we should find the corresponding non-info widgets and remove them.
                context_widgets = [w for w in scroll.children if isinstance(w, MessageWidget) and not w.is_info]
                
                # We want to keep the first one if it corresponds to messages[0]? 
                # Actually, messages[0] isn't usually in context_widgets if it's the base system prompt.
                # Let's count how many we need to remove.
                to_remove = diff
                for w in context_widgets:
                    if to_remove <= 0: break
                    # Skip the very first one if it's the one we always keep (system)
                    # But wait, if context_widgets[0] is NOT in self.messages anymore...
                    w.remove()
                    to_remove -= 1
            except Exception:
                pass

        self.messages = list(new_messages)

    def watch_status_text(self, new_status):
        self.query_one("#status-text").update(new_status)

    def watch_is_loading(self, is_loading: bool) -> None:
        try:
            self.query_one("#btn-stop").display = is_loading
            self.query_one("#btn-continue").display = not is_loading
        except Exception:
            pass

    def watch_user_name(self, name):
        if hasattr(self, "title"):
            self.title = f"aiMultiFool - {name}"
