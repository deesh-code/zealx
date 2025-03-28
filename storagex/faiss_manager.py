import faiss
import numpy as np
import os

STORAGE_DIR = "storagex_data"
FAISS_INDEX_PATH = os.path.join(STORAGE_DIR, "faiss.index")

os.makedirs(STORAGE_DIR, exist_ok=True)

def init_faiss(dim=512):
    """Initialize or load FAISS index (disk-based)."""
    if os.path.exists(FAISS_INDEX_PATH):
        index = faiss.read_index(FAISS_INDEX_PATH)
    else:
        index = faiss.IndexFlatL2(dim)
        faiss.write_index(index, FAISS_INDEX_PATH)
    return index

def add_faiss_embedding(vector):
    """Add a new vector to FAISS index."""
    index = init_faiss(len(vector))
    index.add(np.array([vector]).astype('float32'))
    faiss.write_index(index, FAISS_INDEX_PATH)

def search_faiss_embedding(query_vector, top_k=3):
    """Search for similar vectors in FAISS."""
    index = init_faiss(len(query_vector))
    D, I = index.search(np.array([query_vector]).astype('float32'), top_k)
    return I[0]
