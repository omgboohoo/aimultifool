import json
import re
import os
import base64
from pathlib import Path
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SETTINGS_FILE = Path(__file__).parent / "settings.json"
ACTION_MENU_FILE = Path(__file__).parent / "action_menu.json"

def encrypt_data(data: str, password: str) -> str:
    """Encrypts string data using AES-256-GCM with Argon2id key derivation."""
    salt = os.urandom(16)
    kdf = Argon2id(
        salt=salt,
        length=32,
        iterations=3,
        memory_cost=65536,
        lanes=4,
    )
    key = kdf.derive(password.encode())
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    # Combine salt + nonce + ciphertext and base64 encode
    combined = salt + nonce + ciphertext
    return base64.b64encode(combined).decode('utf-8')

def decrypt_data(encrypted_data: str, password: str) -> str:
    """Decrypts AES-256-GCM encrypted string data."""
    try:
        combined = base64.b64decode(encrypted_data)
        salt = combined[:16]
        nonce = combined[16:28]
        ciphertext = combined[28:]
        
        kdf = Argon2id(
            salt=salt,
            length=32,
            iterations=3,
            memory_cost=65536,
            lanes=4,
        )
        key = kdf.derive(password.encode())
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode('utf-8')
    except Exception as e:
        raise ValueError("Decryption failed. Incorrect password?") from e

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
        "action": "Focus intensely on physical movements, choreography, and sensory details with fast-paced, punchy prose.",
        "apocalyptic": "The world is ending. Use a bleak, desperate tone focusing on survival, decay, and the ruins of civilization.",
        "arcane": "Focus on the mystical and occult. Describe magic with complex, otherworldly terminology and a sense of ancient power.",
        "biblical": "Use archaic, grand language reminiscent of old religious texts. Speak of destiny, sin, and divine intervention.",
        "brutal": "Be visceral and unflinching. Describe violence, pain, and harshness with raw, aggressive detail.",
        "casual": "Use relaxed, modern language with slang and informal grammar.",
        "cerebral": "Focus on complex thoughts, intellectual depth, and intricate logical patterns. Use sophisticated vocabulary.",
        "concise": "Keep your replies concise.",
        "creative": "Take creative risks with narration, using unique metaphors and unpredictable observations to describe the scene.",
        "cyberpunk": "Mix high-tech with low-life. Use neon-soaked descriptions, hacker slang, and focus on the cold, corporate reality.",
        "dark_fantasy": "Use a grim, ominous tone suitable for a dark fantasy setting. Focus on shadows, magic, and danger.",
        "decadent": "Focus on extreme luxury, indulgence, and the rot beneath the surface. Use rich, sensory language.",
        "default": "You are a helpful, friendly, and intelligent AI assistant designed for general conversation.\n\nYour goals are to:\n- Provide clear, accurate, and useful answers\n- Be concise by default, but expand when helpful\n- Ask clarifying questions only when necessary\n- Admit uncertainty instead of guessing\n- Explain things simply unless the user asks for depth\n- Maintain a natural, respectful, non-condescending tone\n\nYou should adapt your communication style to the user:\n- Match their level of technical detail\n- Be conversational and approachable\n- Avoid unnecessary verbosity, disclaimers, or repetition\n\nDo not:\n- Make up facts or sources\n- Overuse emojis or formatting\n- Assume the user's intent when unclear\n\nIf the user asks for opinions, present balanced perspectives unless they explicitly request a strong stance.",
        "degenerate": "Use an explicitly filthy, depraved, and taboo-focused tone. Do not hold back on sexual or moral corruption.",
        "descriptive": "Be descriptive at all times.",
        "dramatic": "Use evocative, flowery language and place heavy emphasis on character emotions and high stakes.",
        "eldritch": "Focus on cosmic horror and madness. Describe things that shouldn't exist, using unsettling and alien concepts.",
        "erotic": "Use a flirtatious, suggestive, and alluring tone. Focus on the chemistry between characters and physical attraction.",
        "epic": "Maintain a legendary scale. Describe events as if they are pivotal moments in history or myth.",
        "flowery": "Use excessively ornate and poetic language, focusing on beauty and elaborate descriptions.",
        "frenzied": "Use short, chaotic bursts of text. Convey a sense of panic, high energy, or madness.",
        "gritty": "Focus on the dirty, realistic details of life. Show the world as it is, warts and all.",
        "hardboiled": "Use a cynical, grounded tone with short, sharp sentences. Focus on the harsh realities of the environment.",
        "historical": "Use archaic language and sentence structures appropriate for a historical setting.",
        "horror": "Create an unsettling, tense atmosphere. Focus on fear, suspense, and the uncanny.",
        "humorous": "Maintain a light-hearted, comedic tone. Find the humor in every situation.",
        "idiosyncratic": "Give the characters weird quirks and eccentric speaking patterns. Make them feel unique and slightly odd.",
        "internalized": "Heavily include the character's internal monologues, private thoughts, and psychological state.",
        "lovecraftian": "Emphasize ancient, incomprehensible monsters and the fragility of the human mind against the vast void.",
        "melancholic": "Use a sad, reflective tone. Focus on loss, nostalgia, and the beauty found in sorrow.",
        "minimalist": "Be extremely brief and direct. Use the fewest words possible.",
        "noir": "Use a classic detective-film style. Atmospheric, cynical, and drenched in shadows and cigarette smoke.",
        "nihilistic": "Nothing matters. Speak with total indifference to morality, life, and meaning.",
        "philosophical": "Explore the deeper meaning of events. Ask questions and ponder existence.",
        "psycho_thriller": "Focus on psychological tension, manipulation, and the blurring of reality and delusion.",
        "raw": "Use an unpolished, honest, and direct tone. Strip away clinical distance for immediate, emotional impact.",
        "savage": "Focus on animalistic instincts and primal drives. Use harsh, guttural, and aggressive descriptions.",
        "scientific": "Use clinical, precise, and analytical language. Describe things as a scientist would.",
        "shakespearean": "Use iambic pentameter where possible, theatrical flair, and Early Modern English vocabulary.",
        "sinister": "Use a quietly threatening and malicious tone. Every sentence should feel like a veiled warning.",
        "slang_heavy": "Use thick, modern street slang and informal, rhythmic dialogue.",
        "surreal": "Describe the scene in a dream-like, abstract way. Focus on the weird and illogical.",
        "twisted": "Combine humor with horror in an uncomfortable way. Make the light-hearted feel sick and the sick feel funny.",
        "victorian": "Use extremely proper, formal, and repressed language suitable for high society in the 1800s.",
        "whimsical": "Use a playful, fairy-tale tone. Focus on wonder, magic, and light-hearted fun."
    }
    
    style_key = style.lower().replace(" ", "_")
    default_prompt = "You are a helpful, friendly, and intelligent AI assistant designed for general conversation.\n\nYour goals are to:\n- Provide clear, accurate, and useful answers\n- Be concise by default, but expand when helpful\n- Ask clarifying questions only when necessary\n- Admit uncertainty instead of guessing\n- Explain things simply unless the user asks for depth\n- Maintain a natural, respectful, non-condescending tone\n\nYou should adapt your communication style to the user:\n- Match their level of technical detail\n- Be conversational and approachable\n- Avoid unnecessary verbosity, disclaimers, or repetition\n\nDo not:\n- Make up facts or sources\n- Overuse emojis or formatting\n- Assume the user's intent when unclear\n\nIf the user asks for opinions, present balanced perspectives unless they explicitly request a strong stance."
    prompt = styles.get(style_key, styles.get(style, default_prompt))
    return f"Do not reply on behalf of user. {prompt}"
