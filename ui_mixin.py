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
        chat_scroll.query("*").remove()
        
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
        
        # Update the messages list first
        self.messages = list(new_messages)
        
        # If messages were pruned, rebuild the UI to match exactly
        if old_len > 0 and new_len > 0 and new_len < old_len:
            # Rebuild the entire chat UI to match the pruned messages exactly
            # This ensures the chat window matches the context window
            try:
                chat_scroll = self.query_one("#chat-scroll")
                # Remove all message widgets (but keep info widgets if any)
                widgets_to_remove = [w for w in chat_scroll.children if isinstance(w, MessageWidget) and not w.is_info]
                for w in widgets_to_remove:
                    w.remove()
                
                # Rebuild widgets from current messages (skip system prompt at index 0)
                for i, msg in enumerate(self.messages):
                    if i == 0 and msg.get("role") == "system":
                        continue  # Skip the base system prompt
                    
                    role = msg.get("role")
                    content = msg.get("content")
                    if content:
                        new_widget = MessageWidget(role, content, self.user_name, is_info=False)
                        chat_scroll.mount(new_widget)
                
                chat_scroll.scroll_end(animate=False)
            except Exception:
                pass

    def watch_status_text(self, new_status):
        self.query_one("#status-text").update(new_status)

    def watch_is_loading(self, is_loading: bool) -> None:
        try:
            self.query_one("#btn-stop").display = is_loading
            self.query_one("#btn-continue").display = not is_loading
            # Regenerate button stays visible during generation so user can stop and regen
            self.query_one("#btn-regenerate").display = True
        except Exception:
            pass

    def watch_user_name(self, name):
        if hasattr(self, "title"):
            self.title = f"aiMultiFool - {name}"
