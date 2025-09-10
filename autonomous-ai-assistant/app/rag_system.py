import faiss
import numpy as np
import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RAGSystem:
    """
    Handles the Retrieval-Augmented Generation system with fallback options.
    - Creates text embeddings using SentenceTransformer or fallback methods.
    - Stores and indexes embeddings using FAISS for fast similarity search.
    - Persists the index and document store to disk.
    - Enhanced with better error handling and fallback models.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', data_dir: str = "data/faiss_index"):
        """
        Initialize the RAG system with fallback options.
        
        Args:
            model_name: Name of the sentence transformer model
            data_dir: Directory to store the FAISS index and documents
        """
        logger.info("Initializing RAG System...")
        
        self.model_name = model_name
        self.data_dir = data_dir
        self.model = None
        self.dimension = None
        self.use_fallback = False
        
        # Try to load SentenceTransformer with fallback
        self._initialize_model()
        
        # 2. Setup paths for persistent storage
        os.makedirs(self.data_dir, exist_ok=True)
        self.index_path = os.path.join(self.data_dir, "vector_index.faiss")
        self.doc_store_path = os.path.join(self.data_dir, "doc_store.json")
        self.metadata_path = os.path.join(self.data_dir, "metadata.json")

        # 3. Initialize storage containers
        self.index = None
        self.doc_store = []
        self.metadata = {"total_docs": 0, "model_name": model_name}

        # 4. Load or initialize the FAISS index and document store
        self.load_index()
        
        logger.info("RAG System initialized successfully")

    def _initialize_model(self):
        """Initialize the embedding model with fallback options."""
        # Try SentenceTransformer first
        try:
            logger.info(f"Attempting to load SentenceTransformer model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name, cache_folder=None)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"SentenceTransformer model loaded successfully. Embedding dimension: {self.dimension}")
            return
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer model: {e}")
        
        # Fallback 1: Try smaller/different model
        try:
            logger.info("Trying fallback model: all-MiniLM-L6-v2 with different settings...")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Fallback SentenceTransformer loaded. Dimension: {self.dimension}")
            return
        except Exception as e:
            logger.warning(f"Fallback SentenceTransformer failed: {e}")
        
        # Fallback 2: Use simple TF-IDF or basic embeddings
        try:
            logger.info("Using simple TF-IDF fallback for embeddings...")
            self._setup_tfidf_fallback()
            self.use_fallback = True
            self.dimension = 300  # Fixed dimension for TF-IDF
            logger.info("TF-IDF fallback initialized successfully")
            return
        except Exception as e:
            logger.error(f"All fallback options failed: {e}")
            raise RuntimeError("Could not initialize any embedding model")

    def _setup_tfidf_fallback(self):
        """Setup TF-IDF as a simple fallback."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            
            self.tfidf = TfidfVectorizer(max_features=1000, stop_words='english')
            self.svd = TruncatedSVD(n_components=300)  # Reduce to 300 dimensions
            self.fallback_fitted = False
            logger.info("TF-IDF fallback components initialized")
        except ImportError:
            logger.error("scikit-learn not available for TF-IDF fallback")
            raise

    def _encode_fallback(self, texts: List[str]) -> np.ndarray:
        """Encode texts using TF-IDF fallback."""
        if not self.use_fallback:
            return self.model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
        
        # Use TF-IDF fallback
        if not self.fallback_fitted:
            # First time: fit the transformers
            if len(self.doc_store) > 0:
                # Use existing documents to fit
                tfidf_matrix = self.tfidf.fit_transform(self.doc_store + texts)
                self.svd.fit(tfidf_matrix)
                self.fallback_fitted = True
                # Transform only the new texts
                new_tfidf = self.tfidf.transform(texts)
                return self.svd.transform(new_tfidf).astype(np.float32)
            else:
                # No existing documents, fit on current texts
                tfidf_matrix = self.tfidf.fit_transform(texts)
                embeddings = self.svd.fit_transform(tfidf_matrix)
                self.fallback_fitted = True
                return embeddings.astype(np.float32)
        else:
            # Already fitted, just transform
            tfidf_matrix = self.tfidf.transform(texts)
            return self.svd.transform(tfidf_matrix).astype(np.float32)

    def load_index(self) -> None:
        """Load the FAISS index and document store from disk."""
        try:
            if (os.path.exists(self.index_path) and 
                os.path.exists(self.doc_store_path) and 
                os.path.getsize(self.index_path) > 0):
                
                logger.info("Loading existing index and document store from disk")
                
                # Load FAISS index
                self.index = faiss.read_index(self.index_path)
                
                # Load document store
                with open(self.doc_store_path, 'r', encoding='utf-8') as f:
                    self.doc_store = json.load(f)
                
                # Load metadata if exists
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
                
                # Update dimension from loaded index
                if self.index.d != self.dimension:
                    logger.warning(f"Loaded index dimension ({self.index.d}) differs from model dimension ({self.dimension})")
                    self.dimension = self.index.d
                
                logger.info(f"Loaded {len(self.doc_store)} documents from existing index")
            
            else:
                logger.info("No existing index found or index is empty. Initializing a new one")
                self._initialize_new_index()
                
        except Exception as e:
            logger.error(f"Error loading index: {e}. Initializing a new one")
            self._initialize_new_index()

    def _initialize_new_index(self) -> None:
        """Initialize a new empty FAISS index."""
        try:
            if self.dimension is None:
                logger.error("Cannot initialize index: dimension not set")
                raise ValueError("Dimension not set")
            
            # Using IndexFlatL2 for basic L2 distance search
            self.index = faiss.IndexFlatL2(self.dimension)
            self.doc_store = []
            self.metadata = {"total_docs": 0, "model_name": self.model_name, "use_fallback": self.use_fallback}
            logger.info(f"New FAISS index initialized with dimension {self.dimension}")
        except Exception as e:
            logger.error(f"Failed to initialize new index: {e}")
            raise

    def save_index(self) -> bool:
        """Save the FAISS index and document store to disk."""
        try:
            logger.info("Saving index and document store to disk")
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save document store
            with open(self.doc_store_path, 'w', encoding='utf-8') as f:
                json.dump(self.doc_store, f, ensure_ascii=False, indent=2)
            
            # Update and save metadata
            self.metadata.update({
                "total_docs": len(self.doc_store),
                "use_fallback": self.use_fallback,
                "dimension": self.dimension
            })
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info("Index and document store saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            return False

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a document to the RAG system."""
        if not isinstance(text, str) or not text.strip():
            logger.warning("Attempted to add an empty or invalid document")
            return False

        try:
            text = text.strip()
            
            # Check for duplicates
            if text in self.doc_store:
                logger.info("Document already exists in the store")
                return True
            
            logger.info(f"Adding document: '{text[:100]}...' (length: {len(text)})")
            
            # Create embedding with fallback support
            embedding = self._encode_fallback([text])
            
            # Ensure embedding is the right shape and type
            embedding = np.array(embedding, dtype=np.float32)
            if embedding.shape[0] != 1 or embedding.shape[1] != self.dimension:
                raise ValueError(f"Embedding shape {embedding.shape} doesn't match expected ({1}, {self.dimension})")
            
            # Add to FAISS index
            self.index.add(embedding)
            
            # Add to document store
            self.doc_store.append(text)
            
            # Persist changes
            if self.save_index():
                logger.info(f"Document added successfully. Total documents: {len(self.doc_store)}")
                return True
            else:
                logger.error("Failed to save index after adding document")
                return False
                
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False

    def retrieve(self, query: str, k: int = 3, threshold: float = 0.0) -> Dict[str, Any]:
        """Retrieve the top-k most relevant documents for a given query."""
        if not isinstance(query, str) or not query.strip():
            return {"error": "Query must be a non-empty string"}
        
        if self.index is None or self.index.ntotal == 0:
            return {"message": "The knowledge base is empty. Add documents first", "results": []}

        try:
            query = query.strip()
            logger.info(f"Retrieving documents for query: '{query}' (k={k}, fallback={self.use_fallback})")
            
            # Create embedding for the query with fallback support
            query_embedding = self._encode_fallback([query])
            query_embedding = np.array(query_embedding, dtype=np.float32)
            
            # Ensure k doesn't exceed available documents
            k = min(k, len(self.doc_store))
            
            # Search the index for the top k similar vectors
            distances, indices = self.index.search(query_embedding, k)
            
            # Process results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.doc_store) and distance >= threshold:
                    similarity_score = 1.0 / (1.0 + distance)  # Convert distance to similarity
                    results.append({
                        "text": self.doc_store[idx],
                        "similarity_score": round(similarity_score, 4),
                        "distance": round(float(distance), 4),
                        "rank": i + 1,
                        "document_id": int(idx)
                    })
            
            logger.info(f"Retrieved {len(results)} documents using {'fallback' if self.use_fallback else 'SentenceTransformer'}")
            
            return {
                "query": query,
                "results": results,
                "total_documents": len(self.doc_store),
                "model_type": "fallback" if self.use_fallback else "sentence_transformer",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return {"error": str(e), "results": []}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        return {
            "total_documents": len(self.doc_store),
            "index_size": self.index.ntotal if self.index else 0,
            "model_name": self.model_name,
            "embedding_dimension": self.dimension,
            "use_fallback": self.use_fallback,
            "model_type": "fallback" if self.use_fallback else "sentence_transformer",
            "index_path": self.index_path,
            "doc_store_path": self.doc_store_path
        }

    def clear_all(self) -> bool:
        """Clear all documents and reinitialize the system."""
        try:
            logger.info("Clearing all documents from RAG system")
            
            # Remove files if they exist
            for path in [self.index_path, self.doc_store_path, self.metadata_path]:
                if os.path.exists(path):
                    os.remove(path)
            
            # Reinitialize
            self._initialize_new_index()
            self.save_index()
            
            logger.info("RAG system cleared successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing RAG system: {e}")
            return False