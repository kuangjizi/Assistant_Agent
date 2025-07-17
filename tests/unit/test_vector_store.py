# tests/unit/test_vector_store.py
from unittest.mock import Mock, patch
from pathlib import Path
from langchain.schema import Document

from data.vector_store import VectorStoreManager

class TestVectorStoreManager:

    def test_add_documents_with_chunking(self, temp_vector_store):
        """Test adding documents with text chunking logic"""
        documents = [
            {
                'content': 'This is a long test content for document 1. ' * 50,  # Long content to trigger chunking
                'metadata': {'url': 'https://example.com/1', 'title': 'Test Doc 1'}
            },
            {
                'content': 'Short content for document 2.',
                'metadata': {'url': 'https://example.com/2', 'title': 'Test Doc 2'}
            }
        ]

        ids = temp_vector_store.add_documents(documents)

        # Verify the method returns the expected IDs from the mock
        assert ids == ['doc1', 'doc2']

        # Verify that add_documents was called on the vectorstore
        temp_vector_store.vectorstore.add_documents.assert_called_once()

        # Get the actual Document objects that were passed to the vectorstore
        call_args = temp_vector_store.vectorstore.add_documents.call_args[0][0]

        # Verify that Document objects were created properly
        assert all(isinstance(doc, Document) for doc in call_args)

        # Verify that chunking metadata was added
        for doc in call_args:
            assert 'chunk_index' in doc.metadata
            assert 'total_chunks' in doc.metadata
            assert 'chunk_id' in doc.metadata

    def test_add_texts_with_uuid_generation(self, temp_vector_store):
        """Test adding texts with UUID generation"""
        texts = ['Test text 1', 'Test text 2']
        metadatas = [
            {'url': 'https://example.com/1'},
            {'url': 'https://example.com/2'}
        ]

        ids = temp_vector_store.add_texts(texts, metadatas)

        # Verify the method returns the expected IDs from the mock
        assert ids == ['text1', 'text2']

        # Verify that add_texts was called with the right parameters
        temp_vector_store.vectorstore.add_texts.assert_called_once()
        call_args = temp_vector_store.vectorstore.add_texts.call_args

        # Verify texts and metadatas were passed correctly
        assert call_args[1]['texts'] == texts
        assert call_args[1]['metadatas'] == metadatas
        # Verify that IDs were generated (should be present in the call)
        assert 'ids' in call_args[1]

    def test_similarity_search_with_filters(self, temp_vector_store):
        """Test similarity search with and without filters"""
        mock_docs = [
            Mock(page_content="Test content 1", metadata={'url': 'https://example.com/1'}),
            Mock(page_content="Test content 2", metadata={'url': 'https://example.com/2'})
        ]

        # Test without filter
        temp_vector_store.vectorstore.similarity_search.return_value = mock_docs
        results = temp_vector_store.similarity_search("test query", k=2)

        assert len(results) == 2
        temp_vector_store.vectorstore.similarity_search.assert_called_with(query="test query", k=2)

        # Reset mock
        temp_vector_store.vectorstore.similarity_search.reset_mock()

        # Test with filter
        filter_dict = {'url': 'https://example.com/1'}
        results = temp_vector_store.similarity_search("test query", k=2, filter_dict=filter_dict)

        temp_vector_store.vectorstore.similarity_search.assert_called_with(
            query="test query", k=2, filter=filter_dict
        )

    def test_similarity_search_with_score_returns_tuples(self, temp_vector_store):
        """Test similarity search with scores returns proper tuples"""
        mock_results = [
            (Mock(page_content="Test content 1"), 0.9),
            (Mock(page_content="Test content 2"), 0.8)
        ]

        temp_vector_store.vectorstore.similarity_search_with_score.return_value = mock_results
        results = temp_vector_store.similarity_search_with_score("test query", k=2)

        assert len(results) == 2
        assert isinstance(results[0], tuple)
        assert results[0][1] == 0.9
        assert results[1][1] == 0.8

    def test_delete_documents_success(self, temp_vector_store):
        """Test successful document deletion"""
        result = temp_vector_store.delete_documents(['doc1', 'doc2'])

        assert result == True
        temp_vector_store.vectorstore.delete.assert_called_once_with(ids=['doc1', 'doc2'])

    def test_delete_by_metadata_logic(self, temp_vector_store):
        """Test delete by metadata logic using the mocked client"""
        # The client is already mocked in the fixture, so we can test the logic
        mock_collection = temp_vector_store.client.get_collection.return_value
        mock_collection.get.return_value = {'ids': ['doc1', 'doc2']}

        result = temp_vector_store.delete_by_metadata({'url': 'https://example.com'})

        assert result == True
        # Verify the collection was queried with the filter
        mock_collection.get.assert_called_once_with(where={'url': 'https://example.com'})
        # Verify the documents were deleted
        mock_collection.delete.assert_called_once_with(ids=['doc1', 'doc2'])

    def test_delete_by_metadata_no_matches(self, temp_vector_store):
        """Test delete by metadata when no documents match"""
        mock_collection = temp_vector_store.client.get_collection.return_value
        mock_collection.get.return_value = {'ids': []}

        result = temp_vector_store.delete_by_metadata({'url': 'https://nonexistent.com'})

        assert result == True
        mock_collection.get.assert_called_once_with(where={'url': 'https://nonexistent.com'})
        # Delete should not be called when no IDs found
        mock_collection.delete.assert_not_called()

    def test_get_collection_stats_utilizes_mocked_client(self, temp_vector_store):
        """Test collection stats using the pre-configured mocked client"""
        # The client and collection are already mocked in the fixture
        mock_collection = temp_vector_store.client.get_collection.return_value
        mock_collection.count.return_value = 15
        mock_collection.peek.return_value = {
            'metadatas': [
                {'url': 'https://example.com/1'},
                {'url': 'https://example.com/2'},
                {'url': 'https://test.com/1'}
            ]
        }

        stats = temp_vector_store.get_collection_stats()

        assert stats['total_documents'] == 15
        assert stats['collection_name'] == "test_collection"
        assert 'https://example.com/1' in stats['sample_urls']
        assert len(stats['sample_urls']) <= 5  # Should limit to 5 URLs

    def test_as_retriever_with_default_and_custom_kwargs(self, temp_vector_store):
        """Test as_retriever with default and custom search kwargs"""
        # Test with default kwargs
        retriever = temp_vector_store.as_retriever()
        temp_vector_store.vectorstore.as_retriever.assert_called_with(search_kwargs={"k": 5})

        # Reset mock
        temp_vector_store.vectorstore.as_retriever.reset_mock()

        # Test with custom kwargs
        custom_kwargs = {'k': 10, 'filter': {'category': 'tech'}}
        retriever = temp_vector_store.as_retriever(custom_kwargs)
        temp_vector_store.vectorstore.as_retriever.assert_called_with(search_kwargs=custom_kwargs)

    def test_update_document_with_embeddings(self, temp_vector_store):
        """Test document update utilizing the mocked embeddings"""
        mock_collection = temp_vector_store.client.get_collection.return_value

        # The embeddings are already mocked in the fixture
        result = temp_vector_store.update_document(
            'doc1',
            content='Updated content',
            metadata={'updated': True}
        )

        assert result == True
        # Verify embeddings were generated for the new content
        temp_vector_store.embeddings.embed_query.assert_called_with('Updated content')
        # Verify the collection was updated with the new embedding and metadata
        mock_collection.update.assert_called_once()

        # Check the update call arguments
        call_args = mock_collection.update.call_args
        assert call_args[1]['ids'] == ['doc1']
        assert call_args[1]['documents'] == ['Updated content']
        assert call_args[1]['embeddings'] == [[0.1, 0.2, 0.3, 0.4, 0.5]]  # From mocked embeddings
        assert call_args[1]['metadatas'] == [{'updated': True}]

    def test_update_document_metadata_only(self, temp_vector_store):
        """Test updating only metadata without content"""
        mock_collection = temp_vector_store.client.get_collection.return_value

        result = temp_vector_store.update_document('doc1', metadata={'category': 'updated'})

        assert result == True
        # Embeddings should not be called for metadata-only updates
        temp_vector_store.embeddings.embed_query.assert_not_called()
        # Collection should be updated with metadata only
        call_args = mock_collection.update.call_args
        assert 'documents' not in call_args[1]
        assert 'embeddings' not in call_args[1]
        assert call_args[1]['metadatas'] == [{'category': 'updated'}]

    def test_error_handling_in_vector_operations(self, temp_vector_store):
        """Test error handling in various vector store operations"""
        # Test add_documents error handling
        temp_vector_store.vectorstore.add_documents.side_effect = Exception("Vector store error")
        ids = temp_vector_store.add_documents([{'content': 'test', 'metadata': {}}])
        assert ids == []

        # Reset the side effect
        temp_vector_store.vectorstore.add_documents.side_effect = None
        temp_vector_store.vectorstore.add_documents.return_value = ['doc1', 'doc2']

        # Test similarity_search error handling
        temp_vector_store.vectorstore.similarity_search.side_effect = Exception("Search error")
        results = temp_vector_store.similarity_search("test query")
        assert results == []

    def test_reset_collection_recreates_vectorstore(self, temp_vector_store):
        """Test that reset_collection properly recreates the vectorstore"""
        with patch('data.vector_store.Chroma') as mock_chroma_class:
            mock_new_vectorstore = Mock()
            mock_chroma_class.return_value = mock_new_vectorstore

            result = temp_vector_store.reset_collection()

            assert result == True
            # Verify collection was deleted
            temp_vector_store.client.delete_collection.assert_called_once_with("test_collection")
            # Verify new Chroma instance was created
            mock_chroma_class.assert_called_once()
            # Verify the vectorstore was replaced
            assert temp_vector_store.vectorstore == mock_new_vectorstore

    def test_backup_collection_copies_directory(self, temp_vector_store, temp_dir):
        """Test collection backup copies the persist directory"""
        backup_path = Path(temp_dir) / "backup"

        with patch('shutil.copytree') as mock_copy:
            result = temp_vector_store.backup_collection(str(backup_path))

            assert result == True
            mock_copy.assert_called_once_with(
                temp_vector_store.persist_directory,
                str(backup_path),
                dirs_exist_ok=True
            )
