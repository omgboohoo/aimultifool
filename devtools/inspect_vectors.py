import qdrant_client
from pathlib import Path
import json
import os

# Base directory for vectors relative to this script (go up one level from devtools/)
BASE_DIR = Path(__file__).parent.parent
VECTORS_DIR = BASE_DIR / "vectors"

def main():
    if not VECTORS_DIR.exists():
        print(f"Vectors directory not found at: {VECTORS_DIR}")
        return

    print("=" * 60)
    print(" VECTOR DATABASE ENCRYPTION CHECKER (Developer Tool) ")
    print("=" * 60)
    print(f"Scanning: {VECTORS_DIR}\n")

    # Sort to keep output consistent
    folders = sorted([f for f in VECTORS_DIR.iterdir() if f.is_dir()])
    
    if not folders:
        print("No vector databases found.")
        return

    for db_dir in folders:
        name = db_dir.name
        # The app places a hidden marker file if the DB is intended to be encrypted
        is_encrypted_marked = (db_dir / ".encrypted").exists()
        
        print(f"DATABASE: {name}")
        print(f"MARKER:   {'.encrypted FOUND' if is_encrypted_marked else 'NO ENCRYPTION MARKER'}")
        
        try:
            # Initialize Qdrant in local storage mode
            client = qdrant_client.QdrantClient(path=str(db_dir))
            collections = client.get_collections().collections
            
            if not collections:
                print("  [!] No collections found.")
            else:
                for coll in collections:
                    coll_name = coll.name
                    # Scroll to get the very first entry
                    points, _ = client.scroll(
                        collection_name=coll_name,
                        limit=1,
                        with_payload=True,
                        with_vectors=True
                    )
                    
                    if not points:
                        print(f"  [Collection: {coll_name}] - Empty")
                        continue
                    
                    point = points[0]
                    print(f"  [Collection: {coll_name}]")
                    
                    # 1. Show Vector
                    if point.vector is not None:
                        # Vectors are long, just show the start
                        dim = len(point.vector)
                        sample = [round(float(x), 4) for x in point.vector[:5]]
                        print(f"    First Vector (Dim {dim}): {sample}...")
                    else:
                        print("    First Vector: MISSING")
                        
                    # 2. Show Payload
                    print("    Payload Data:")
                    # Pretty print the JSON payload
                    # If 'text' is encrypted, it will look like a Base64 string blob
                    payload_str = json.dumps(point.payload, indent=6)
                    print(f"{payload_str}")
            
            client.close()
        except Exception as e:
            print(f"  [!] ERROR reading {name}: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    main()
