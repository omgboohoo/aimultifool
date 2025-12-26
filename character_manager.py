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

def write_chara_metadata(png_path, metadata_json):
    """Write character metadata back to SillyTavern PNG card"""
    try:
        # Convert metadata to JSON and then to Base64
        json_str = json.dumps(metadata_json)
        b64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

        with open(png_path, 'rb') as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                return False
            
            chunks = []
            while True:
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                length = struct.unpack(">I", length_bytes)[0]
                chunk_type = f.read(4)
                chunk_data = f.read(length)
                crc = f.read(4) # read but we will recalculate
                chunks.append((chunk_type, chunk_data))
                if chunk_type == b'IEND':
                    break
        
        # Filter out existing chara chunks and find where to insert
        new_chunks = []
        inserted = False
        compressed_data = zlib.compress(b64_data.encode('utf-8'))
        # zTXt chunk data format: keyword (null-terminated) + compression method (1 byte) + compressed data
        new_chara_data = b'chara\x00\x00' + compressed_data

        for c_type, c_data in chunks:
            if c_type in (b'tEXt', b'zTXt'):
                keyword = c_data.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
                if keyword == 'chara':
                    continue # Skip old chara chunks
            
            # Insert before first IDAT or if we reach IEND
            if not inserted and c_type in (b'IDAT', b'IEND'):
                new_chunks.append((b'zTXt', new_chara_data))
                inserted = True
            
            new_chunks.append((c_type, c_data))
        
        if not inserted:
             # Fallback if no IDAT found (unlikely for valid PNG)
             new_chunks.insert(-1, (b'zTXt', new_chara_data))

        # Write back to file
        with open(png_path, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n')
            for c_type, c_data in new_chunks:
                f.write(struct.pack(">I", len(c_data)))
                f.write(c_type)
                f.write(c_data)
                crc = zlib.crc32(c_type + c_data) & 0xffffffff
                f.write(struct.pack(">I", crc))
        
        return True
    except Exception as e:
        print(f"Error writing metadata: {e}")
        return False

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
