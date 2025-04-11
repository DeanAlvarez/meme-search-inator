import os
import sqlite3
import argparse
import time
import json
import sys
from flask import Flask, request, jsonify, g, send_from_directory, abort
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

# --- Global Variables ---
config = {}
app = Flask(__name__)
embedding_model = None
image_index = None
text_index = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Config Loading ---
# (load_config function remains the same)
def load_config(config_path):
    """Loads configuration from a JSON file."""
    global config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        required_keys = ["database_file", "image_index_file", "text_index_file", "embedding_model", "search_params", "server"]
        if not all(key in config for key in required_keys):
            raise ValueError("Config file missing one or more required keys.")
        if not all(key in config["search_params"] for key in ["k_keyword", "k_vector", "max_results", "rrf_k"]):
             raise ValueError("Config file missing one or more required search_params keys.")
        if not all(key in config["server"] for key in ["host", "port"]):
             raise ValueError("Config file missing one or more required server keys.")
        print(f"Configuration loaded successfully from {config_path}")
        return True
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        return False
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from configuration file {config_path}", file=sys.stderr)
        return False
    except ValueError as e:
        print(f"Error: Invalid configuration: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred loading config: {e}", file=sys.stderr)
        return False


# --- Model & Index Loading ---
# (load_resources function remains the same)
def load_resources():
    """Loads the embedding model and Faiss indices based on loaded config."""
    global embedding_model, image_index, text_index
    if not config:
        print("Error: Configuration not loaded. Cannot load resources.", file=sys.stderr)
        return False
    print("Loading resources...")
    embedding_model_name = config.get("embedding_model")
    image_index_path = config.get("image_index_file")
    text_index_path = config.get("text_index_file")
    try:
        print(f"Loading embedding model: {embedding_model_name} on {DEVICE}")
        embedding_model = SentenceTransformer(embedding_model_name, device=DEVICE)
        print("Embedding model loaded.")
        print(f"Loading Faiss image index from: {image_index_path}")
        if os.path.exists(image_index_path):
            image_index = faiss.read_index(image_index_path)
            print(f"Image index loaded. Total vectors: {image_index.ntotal}")
        else:
            print(f"Warning: Image index file not found at {image_index_path}. Image vector search disabled.", file=sys.stderr)
            image_index = None
        print(f"Loading Faiss text index from: {text_index_path}")
        if os.path.exists(text_index_path):
            text_index = faiss.read_index(text_index_path)
            print(f"Text index loaded. Total vectors: {text_index.ntotal}")
        else:
             print(f"Warning: Text index file not found at {text_index_path}. Text vector search disabled.", file=sys.stderr)
             text_index = None
        if image_index is None and text_index is None:
             print("Warning: Both Faiss indices failed to load. Vector search will not function.", file=sys.stderr)
        return True
    except Exception as e:
        print(f"FATAL ERROR loading resources: {e}", file=sys.stderr)
        return False

# --- Database Connection Handling ---
# (get_db and close_db remain the same)
def get_db():
    if 'db' not in g:
        db_path = config.get("database_file")
        if not db_path:
            app.logger.error("Database file path not found in configuration.")
            return None
        try:
            g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            app.logger.error(f"Error connecting to database {db_path}: {e}")
            return None
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Search Functions ---
# (keyword_search_fts, vector_search_faiss, reciprocal_rank_fusion remain the same)
def keyword_search_fts(query_text):
    db = get_db()
    if not db: return []
    k = config["search_params"]["k_keyword"]
    start_time = time.time()
    results = []
    try:
        cursor = db.execute(
            "SELECT rowid as id, rank FROM memes_fts WHERE memes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query_text, k)
        )
        results = [(row['id'], 1.0 / (row['rank'] + 1e-6)) for row in cursor.fetchall()]
        app.logger.debug(f"FTS search found {len(results)} results.")
    except sqlite3.Error as e:
        app.logger.error(f"FTS Keyword search error: {e}")
    duration = time.time() - start_time
    app.logger.info(f"Keyword search took {duration:.4f} seconds.")
    return results

def vector_search_faiss(query_embedding, index):
    if index is None or query_embedding is None:
        app.logger.warning("Vector search skipped: Index or query embedding unavailable.")
        return []
    k = config["search_params"]["k_vector"]
    start_time = time.time()
    try:
        distances, ids = index.search(np.array([query_embedding]).astype(np.float32), k)
        valid_indices = ids[0] != -1
        ids = ids[0][valid_indices]
        distances = distances[0][valid_indices]
        scores = 1.0 / (1.0 + distances + 1e-6)
        results = list(zip(ids.tolist(), scores.tolist()))
        app.logger.debug(f"Vector search found {len(results)} results.")
    except Exception as e:
        app.logger.error(f"Faiss Vector search error: {e}")
        results = []
    duration = time.time() - start_time
    app.logger.info(f"Vector search took {duration:.4f} seconds.")
    return results

def reciprocal_rank_fusion(*results_lists):
    fused_scores = {}
    rrf_k = config["search_params"]["rrf_k"]
    app.logger.debug(f"Starting RRF fusion with {len(results_lists)} lists (k={rrf_k}).")
    for results in results_lists:
        if not results: continue
        for rank, (doc_id, _) in enumerate(results):
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0
            fused_scores[doc_id] += 1.0 / (rrf_k + rank)
    reranked_results = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    app.logger.debug(f"RRF resulted in {len(reranked_results)} fused results.")
    return reranked_results


# --- Flask Routes ---
@app.route('/search', methods=['GET'])
# (Search route remains the same)
def search():
    start_time_total = time.time()
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    if not embedding_model:
         return jsonify({"error": "Search resources not loaded properly (model missing)"}), 500
    if image_index is None and text_index is None:
         app.logger.warning("Both Faiss indices are unavailable.")
    app.logger.info(f"Received search query: '{query}'")
    try:
        query_embedding = embedding_model.encode(query).astype(np.float32)
    except Exception as e:
        app.logger.error(f"Failed to encode query '{query}': {e}")
        return jsonify({"error": "Failed to process query embedding"}), 500
    keyword_results = keyword_search_fts(query)
    image_vector_results = vector_search_faiss(query_embedding, image_index)
    text_vector_results = vector_search_faiss(query_embedding, text_index)
    fused_results = reciprocal_rank_fusion(
        keyword_results,
        image_vector_results,
        text_vector_results
    )
    max_results = config["search_params"]["max_results"]
    top_ids = [doc_id for doc_id, score in fused_results[:max_results]]
    final_results = []
    if top_ids:
        db = get_db()
        if db:
            try:
                placeholders = ','.join('?' * len(top_ids))
                query_sql = f"SELECT id, image_path, ocr_text FROM memes WHERE id IN ({placeholders})"
                cursor = db.execute(query_sql, top_ids)
                rows_dict = {row['id']: dict(row) for row in cursor.fetchall()}
                for doc_id, score in fused_results[:max_results]:
                    if doc_id in rows_dict:
                        result_item = rows_dict[doc_id]
                        result_item['score'] = score
                        final_results.append(result_item)
            except sqlite3.Error as e:
                app.logger.error(f"Error retrieving metadata from DB: {e}")
                return jsonify({"error": "Failed to retrieve result metadata"}), 500
        else:
             return jsonify({"error": "Database connection failed"}), 500
    duration_total = time.time() - start_time_total
    app.logger.info(f"Total search request took {duration_total:.4f} seconds.")
    return jsonify({
        "query": query,
        "results_count": len(final_results),
        "results": final_results
        })


# --- Image Serving Route ---
# (serve_image route remains the same)
@app.route('/images/<int:image_id>')
def serve_image(image_id):
    db = get_db()
    image_path = None
    if db:
        try:
            cursor = db.execute("SELECT image_path FROM memes WHERE id = ?", (image_id,))
            row = cursor.fetchone()
            if row:
                image_path = row['image_path']
            else:
                app.logger.warning(f"Image ID {image_id} not found in database.")
                abort(404)
        except sqlite3.Error as e:
            app.logger.error(f"Database error retrieving path for image ID {image_id}: {e}")
            abort(500)
    else:
        app.logger.error("Database connection unavailable for image serving.")
        abort(500)
    if image_path and os.path.exists(image_path):
        try:
            directory = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            app.logger.debug(f"Serving image: Directory='{directory}', Filename='{filename}'")
            return send_from_directory(directory, filename)
        except FileNotFoundError:
             app.logger.error(f"Image file not found at path: {image_path} (from DB for ID {image_id})")
             abort(404)
        except Exception as e:
            app.logger.error(f"Error serving file {image_path}: {e}")
            abort(500)
    else:
        app.logger.error(f"Image path {image_path} invalid or file missing for ID {image_id}.")
        abort(404)


# --- Simple HTML Frontend Route (Updated JS for Clickable Images) ---
@app.route('/', methods=['GET'])
def index():
    """Serves a simple HTML page for searching."""
    # UPDATED: Wrapped image in an anchor tag
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Meme Search</title>
        <style>
            body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; }
            #results { margin-top: 20px; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
            .result-item {
                background-color: #fff;
                border: 1px solid #ddd;
                padding: 10px;
                text-align: center;
                word-wrap: break-word;
                font-size: 0.8em;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                cursor: pointer; /* Indicate it's clickable */
                transition: transform 0.2s ease-in-out;
            }
            .result-item:hover {
                 transform: scale(1.03); /* Slight zoom on hover */
                 border-color: #aaa;
            }
            .result-item img {
                max-width: 100%;
                height: auto;
                display: block;
                margin-bottom: 5px;
                flex-shrink: 0;
            }
            /* Style anchor tag like a block element */
            .result-item a {
                display: block;
                text-decoration: none; /* Remove underline */
                color: inherit; /* Inherit text color */
            }
            .result-item p { margin: 2px 0; }
            input[type=text] { padding: 10px; width: 300px; margin-right: 5px; }
            button { padding: 10px; }
            .loader { display: none; }
            .loading .loader { display: inline-block; margin-left: 10px; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <h1>Meme Search</h1>
        <form id="search-form">
            <input type="text" id="query" name="q" placeholder="Enter search terms...">
            <button type="submit">Search</button>
            <div class="loader"></div>
        </form>
        <div id="results"></div>

        <script>
            const form = document.getElementById('search-form');
            const resultsDiv = document.getElementById('results');
            const loader = form.querySelector('.loader');

            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const query = document.getElementById('query').value;
                if (!query) return;

                resultsDiv.innerHTML = '';
                loader.style.display = 'inline-block';
                form.classList.add('loading');

                try {
                    const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
                    if (!response.ok) {
                        let errorMsg = `HTTP error! status: ${response.status}`;
                        try {
                            const errorData = await response.json();
                            errorMsg = errorData.error || errorMsg;
                        } catch(e) { /* Ignore if response isn't JSON */ }
                        throw new Error(errorMsg);
                    }
                    const data = await response.json();

                    if (data.results && data.results.length > 0) {
                        data.results.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'result-item';
                            console.log(`Creating item for ID: ${item.id}, Image link: /images/${item.id}`); // Debug log

                            // *** WRAP IMAGE IN ANCHOR TAG ***
                            div.innerHTML = `
                                <a href="/images/${item.id}" target="_blank" title="Click to open image in new tab">
                                    <img src="/images/${item.id}" alt="Meme ${item.id}" loading="lazy">
                                </a>
                                <div>
                                    <p>ID: ${item.id}</p>
                                    <p>Score: ${item.score.toFixed(4)}</p>
                                    <p title="${item.ocr_text || ''}">OCR: ${(item.ocr_text || 'N/A').substring(0, 50)}${ (item.ocr_text && item.ocr_text.length > 50) ? '...' : ''}</p>
                                </div>
                            `;
                            // Add error handling for image loading (applies to the img tag inside the link)
                             const imgElement = div.querySelector('img');
                             if (imgElement) {
                                imgElement.onerror = function() {
                                    this.alt = `Image ID ${item.id} failed to load`;
                                    this.style.border = '1px dashed red';
                                    // Add error text *after* the image (which is inside the 'a' tag)
                                    this.parentElement.insertAdjacentHTML('afterend', '<p style="color:red; font-size:0.8em;">Load Error</p>');
                                };
                             } else {
                                 console.error("Could not find img element after setting innerHTML for ID:", item.id);
                             }

                            resultsDiv.appendChild(div);
                        });
                    } else {
                        resultsDiv.innerHTML = '<p>No results found.</p>';
                    }
                } catch (error) {
                    console.error('Search failed:', error);
                    resultsDiv.innerHTML = `<p>Search failed: ${error.message}. Check console for details.</p>`;
                } finally {
                     loader.style.display = 'none';
                     form.classList.remove('loading');
                }
            });
        </script>
    </body>
    </html>
    """

# --- Main Execution ---
# (Main block remains the same)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Meme Search Flask App")
    parser.add_argument("config_file", help="Path to the JSON configuration file.")
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode (overrides config)')
    args = parser.parse_args()
    if not load_config(args.config_file):
        sys.exit(1)
    if not load_resources():
         sys.exit(1)
    server_host = config.get("server", {}).get("host", "127.0.0.1")
    server_port = config.get("server", {}).get("port", 5000)
    debug_mode = args.debug
    print(f"Starting Flask app on http://{server_host}:{server_port} (Debug: {debug_mode})")
    use_reloader = debug_mode
    app.run(host=server_host, port=server_port, debug=debug_mode, use_reloader=use_reloader)