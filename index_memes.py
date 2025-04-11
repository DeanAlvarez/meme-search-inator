import os
import sqlite3
import argparse
from PIL import Image
import easyocr
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
import faiss
from tqdm import tqdm # Optional: for a progress bar
import sys

# --- Configuration ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBEDDING_MODEL = 'clip-ViT-B-32'
OCR_LANGUAGES = ['en']
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')

# --- File/DB Names ---
DEFAULT_DB_FILE = 'meme_metadata.db'
DEFAULT_IMAGE_INDEX_FILE = 'image_embeddings.index'
DEFAULT_TEXT_INDEX_FILE = 'text_embeddings.index' # If storing text embeddings separately

# --- Model Initialization ---
try:
    print(f"Initializing models on device: {DEVICE}")
    print("Loading OCR model...")
    ocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=(DEVICE == "cuda"))
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
    EMBEDDING_DIM = None # Initialize to None

    try:
        # Attempt 1: Try the dedicated method first
        EMBEDDING_DIM = embedding_model.get_sentence_embedding_dimension()

        if EMBEDDING_DIM is not None:
            print(f"Embedding dimension obtained directly from model: {EMBEDDING_DIM}")

        # Attempt 2: If the first attempt returned None (or failed), try the manual calculation
        if EMBEDDING_DIM is None:
            print("get_sentence_embedding_dimension() returned None. Calculating manually...")
            sample_sentence = "Determine embedding dimension" # Use a simple, representative sentence
            try:
                # Generate an embedding for the sample sentence
                # Make sure the encode method returns a list, numpy array, or similar iterable
                sample_embedding = embedding_model.encode(sample_sentence)

                # Check if the result is usable (e.g., list, numpy array) and get its length
                if hasattr(sample_embedding, '__len__') and len(sample_embedding) > 0:
                    EMBEDDING_DIM = len(sample_embedding)
                    print(f"Embedding dimension calculated manually: {EMBEDDING_DIM}")
                elif hasattr(sample_embedding, 'shape') and len(sample_embedding.shape) > 0: # Handle tensors/arrays
                    # Assuming the dimension is the size of the last axis for multi-dim tensors,
                    # or the only axis for 1D tensors/arrays. Adjust if needed.
                    EMBEDDING_DIM = sample_embedding.shape[-1]
                    print(f"Embedding dimension calculated manually from shape: {EMBEDDING_DIM}")
                else:
                    print("Error: Manual embedding calculation returned an invalid or empty result.")
                    # EMBEDDING_DIM remains None

            except Exception as e:
                print(f"Error during manual embedding calculation: {e}")
                # EMBEDDING_DIM remains None

    except AttributeError as e:
        print(f"Error: The embedding model might be missing a required method: {e}")
        # EMBEDDING_DIM remains None
    except Exception as e:
        print(f"An unexpected error occurred while getting embedding dimension: {e}")
        # EMBEDDING_DIM remains None


    # --- Post-determination check ---
    if EMBEDDING_DIM is None:
        print("WARNING: Could not determine embedding dimension using either method.")
        raise ValueError("Failed to determine embedding dimension.")

    else:
        print(f"Final Embedding Dimension set to: {EMBEDDING_DIM}")

    print("Models loaded successfully.")
except Exception as e:
    print(f"Error loading models: {e}")
    sys.exit(1)

# --- Database Setup ---
def setup_database(db_file):
    """Connects to or creates the SQLite DB and sets up the necessary tables."""
    print(f"Setting up database: {db_file}")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create main table for metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memes (
            id INTEGER PRIMARY KEY,
            image_path TEXT UNIQUE NOT NULL,
            ocr_text TEXT
        )
    ''')

    # Create FTS5 table for efficient text search on ocr_text
    # Note: content='' makes it an external content FTS table referencing 'memes'
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memes_fts USING fts5(
            ocr_text,
            content='memes',
            content_rowid='id'
        )
    ''')

    # Triggers to keep FTS table synchronized with the main memes table
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS memes_ai AFTER INSERT ON memes BEGIN
            INSERT INTO memes_fts (rowid, ocr_text) VALUES (new.id, new.ocr_text);
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS memes_ad AFTER DELETE ON memes BEGIN
            DELETE FROM memes_fts WHERE rowid=old.id;
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS memes_au AFTER UPDATE ON memes BEGIN
            UPDATE memes_fts SET ocr_text=new.ocr_text WHERE rowid=old.id;
        END;
    ''')

    conn.commit()
    print("Database setup complete.")
    return conn, cursor

# --- Core Functions ---
def extract_ocr_text(image_path, reader):
    """Extracts text from an image using easyocr."""
    try:
        result = reader.readtext(image_path, detail=0, paragraph=True)
        return " ".join(result)
    except Exception as e:
        print(f"Warning: OCR failed for {os.path.basename(image_path)}: {e}", file=sys.stderr)
        return ""

def generate_embeddings(image_path, ocr_text, model):
    """Generates image and text embeddings as float32 NumPy arrays."""
    image_embedding_np = None
    text_embedding_np = None

    # Generate image embedding
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Encode returns a NumPy array. Ensure it's float32 for Faiss.
        image_embedding_np = model.encode(img).astype(np.float32)
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"Warning: Image embedding failed for {os.path.basename(image_path)}: {e}", file=sys.stderr)
        # Proceed to text embedding

    # Generate text embedding
    try:
        text_to_embed = ocr_text if ocr_text else "" # Embed empty string if no OCR text
        # Ensure it's float32 for Faiss
        text_embedding_np = model.encode(text_to_embed).astype(np.float32)
    except Exception as e:
        print(f"Warning: Text embedding failed for {os.path.basename(image_path)}: {e}", file=sys.stderr)
        # Keep image embedding if it succeeded

    return image_embedding_np, text_embedding_np

def index_directory(image_dir, db_file, image_index_file, text_index_file):
    """Indexes images: metadata to SQLite, embeddings to Faiss."""
    conn, cursor = None, None
    try:
        conn, cursor = setup_database(db_file)
    except sqlite3.Error as e:
        print(f"Database error during setup: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning directory: {image_dir}")
    image_files = [
        f for f in os.listdir(image_dir)
        if os.path.isfile(os.path.join(image_dir, f)) and f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]

    if not image_files:
        print("No supported image files found in the directory.")
        if conn: conn.close()
        return

    print(f"Found {len(image_files)} supported images. Starting indexing...")

    ids_list = []
    image_embeddings_list = []
    text_embeddings_list = []

    processed_count = 0
    skipped_count = 0

    for filename in tqdm(image_files, desc="Indexing Images"):
        image_path = os.path.join(image_dir, filename)
        row_id = None

        try:
            # 1. Extract OCR Text
            ocr_text = extract_ocr_text(image_path, ocr_reader)

            # 2. Insert metadata and get ID (handle duplicates)
            try:
                cursor.execute("INSERT INTO memes (image_path, ocr_text) VALUES (?, ?)", (image_path, ocr_text))
                row_id = cursor.lastrowid
                conn.commit() # Commit after each successful insert
            except sqlite3.IntegrityError: # UNIQUE constraint failed (image_path already exists)
                print(f"Warning: Image already indexed, skipping: {filename}", file=sys.stderr)
                # Optionally: Update existing record's OCR text if needed
                # cursor.execute("UPDATE memes SET ocr_text = ? WHERE image_path = ?", (ocr_text, image_path))
                # conn.commit()
                # cursor.execute("SELECT id FROM memes WHERE image_path = ?", (image_path,))
                # existing_id = cursor.fetchone()
                # if existing_id: row_id = existing_id[0] ... # More complex update logic needed if re-indexing embeddings
                skipped_count += 1
                continue # Skip processing embeddings for duplicates for now
            except sqlite3.Error as e:
                 print(f"Error inserting metadata for {filename}: {e}", file=sys.stderr)
                 skipped_count += 1
                 continue # Skip this file

            # 3. Generate Embeddings (only if metadata insert was successful)
            if row_id is not None:
                image_embedding, text_embedding = generate_embeddings(image_path, ocr_text, embedding_model)

                # Store embeddings only if image embedding succeeded
                if image_embedding is not None:
                    ids_list.append(row_id)
                    image_embeddings_list.append(image_embedding)
                    # Store text embedding if it also succeeded, otherwise maybe a zero vector or skip?
                    # Storing a corresponding entry is needed to keep lists aligned.
                    if text_embedding is not None:
                        text_embeddings_list.append(text_embedding)
                    else:
                        # Append a zero vector of the correct dimension if text embed failed
                        text_embeddings_list.append(np.zeros(EMBEDDING_DIM, dtype=np.float32))
                    processed_count += 1
                else:
                    print(f"Skipping embeddings for {filename} due to image embedding failure.", file=sys.stderr)
                    # We might have inserted metadata but won't have embeddings for it.
                    # Could delete the metadata row here, or just leave it. Leaving it is simpler.
                    skipped_count += 1

        except Exception as e:
            print(f"Unexpected error processing {filename}: {e}", file=sys.stderr)
            skipped_count += 1
            if conn: conn.rollback() # Rollback potential failed transaction for this file

    print(f"\nMetadata processing complete. Processed: {processed_count}, Skipped/Duplicates: {skipped_count}")

    # --- Build and Save Faiss Index ---
    if not ids_list:
        print("No new embeddings were generated. Skipping Faiss index creation.")
        if conn: conn.close()
        return

    print("Building Faiss indices...")
    try:
        # Convert lists to NumPy arrays
        ids_np = np.array(ids_list)
        image_embeddings_np = np.array(image_embeddings_list).astype(np.float32)
        text_embeddings_np = np.array(text_embeddings_list).astype(np.float32)

        # --- Image Index ---
        print(f"Building Image embedding index ({len(ids_list)} vectors)...")
        # Use IndexFlatL2 for exact search, wrapped in IndexIDMap
        index_flat_img = faiss.IndexFlatL2(EMBEDDING_DIM)
        image_index = faiss.IndexIDMap(index_flat_img)
        image_index.add_with_ids(image_embeddings_np, ids_np)
        print(f"Saving Image index to {image_index_file}...")
        faiss.write_index(image_index, image_index_file)

        # --- Text Index ---
        print(f"Building Text embedding index ({len(ids_list)} vectors)...")
         # Use IndexFlatL2 for exact search, wrapped in IndexIDMap
        index_flat_text = faiss.IndexFlatL2(EMBEDDING_DIM)
        text_index = faiss.IndexIDMap(index_flat_text)
        text_index.add_with_ids(text_embeddings_np, ids_np)
        print(f"Saving Text index to {text_index_file}...")
        faiss.write_index(text_index, text_index_file)

        print("Faiss indices built and saved successfully.")

    except Exception as e:
        print(f"Error building or saving Faiss index: {e}", file=sys.stderr)
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index meme images: metadata to SQLite, embeddings to Faiss.")
    parser.add_argument("image_dir", help="Directory containing meme images.")
    parser.add_argument("--db", default=DEFAULT_DB_FILE,
                        help=f"SQLite database file (default: {DEFAULT_DB_FILE})")
    parser.add_argument("--img-idx", default=DEFAULT_IMAGE_INDEX_FILE,
                        help=f"Output Faiss index file for images (default: {DEFAULT_IMAGE_INDEX_FILE})")
    parser.add_argument("--txt-idx", default=DEFAULT_TEXT_INDEX_FILE,
                        help=f"Output Faiss index file for text (default: {DEFAULT_TEXT_INDEX_FILE})")

    args = parser.parse_args()

    if not os.path.isdir(args.image_dir):
        print(f"Error: Directory not found at {args.image_dir}", file=sys.stderr)
        sys.exit(1)

    index_directory(args.image_dir, args.db, args.img_idx, args.txt_idx)

    print("Indexing process finished.")