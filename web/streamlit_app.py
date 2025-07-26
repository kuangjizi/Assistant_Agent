# web/streamlit_app.py
import streamlit as st
import asyncio
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.agents.query_engine import QueryEngine
from src.agents.summarizer import Summarizer
from src.data.database import DatabaseManager
from src.data.vector_store import VectorStoreManager
from src.agents.content_retriever import ContentRetriever
from src.services.email_service import EmailService
from src.utils.config_manager import get_config

# Initialize components
@st.cache_resource
def init_components():
    """Initialize and cache all backend components"""
    config = get_config()

    # Initialize database manager
    db_manager = DatabaseManager(config.database_url)

    # Initialize vector store
    vector_store = VectorStoreManager(
        persist_directory=config.vector_store_config['path'],
        collection_name=config.vector_store_config['collection_name']
    )

    # Initialize content retriever
    content_retriever = ContentRetriever(
        vector_store=vector_store,
        db_manager=db_manager
    )

    # Initialize query engine
    query_engine = QueryEngine(
        vector_store=vector_store,
        model_config=config.google_model_config
    )

    # Initialize summarizer
    summarizer = Summarizer(
        db_manager=db_manager,
        model_config=config.google_model_config
    )

    # Initialize email service
    email_service = EmailService(config.email_config)

    return {
        "db_manager": db_manager,
        "vector_store": vector_store,
        "content_retriever": content_retriever,
        "query_engine": query_engine,
        "summarizer": summarizer,
        "email_service": email_service,
        "config": config
    }

# Create an async wrapper for Streamlit
async def run_async(func, *args, **kwargs):
    """Helper function to run async functions in Streamlit"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = await func(*args, **kwargs)
    loop.close()
    return result

def main():
    st.set_page_config(
        page_title="AI Assistant Agent",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 AI Assistant Agent")

    # Initialize all components
    components = init_components()
    db_manager = components["db_manager"]
    vector_store = components["vector_store"]
    content_retriever = components["content_retriever"]
    query_engine = components["query_engine"]
    summarizer = components["summarizer"]
    email_service = components["email_service"]
    config = components["config"]

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # URL Management
        st.subheader("Monitored URLs")
        new_url = st.text_input("Add new URL to monitor:")
        tags = st.text_input("Tags (comma-separated):")

        if st.button("Add URL"):
            if new_url:
                tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                success = db_manager.add_url(new_url, "streamlit_user", tag_list)
                if success:
                    st.success("URL added successfully!")
                else:
                    st.error("Failed to add URL")

        # Display current URLs
        urls = db_manager.get_active_urls()
        if urls:
            st.write("**Current URLs:**")
            for url_info in urls:
                st.write(f"• {url_info['url']}")
                if url_info.get('tags'):
                    st.write(f"  Tags: {', '.join(url_info['tags'])}")

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
                    # Use the query engine to get a real response
                    use_web_search = True

                    # Format chat history for the query engine
                    chat_history = st.session_state.messages[:-1]  # Exclude the current user message

                    # Run the async query in a synchronous context
                    response = asyncio.run(query_engine.answer_query(
                        question=prompt,
                        use_web_search=use_web_search,
                        chat_history=chat_history
                    ))

                    st.markdown(response["answer"])

                    # Show confidence and sources
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("Confidence", response["confidence"])

                    with st.expander("Sources"):
                        for source in response["sources"]:
                            st.write(f"• [{source.get('title', 'Unknown')}]({source.get('url', '#')})")

                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "sources": response["sources"]
                    })

                    # Log the query for analytics
                    start_time = datetime.now()
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    db_manager.log_query(
                        question=prompt,
                        answer=response["answer"],
                        sources=response["sources"],
                        confidence=response["confidence"],
                        response_time=response_time
                    )

    with tab2:
        st.header("Content Summaries")

        col1, col2 = st.columns(2)

        # Initialize session state for summaries and email actions
        if "daily_summary" not in st.session_state:
            st.session_state.daily_summary = None
        if "topic_summary" not in st.session_state:
            st.session_state.topic_summary = None
        if "email_daily" not in st.session_state:
            st.session_state.email_daily = False
        if "email_topic" not in st.session_state:
            st.session_state.email_topic = False

        # Helper functions for email actions
        def email_daily_summary():
            st.session_state.email_daily = True

        def email_topic_summary():
            st.session_state.email_topic = True

        with col1:
            st.subheader("Daily Summary")
            if st.button("Generate Daily Summary"):
                with st.spinner("Generating summary..."):
                    # Call the actual summarizer
                    summary_data = summarizer.create_daily_summary()
                    st.session_state.daily_summary = summary_data

                    st.write(summary_data.get("summary", "No summary available"))
                    st.metric("New Items", summary_data.get("content_count", 0))

                    # Display sources if available
                    if summary_data.get("sources"):
                        with st.expander("Sources"):
                            for source in summary_data.get("sources", []):
                                st.write(f"• [{source.get('title', 'Unknown')}]({source.get('url', '#')})")

            # Email button (using a callback to avoid direct session state access)
            if st.session_state.daily_summary is not None:
                st.button("Email This Summary", on_click=email_daily_summary)

            # Handle email sending based on state flag
            if st.session_state.email_daily and st.session_state.daily_summary is not None:
                with st.spinner("Sending email..."):
                    if asyncio.run(email_service.send_daily_summary(st.session_state.daily_summary)):
                        st.success("Summary email sent successfully!")
                    else:
                        st.error("Failed to send summary email")
                # Reset the flag
                st.session_state.email_daily = False

        with col2:
            st.subheader("Topic Summary")
            topic = st.text_input("Enter topic:")
            days = st.slider("Days to look back:", 1, 30, 7)

            if st.button("Generate Topic Summary") and topic:
                with st.spinner(f"Generating summary for '{topic}'..."):
                    # Call the actual topic summarizer
                    topic_summary = summarizer.create_topic_summary(topic, days)
                    st.session_state.topic_summary = topic_summary

                    st.write(topic_summary.get("summary", "No summary available"))
                    st.metric("Relevant Items", topic_summary.get("content_count", 0))

                    # Display sources if available
                    if topic_summary.get("sources"):
                        with st.expander("Sources"):
                            for source in topic_summary.get("sources", []):
                                st.write(f"• [{source.get('title', 'Unknown')}]({source.get('url', '#')})")

            # Email button (using a callback to avoid direct session state access)
            if st.session_state.topic_summary is not None:
                st.button("Email This Topic Summary", on_click=email_topic_summary)

            # Handle email sending based on state flag
            if st.session_state.email_topic and st.session_state.topic_summary is not None:
                with st.spinner("Sending email..."):
                    if asyncio.run(email_service.send_topic_summary(st.session_state.topic_summary)):
                        st.success("Topic summary email sent successfully!")
                    else:
                        st.error("Failed to send topic summary email")
                # Reset the flag
                st.session_state.email_topic = False

    with tab3:
        st.header("System Administration")

        # System stats
        col1, col2, col3 = st.columns(3)

        # Query for actual stats
        content_count_query = """
            SELECT COUNT(*) FROM content_records
        """
        queries_today_query = """
            SELECT COUNT(*) FROM query_logs
            WHERE created_at >= CURRENT_DATE
        """

        with psycopg2.connect(config.database_url) as conn:
            with conn.cursor() as cur:
                # Get content count
                try:
                    cur.execute(content_count_query)
                    content_count = cur.fetchone()[0]
                except:
                    content_count = "N/A"

                # Get queries today
                try:
                    cur.execute(queries_today_query)
                    queries_today = cur.fetchone()[0]
                except:
                    queries_today = "N/A"

        with col1:
            st.metric("Monitored URLs", len(urls) if urls else 0)

        with col2:
            st.metric("Total Content Items", content_count)

        with col3:
            st.metric("Queries Today", queries_today)

        # Vector store stats
        st.subheader("Vector Store Stats")
        vector_stats = vector_store.get_collection_stats()
        st.json(vector_stats)

        # Manual operations
        st.subheader("Manual Operations")

        if st.button("Trigger Content Update"):
            with st.spinner("Retrieving content from monitored URLs..."):
                # Get active URLs
                urls_to_update = [item['url'] for item in db_manager.get_active_urls()]

                if urls_to_update:
                    # Run content retrieval
                    result = asyncio.run(content_retriever.retrieve_content(urls_to_update))
                    new_content_count = sum(1 for item in result if item.get('is_new', False))
                    st.success(f"Content update completed! Retrieved {len(result)} URLs, {new_content_count} with new content.")
                else:
                    st.warning("No URLs configured for monitoring")

        if st.button("Send Test Summary Email"):
            with st.spinner("Sending test email..."):
                # Create a test summary
                test_summary = {
                    "summary": "This is a test summary email from the AI Assistant Agent.",
                    "content_count": 3,
                    "sources": [
                        {"title": "Test Source 1", "url": "https://example.com/1"},
                        {"title": "Test Source 2", "url": "https://example.com/2"}
                    ],
                    "generated_at": datetime.now().isoformat()
                }

                # Send the email
                if asyncio.run(email_service.send_daily_summary(test_summary)):
                    st.success("Test email sent successfully!")
                else:
                    st.error("Failed to send test email")

        # Database maintenance
        st.subheader("Database Maintenance")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Reset Vector Store"):
                if vector_store.reset_collection():
                    st.success("Vector store reset successfully!")
                else:
                    st.error("Failed to reset vector store")

        with col2:
            backup_path = st.text_input("Backup Path:", value="./data/vector_store_backup")
            if st.button("Backup Vector Store"):
                if vector_store.backup_collection(backup_path):
                    st.success(f"Vector store backed up to {backup_path}")
                else:
                    st.error("Failed to backup vector store")

# Add missing import
import psycopg2

if __name__ == "__main__":
    main()
