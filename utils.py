import json
import re
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "settings.json"
ACTION_MENU_FILE = Path(__file__).parent / "action_menu.json"

def _get_action_menu_data():
    """Retrieves action menu data from the JSON file or creates it from defaults."""
    if not ACTION_MENU_FILE.exists():
        try:
            from action_menu_defaults import default_action_menu_json
            with open(ACTION_MENU_FILE, "w", encoding="utf-8") as f:
                json.dump(default_action_menu_json, f, indent=4, ensure_ascii=False)
            return default_action_menu_json
        except Exception as e:
            print(f"Error creating default action menu from local defaults: {e}")
            return []
    try:
        with open(ACTION_MENU_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if "ui" in data:
            return data["ui"]
        return []
    except Exception:
        return []

def save_action_menu_data(data):
    """Saves action menu data to the JSON file."""
    try:
        with open(ACTION_MENU_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving action menu: {e}")
        return False

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass

# Check for download capability
try:
    import requests
    from tqdm import tqdm
    DOWNLOAD_AVAILABLE = True
except ImportError:
    DOWNLOAD_AVAILABLE = False

def get_style_prompt(style: str) -> str:
    styles = {
        "Default": "you are a helpful AI.",
        "concise": "Keep your replies concise.",
        "descriptive": "Be descriptive at all times.",
        "dramatic": "Use evocative, flowery language and place heavy emphasis on character emotions and high stakes.",
        "action": "Focus intensely on physical movements, choreography, and sensory details with fast-paced, punchy prose.",
        "internalized": "Heavily include the character's internal monologues, private thoughts, and psychological state in every response.",
        "hardboiled": "Use a cynical, grounded tone with short, sharp sentences. Focus on the harsh realities of the environment.",
        "creative": "Take creative risks with narration, using unique metaphors and unpredictable observations to describe the scene.",
        "erotic": "Use a flirtatious, suggestive, and alluring tone. Focus on the chemistry between characters, physical attraction, and sultry descriptions.",
        "flowery": "Use excessively ornate and poetic language, focusing on beauty and elaborate descriptions.",
        "minimalist": "Be extremely brief and direct. Use the fewest words possible.",
        "humorous": "Maintain a light-hearted, comedic tone. Find the humor in every situation.",
        "dark_fantasy": "Use a grim, ominous tone suitable for a dark fantasy setting. Focus on shadows, magic, and danger.",
        "scientific": "Use clinical, precise, and analytical language. Describe things as a scientist would.",
        "casual": "Use relaxed, modern language with slang and informal grammar.",
        "historical": "Use archaic language and sentence structures appropriate for a historical setting.",
        "horror": "Create an unsettling, tense atmosphere. Focus on fear, suspense, and the uncanny.",
        "surreal": "Describe the scene in a dream-like, abstract way. Focus on the weird and illogical.",
        "philosophical": "Explore the deeper meaning of events. Ask questions and ponder existence.",
        "gritty": "Focus on the dirty, realistic details of life. Show the world as it is, warts and all.",
        "whimsical": "Use a playful, fairy-tale tone. Focus on wonder, magic, and light-hearted fun."
    }
    prompt = styles.get(style, "you are a helpful AI.")
    return f"Do not reply on behalf of user. {prompt}"
