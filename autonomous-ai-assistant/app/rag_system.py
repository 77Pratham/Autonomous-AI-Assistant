import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import json

class RAGSystem:
    """
    Handles the Retrieval-Augmented Generation system.
    - Creates text embeddings using SentenceTransformer.
    - Stores and indexes embeddings using FAISS for fast similarity search.
    - Persists the index and document store to disk.
    """
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print("Initializing RAG System...")
        # 1. Load the sentence transformer model
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # 2. Setup paths for persistent storage
        self.index_path = "data/faiss_index/vector_index.faiss"
        self.doc_store_path = "data/faiss_index/doc_store.json"
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # 3. Load or initialize the FAISS index and document store
        self.load_index()
        print("RAG System initialized successfully.")

    def load_index(self):
        """Loads the FAISS index and document store from disk."""
        if os.path.exists(self.index_path) and os.path.exists(self.doc_store_path):
            print("Loading existing index and document store from disk.")
            self.index = faiss.read_index(self.index_path)
            with open(self.doc_store_path, 'r') as f:
                self.doc_store = json.load(f)
        else:
            print("No existing index found. Initializing a new one.")
            # Using IndexFlatL2 for basic L2 distance search
            self.index = faiss.IndexFlatL2(self.dimension)
            # A simple list to store the actual text documents
            self.doc_store = []

    def save_index(self):
        """Saves the FAISS index and document store to disk."""
        print("Saving index and document store to disk.")
        faiss.write_index(self.index, self.index_path)
        with open(self.doc_store_path, 'w') as f:
            json.dump(self.doc_store, f)

    def add_document(self, text: str):
        """
        Adds a document to the RAG system.
        - Creates an embedding for the text.
        - Adds the embedding to the FAISS index.
        - Stores the original text in the document store.
        """
        if not isinstance(text, str) or not text.strip():
            print("Warning: Attempted to add an empty or invalid document.")
            return

        # Create embedding
        embedding = self.model.encode([text], convert_to_tensor=False)
        
        # Add to FAISS index
        self.index.add(np.array(embedding, dtype=np.float32))
        
        # Add to document store
        self.doc_store.append(text)
        
        # Persist changes
        self.save_index()
        print(f"Document added successfully. Total documents: {len(self.doc_store)}")

    def retrieve(self, query: str, k: int = 3):
        """
        Retrieves the top-k most relevant documents for a given query.
        """
        if not isinstance(query, str) or not query.strip():
            return {"error": "Query must be a non-empty string."}
        
        if self.index.ntotal == 0:
            return {"message": "The knowledge base is empty. Add documents first."}

        # Create embedding for the query
        query_embedding = self.model.encode([query])
        
        # Search the index for the top k similar vectors
        distances, indices = self.index.search(np.array(query_embedding, dtype=np.float32), k)
        
        # Retrieve the corresponding documents
        results = [self.doc_store[i] for i in indices[0] if i < len(self.doc_store)]
        
        return {"results": results}