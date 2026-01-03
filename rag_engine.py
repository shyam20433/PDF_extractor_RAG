import os
import pickle
import time
import numpy as np
import faiss
import requests
from pypdf import PdfReader

# ================= CONFIG =================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CHUNKS_FILE = f"{DATA_DIR}/chunks.pkl"
META_FILE = f"{DATA_DIR}/metadata.pkl"
INDEX_FILE = f"{DATA_DIR}/vectors.index"

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"  # Fast, high-quality embedding model
LLM_MODEL = "llama3.2"  # For text generation

# =============== GLOBALS ==================
chunks = []
metadata = []
index = None

# =============== PDF LOAD =================
def load_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []

    for page_num, page in enumerate(reader.pages):
        pages.append({
            "text": page.extract_text(),
            "page": page_num + 1
        })

    return pages

# =============== CHUNKING =================
def create_chunks(pages, chunk_size=500, overlap=100):
    global chunks, metadata
    chunks, metadata = [], []

    full_text = "".join(p["text"] for p in pages)
    total_pages = len(pages)
    step = chunk_size - overlap

    for i in range(0, len(full_text), step):
        chunk = full_text[i:i + chunk_size]
        chunks.append(chunk)

        est_page = min(
            (i // (len(full_text) // total_pages)) + 1,
            total_pages
        )

        metadata.append({
            "start_pos": i,
            "estimated_page": est_page
        })

# =============== OLLAMA HELPERS =================
def get_ollama_embedding(text):
    """Get embedding from Ollama for a single text."""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text}
    )
    if response.status_code == 200:
        return response.json()["embedding"]
    else:
        raise Exception(f"Ollama embedding failed: {response.text}")

# =============== EMBEDDINGS =================
def build_faiss_index(progress_callback=None):
    global index

    embeddings = []
    total = len(chunks)
    
    for i, chunk in enumerate(chunks):
        print(f"Embedding {i+1}/{total}")
        emb = get_ollama_embedding(chunk)
        embeddings.append(emb)
        
        # Report progress
        if progress_callback:
            snippet = chunk[:40].replace('\n', ' ') + "..."
            progress_callback(i + 1, total, f"Embedding {i+1}/{total}: \"{snippet}\"")

    vectors = np.array(embeddings).astype("float32")
    dim = vectors.shape[1]

    index = faiss.IndexFlatL2(dim)
    index.add(vectors)

# =============== SAVE =================
def save_objects():
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)

    with open(META_FILE, "wb") as f:
        pickle.dump(metadata, f)

    faiss.write_index(index, INDEX_FILE)

# =============== LOAD =================
def load_objects():
    global chunks, metadata, index

    if not os.path.exists(CHUNKS_FILE):
        return False

    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)

    with open(META_FILE, "rb") as f:
        metadata = pickle.load(f)

    index = faiss.read_index(INDEX_FILE)
    return True

# =============== QA =================
def answer_question(question, socketio=None, top_k=3):
    # Get question embedding
    if socketio:
        socketio.emit('thinking', {'status': 'Analyzing question...'})
    
    query_emb = get_ollama_embedding(question)
    query_vec = np.array(query_emb).reshape(1, -1).astype("float32")
    
    # Search for similar chunks
    if socketio:
        socketio.emit('thinking', {'status': 'Searching document...'})
    
    scores, indices = index.search(query_vec, top_k)

    context_parts = []
    sources = []
    for idx in indices[0]:
        page = metadata[idx]["estimated_page"]
        chunk_text = chunks[idx]
        context_parts.append(f"[Page {page}]: {chunk_text}")
        sources.append({
            "page": page,
            "text": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
        })

    context = "\n\n".join(context_parts)

    # Generate answer using Ollama
    if socketio:
        socketio.emit('thinking', {'status': 'Generating answer...'})
    
    prompt = f"""You are a helpful AI assistant.
Answer the question based ONLY on the provided context.
If the context contains relevant information, summarize it to answer the question.
If the context is completely unrelated to the question, say "Not found in the document".

Context:
{context}

Question:
{question}

Answer:"""

    print(f"DEBUG: Requesting generation with model '{LLM_MODEL}'")
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        answer = response.json()["response"].strip()
        return answer, sources
    else:
        raise Exception(f"Ollama generation failed: {response.text}")
