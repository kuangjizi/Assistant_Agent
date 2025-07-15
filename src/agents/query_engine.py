# src/agents/query_engine.py
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.tools import DuckDuckGoSearchRun
import logging
import datetime
import re

class QueryEngine:
    def __init__(self, vector_store, llm_model="gpt-3.5-turbo"):
        self.vector_store = vector_store
        self.llm = OpenAI(model_name=llm_model, temperature=0.2)
        self.web_search = DuckDuckGoSearchRun()

        # Custom prompt template
        self.prompt_template = PromptTemplate(
            template="""
            You are a knowledgeable assistant. Answer the question based on the provided context and your knowledge.
            Always include source references and links when available.

            Context from knowledge base:
            {context}

            Web search results (if applicable):
            {web_results}

            Question: {question}

            Provide a detailed answer with:
            1. Main answer
            2. Supporting details
            3. Source references with links
            4. Confidence level (High/Medium/Low)

            Answer:
            """,
            input_variables=["context", "web_results", "question"]
        )

    async def answer_query(self, question: str, use_web_search: bool = True) -> dict:
        """Answer user query using RAG + web search"""

        # 1. Retrieve relevant documents from vector store
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.get_relevant_documents(question)

        # 2. Prepare context from retrieved documents
        context = "\n\n".join([
            f"Source: {doc.metadata.get('url', 'Unknown')}\n{doc.page_content}"
            for doc in relevant_docs
        ])

        # 3. Perform web search if enabled
        web_results = ""
        if use_web_search:
            try:
                search_results = self.web_search.run(question)
                web_results = f"Recent web search results:\n{search_results}"
            except Exception as e:
                logging.warning(f"Web search failed: {e}")

        # 4. Generate answer using LLM
        qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.llm,
            retriever=retriever,
            return_source_documents=True
        )

        result = qa_chain({"question": question})

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
        if len(documents) >= 3 and len(answer) > 100:
            return "High"
        elif len(documents) >= 1 and len(answer) > 50:
            return "Medium"
        else:
            return "Low"
