# src/agents/query_engine.py
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.memory import ConversationBufferMemory
import logging
import datetime
import re

class QueryEngine:
    def __init__(self, vector_store, model_config):
        self.vector_store = vector_store
        self.llm = ChatGoogleGenerativeAI(**model_config)
        self.embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')
        self.web_search = DuckDuckGoSearchRun()

        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )

        # Custom prompt template with chat history
        self.prompt_template = PromptTemplate(
            template="""
            You are a knowledgeable assistant. Answer the question based on the provided context, chat history, and your knowledge.
            Always include source references and links when available.

            Context from knowledge base:
            {context}

            Web search results (if applicable):
            {web_results}

            Chat history:
            {chat_history}

            Question: {question}

            Provide a detailed answer with:
            1. Main answer
            2. Supporting details
            3. Source references with links
            4. Confidence level (High/Medium/Low)

            Answer:
            """,
            input_variables=["context", "web_results", "chat_history", "question"]
        )

    async def answer_query(self, question: str, use_web_search: bool = True, chat_history: list = []) -> dict:
        """Answer user query using RAG + web search with conversation memory"""

        # 1. Retrieve relevant documents from vector store
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(question)

        # 2. Perform web search if enabled
        if use_web_search:
            try:
                search_results_text = await self.web_search.arun(question) # Use async version
                # Create a Document object for the web results
                web_doc = Document(
                    page_content=search_results_text,
                    metadata={"source": "Web Search"}
                )
                # Add the web search result to your list of documents
                relevant_docs.append(web_doc)
            except Exception as e:
                logging.warning(f"Web search failed: {e}")

        # 3. Create a combined, in-memory retriever from all documents
        combined_vector_store = FAISS.from_documents(relevant_docs, self.embeddings)
        combined_retriever = combined_vector_store.as_retriever(search_kwargs={"k": 10})

        # 4. Generate answer using LLM with memory
        qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm,
            retriever=combined_retriever,
            memory=self.memory,
            return_source_documents=True
        )

        # If chat history is provided from the Streamlit app, update memory
        if chat_history:
            # Clear existing memory to avoid duplication
            self.memory.clear()

            # Add chat history to memory
            for message in chat_history:
                if message["role"] == "user":
                    self.memory.chat_memory.add_user_message(message["content"])
                elif message["role"] == "assistant":
                    self.memory.chat_memory.add_ai_message(message["content"])

        result = await qa_chain({"question": question})

        # 5. Extract and format sources
        sources = self._extract_sources(relevant_docs)

        return {
            "answer": result["answer"],
            "sources": sources,
            "confidence": self._assess_confidence(relevant_docs, result["answer"]),
            "web_search_used": use_web_search,
            "timestamp": datetime.datetime.now().isoformat()
        }

    def _extract_sources(self, documents) -> list:
        """Extract and format source information"""
        sources = []
        seen_urls = set()

        for doc in documents:
            url = doc.metadata.get('url')
            if url and url not in seen_urls:
                sources.append({
                    'url': url,
                    'title': doc.metadata.get('title', 'Unknown'),
                    'relevance_score': doc.metadata.get('score', 0)
                })
                seen_urls.add(url)

        return sources

    def _assess_confidence(self, documents, answer) -> str:
        """Assess confidence level based on source quality and answer completeness"""
        if len(documents) >= 7 and len(answer) > 100:
            return "High"
        elif len(documents) >= 3 and len(answer) > 50:
            return "Medium"
        else:
            return "Low"
