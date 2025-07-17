# src/data/vector_store.py
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import logging
import os
from typing import List, Dict, Any, Optional
import uuid

class VectorStoreManager:
    def __init__(self, persist_directory: str = "./data/vector_store",
                 collection_name: str = "ai_assistant_docs",
                 google_api_key: str = ''):
        """
        Initialize Vector Store Manager with ChromaDB

        Args:
            persist_directory: Directory to persist the vector database
            collection_name: Name of the collection to use
            google_api_key: Google API key for embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)

        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Initialize Langchain Chroma wrapper
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )

        self.logger.info(f"Vector store initialized at {persist_directory}")

    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Add documents to the vector store

        Args:
            documents: List of document dictionaries with 'content', 'metadata', etc.

        Returns:
            List of document IDs
        """
        try:
            doc_objects = []

            for doc in documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})

                # Split content into chunks
                chunks = self.text_splitter.split_text(content)

                # Create Document objects for each chunk
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'chunk_id': f"{metadata.get('url', 'unknown')}_{i}"
                    })

                    doc_objects.append(Document(
                        page_content=chunk,
                        metadata=chunk_metadata
                    ))

            # Add documents to vector store
            ids = self.vectorstore.add_documents(doc_objects)

            self.logger.info(f"Added {len(doc_objects)} document chunks to vector store")
            return ids

        except Exception as e:
            self.logger.error(f"Error adding documents to vector store: {e}")
            return []

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[str]:
        """
        Add texts directly to the vector store

        Args:
            texts: List of text strings
            metadatas: List of metadata dictionaries

        Returns:
            List of document IDs
        """
        try:
            if metadatas is None:
                metadatas = [{}] * len(texts)

            # Generate unique IDs
            ids = [str(uuid.uuid4()) for _ in texts]

            # Add to vector store
            self.vectorstore.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )

            self.logger.info(f"Added {len(texts)} texts to vector store")
            return ids

        except Exception as e:
            self.logger.error(f"Error adding texts to vector store: {e}")
            return []

    def similarity_search(self, query: str, k: int = 5,
                         filter_dict: Optional[Dict] = None) -> List[Document]:
        """
        Perform similarity search

        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            List of similar documents
        """
        try:
            if filter_dict:
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k,
                    filter=filter_dict
                )
            else:
                results = self.vectorstore.similarity_search(
                    query=query,
                    k=k
                )

            self.logger.debug(f"Found {len(results)} similar documents for query: {query[:50]}...")
            return results

        except Exception as e:
            self.logger.error(f"Error in similarity search: {e}")
            return []

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """
        Perform similarity search with relevance scores

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        try:
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k
            )

            self.logger.debug(f"Found {len(results)} scored results for query: {query[:50]}...")
            return results

        except Exception as e:
            self.logger.error(f"Error in similarity search with score: {e}")
            return []

    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents by IDs

        Args:
            ids: List of document IDs to delete

        Returns:
            Success status
        """
        try:
            self.vectorstore.delete(ids=ids)
            self.logger.info(f"Deleted {len(ids)} documents from vector store")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting documents: {e}")
            return False

    def delete_by_metadata(self, filter_dict: Dict) -> bool:
        """
        Delete documents by metadata filter

        Args:
            filter_dict: Metadata filter to match documents for deletion

        Returns:
            Success status
        """
        try:
            # First, find documents matching the filter
            collection = self.client.get_collection(self.collection_name)
            results = collection.get(where=filter_dict)

            if results['ids']:
                collection.delete(ids=results['ids'])
                self.logger.info(f"Deleted {len(results['ids'])} documents matching filter")
                return True
            else:
                self.logger.info("No documents found matching the filter")
                return True

        except Exception as e:
            self.logger.error(f"Error deleting documents by metadata: {e}")
            return False

    def update_document(self, doc_id: str, content: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> bool:
        """
        Update a document's content or metadata

        Args:
            doc_id: Document ID to update
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            Success status
        """
        try:
            collection = self.client.get_collection(self.collection_name)

            update_data = {}
            if content is not None:
                # Generate new embedding for updated content
                embedding = self.embeddings.embed_query(content)
                update_data['documents'] = [content]
                update_data['embeddings'] = [embedding]

            if metadata is not None:
                update_data['metadatas'] = [metadata]

            if update_data:
                collection.update(ids=[doc_id], **update_data)
                self.logger.info(f"Updated document {doc_id}")
                return True
            else:
                self.logger.warning("No content or metadata provided for update")
                return False

        except Exception as e:
            self.logger.error(f"Error updating document: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.client.get_collection(self.collection_name)
            count = collection.count()

            # Get sample of metadata to understand structure
            sample = collection.peek(limit=10)

            # Count documents by source URL if available
            url_counts = {}
            if sample.get('metadatas'):
                for metadata in sample['metadatas']:
                    url = metadata.get('url', 'unknown')
                    url_counts[url] = url_counts.get(url, 0) + 1

            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'sample_urls': list(url_counts.keys())[:5],
                'persist_directory': self.persist_directory
            }

        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {}

    def as_retriever(self, search_kwargs: Dict = None):
        """
        Return the vector store as a LangChain retriever

        Args:
            search_kwargs: Additional search parameters

        Returns:
            LangChain retriever object
        """
        search_kwargs = search_kwargs or {"k": 5}
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)

    def reset_collection(self) -> bool:
        """
        Reset (clear) the entire collection

        Returns:
            Success status
        """
        try:
            self.client.delete_collection(self.collection_name)
            # Recreate the collection
            self.vectorstore = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            self.logger.info(f"Reset collection {self.collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error resetting collection: {e}")
            return False

    def backup_collection(self, backup_path: str) -> bool:
        """
        Create a backup of the collection

        Args:
            backup_path: Path to save the backup

        Returns:
            Success status
        """
        try:
            import shutil
            shutil.copytree(self.persist_directory, backup_path, dirs_exist_ok=True)
            self.logger.info(f"Collection backed up to {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error backing up collection: {e}")
            return False
