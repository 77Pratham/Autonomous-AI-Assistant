import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RAGSystem:
    """
    Handles the Retrieval-Augmented Generation system.
    - Creates text embeddings using SentenceTransformer.
    - Stores and indexes embeddings using FAISS for fast similarity search.
    - Persists the index and document store to disk.
    - Enhanced with better error handling and robustness.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', data_dir: str = "data/faiss_index"):
        """
        Initialize the RAG system.
        
        Args:
            model_name: Name of the sentence transformer model
            data_dir: Directory to store the FAISS index and documents
        """
        logger.info("Initializing RAG System...")
        
        self.model_name = model_name
        self.data_dir = data_dir
        
        try:
            # 1. Load the sentence transformer model
            logger.info(f"Loading SentenceTransformer model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {e}")
            raise
        
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
                
                logger.info(f"Loaded {len(self.doc_store)} documents from existing index")
                
                # Validate consistency
                if self.index.ntotal != len(self.doc_store):
                    logger.warning(f"Index size ({self.index.ntotal}) doesn't match doc store size ({len(self.doc_store)})")
            
            else:
                logger.info("No existing index found or index is empty. Initializing a new one")
                self._initialize_new_index()
                
        except Exception as e:
            logger.error(f"Error loading index: {e}. Initializing a new one")
            self._initialize_new_index()

    def _initialize_new_index(self) -> None:
        """Initialize a new empty FAISS index."""
        try:
            # Using IndexFlatL2 for basic L2 distance search
            self.index = faiss.IndexFlatL2(self.dimension)
            self.doc_store = []
            self.metadata = {"total_docs": 0, "model_name": self.model_name}
            logger.info("New FAISS index initialized")
        except Exception as e:
            logger.error(f"Failed to initialize new index: {e}")
            raise

    def save_index(self) -> bool:
        """
        Save the FAISS index and document store to disk.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            logger.info("Saving index and document store to disk")
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save document store
            with open(self.doc_store_path, 'w', encoding='utf-8') as f:
                json.dump(self.doc_store, f, ensure_ascii=False, indent=2)
            
            # Update and save metadata
            self.metadata["total_docs"] = len(self.doc_store)
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info("Index and document store saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            return False

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a document to the RAG system.
        
        Args:
            text: The document text to add
            metadata: Optional metadata for the document
            
        Returns:
            True if added successfully, False otherwise
        """
        if not isinstance(text, str) or not text.strip():
            logger.warning("Attempted to add an empty or invalid document")
            return False

        try:
            # Clean the text
            text = text.strip()
            
            # Check for duplicates
            if text in self.doc_store:
                logger.info("Document already exists in the store")
                return True
            
            logger.info(f"Adding document: '{text[:100]}...' (length: {len(text)})")
            
            # Create embedding
            embedding = self.model.encode([text], convert_to_tensor=False, show_progress_bar=False)
            
            # Ensure embedding is the right shape and type
            embedding = np.array(embedding, dtype=np.float32)
            if embedding.shape[0] != 1 or embedding.shape[1] != self.dimension:
                raise ValueError(f"Embedding shape {embedding.shape} doesn't match expected ({1}, {self.dimension})")
            
            # Add to FAISS index
            self.index.add(embedding)
            
            # Add to document store with metadata
            doc_entry = {
                "text": text,
                "metadata": metadata or {},
                "id": len(self.doc_store)
            }
            self.doc_store.append(text)  # Keep simple format for compatibility
            
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

    def add_documents_batch(self, texts: List[str]) -> int:
        """
        Add multiple documents in batch for efficiency.
        
        Args:
            texts: List of document texts
            
        Returns:
            Number of documents successfully added
        """
        if not texts:
            return 0
        
        added_count = 0
        try:
            # Filter valid texts
            valid_texts = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
            valid_texts = [text for text in valid_texts if text not in self.doc_store]  # Remove duplicates
            
            if not valid_texts:
                logger.info("No new valid documents to add")
                return 0
            
            logger.info(f"Adding {len(valid_texts)} documents in batch")
            
            # Create embeddings for all texts at once
            embeddings = self.model.encode(valid_texts, convert_to_tensor=False, show_progress_bar=True)
            embeddings = np.array(embeddings, dtype=np.float32)
            
            # Add all embeddings to index
            self.index.add(embeddings)
            
            # Add all texts to document store
            self.doc_store.extend(valid_texts)
            
            # Save changes
            if self.save_index():
                added_count = len(valid_texts)
                logger.info(f"Batch added {added_count} documents successfully")
            else:
                logger.error("Failed to save index after batch add")
                
        except Exception as e:
            logger.error(f"Error in batch add: {e}")
        
        return added_count

    def retrieve(self, query: str, k: int = 3, threshold: float = 0.0) -> Dict[str, Any]:
        """
        Retrieve the top-k most relevant documents for a given query.
        
        Args:
            query: The search query
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            Dictionary containing search results
        """
        if not isinstance(query, str) or not query.strip():
            return {"error": "Query must be a non-empty string"}
        
        if self.index is None or self.index.ntotal == 0:
            return {"message": "The knowledge base is empty. Add documents first", "results": []}

        try:
            query = query.strip()
            logger.info(f"Retrieving documents for query: '{query}' (k={k})")
            
            # Create embedding for the query
            query_embedding = self.model.encode([query], convert_to_tensor=False, show_progress_bar=False)
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
            
            logger.info(f"Retrieved {len(results)} documents")
            
            return {
                "query": query,
                "results": results,
                "total_documents": len(self.doc_store),
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
            "index_path": self.index_path,
            "doc_store_path": self.doc_store_path
        }

    def clear_all(self) -> bool:
        """
        Clear all documents and reinitialize the system.
        
        Returns:
            True if cleared successfully
        """
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

    def search_documents(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search documents with optional filters.
        
        Args:
            query: Search query
            filters: Optional filters to apply
            
        Returns:
            List of matching documents
        """
        # For now, just use the regular retrieve method
        # Can be extended to support metadata filtering
        result = self.retrieve(query, k=10)
        return result.get("results", [])