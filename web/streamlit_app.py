# web/streamlit_app.py
import streamlit as st
import asyncio
from datetime import datetime, timedelta
import sys
import os

from agents.query_engine import QueryEngine
from agents.summarizer import Summarizer
from data.database import DatabaseManager
from utils.config_manager import get_config

# Initialize components
@st.cache_resource
def init_components():
    config = get_config()
    db_manager = DatabaseManager(config.database_url)
    # Initialize other components...
    return db_manager

def main():
    st.set_page_config(
        page_title="AI Assistant Agent",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 AI Assistant Agent")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # URL Management
        st.subheader("Monitored URLs")
        new_url = st.text_input("Add new URL to monitor:")
        tags = st.text_input("Tags (comma-separated):")

        if st.button("Add URL"):
            if new_url:
                db_manager = init_components()
                tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                success = db_manager.add_url(new_url, "streamlit_user", tag_list)
                if success:
                    st.success("URL added successfully!")
                else:
                    st.error("Failed to add URL")

        # Display current URLs
        db_manager = init_components()
        urls = db_manager.get_active_urls()
        if urls:
            st.write("**Current URLs:**")
            for url_info in urls:
                st.write(f"• {url_info['url']}")

    # Main content area
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Summaries", "⚙️ Admin"])

    with tab1:
        st.header("Ask Questions")

        # Chat interface
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "sources" in message:
                    with st.expander("Sources"):
                        for source in message["sources"]:
                            st.write(f"• [{source['title']}]({source['url']})")

        # Chat input
        if prompt := st.chat_input("Ask me anything..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Here you would call your query engine
                    # For demo purposes, using placeholder
                    response = {
                        "answer": "This is a placeholder response. In the actual implementation, this would be generated by the QueryEngine.",
                        "sources": [{"title": "Example Source", "url": "https://example.com"}],
                        "confidence": "Medium"
                    }

                    st.markdown(response["answer"])

                    # Show confidence and sources
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("Confidence", response["confidence"])

                    with st.expander("Sources"):
                        for source in response["sources"]:
                            st.write(f"• [{source['title']}]({source['url']})")

                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response["sources"]
                    })

    with tab2:
        st.header("Content Summaries")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Daily Summary")
            if st.button("Generate Daily Summary"):
                with st.spinner("Generating summary..."):
                    # Call summarizer
                    summary_data = {
                        "summary": "This is a placeholder daily summary.",
                        "content_count": 5,
                        "sources": [{"title": "Example", "url": "https://example.com"}]
                    }

                    st.write(summary_data["summary"])
                    st.metric("New Items", summary_data["content_count"])

        with col2:
            st.subheader("Topic Summary")
            topic = st.text_input("Enter topic:")
            days = st.slider("Days to look back:", 1, 30, 7)

            if st.button("Generate Topic Summary") and topic:
                with st.spinner(f"Generating summary for '{topic}'..."):
                    # Call topic summarizer
                    topic_summary = {
                        "summary": f"This is a placeholder summary for topic '{topic}'.",
                        "content_count": 3
                    }

                    st.write(topic_summary["summary"])
                    st.metric("Relevant Items", topic_summary["content_count"])

    with tab3:
        st.header("System Administration")

        # System stats
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Monitored URLs", len(urls) if urls else 0)

        with col2:
            st.metric("Total Content Items", "N/A")  # Would query database

        with col3:
            st.metric("Queries Today", "N/A")  # Would query logs

        # Manual operations
        st.subheader("Manual Operations")

        if st.button("Trigger Content Update"):
            st.info("Content update triggered (this would run the retrieval job)")

        if st.button("Send Test Summary Email"):
            st.info("Test email sent (this would trigger the email service)")

if __name__ == "__main__":
    main()
