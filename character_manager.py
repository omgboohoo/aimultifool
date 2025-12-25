import json
import re
import zlib
import base64
import struct

def extract_chara_metadata(png_path):
    """Extract character metadata from SillyTavern PNG card"""
    try:
        with open(png_path, 'rb') as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                return None
            while True:
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                length = struct.unpack(">I", length_bytes)[0]
                chunk_type = f.read(4)
                chunk_data = f.read(length)
                f.read(4)
                if chunk_type == b'tEXt':
                    keyword, _, text = chunk_data.partition(b'\x00')
                    if keyword.decode('utf-8') == 'chara':
                        return base64.b64decode(text).decode('utf-8')
                elif chunk_type == b'zTXt':
                    keyword, rest = chunk_data.split(b'\x00', 1)
                    if keyword.decode('utf-8') == 'chara':
                        compression_method = rest[0]
                        if compression_method == 0:
                            compressed_text = rest[1:]
                            decompressed = zlib.decompress(compressed_text)
                            return base64.b64decode(decompressed).decode('utf-8')
    except Exception:
        return None
    return None

def process_character_metadata(chara_json, user_name):
    """
    Processes the character metadata and returns the character object and prompts.
    """
    try:
        # Replace {{user}} with the user's name, case-insensitive
        chara_json_processed = re.sub(r'\{\{user\}\}', user_name, chara_json, flags=re.IGNORECASE)
        chara_obj = json.loads(chara_json_processed)
        
        # Simplified processing
        talk_prompt = chara_obj.get("talk_prompt", "")
        depth_prompt = chara_obj.get("depth_prompt", "")
        return chara_obj, talk_prompt, depth_prompt
    except Exception:
        return None, None, None

def create_initial_messages(chara_obj, user_name):
    """Creates initial system message from character object."""
    chara_json_str = json.dumps(chara_obj)
    chara_json_processed = re.sub(r'\{\{user\}\}', user_name, chara_json_str, flags=re.IGNORECASE)
    chara_obj_processed = json.loads(chara_json_processed)
    
    talk_prompt = chara_obj_processed.get("talk_prompt", "")
    depth_prompt = chara_obj_processed.get("depth_prompt", "")
    data_section = chara_obj_processed.get('data', chara_obj_processed)
    modified_data_json_string = json.dumps(data_section)
    
    system_prompt = f"{talk_prompt}{depth_prompt}roleplay the following scene defined in the json. do not break from your character\n{modified_data_json_string}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": ""}
    ]
