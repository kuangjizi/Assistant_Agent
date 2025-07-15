# src/agents/summarizer.py
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from datetime import datetime, timedelta

class Summarizer:
    def __init__(self, llm, db_manager):
        self.llm = llm
        self.db_manager = db_manager

        # Custom summarization prompt
        self.summary_prompt = PromptTemplate(
            template="""
            Create a comprehensive daily summary of the following content:

            {text}

            Please provide:
            1. Key highlights (3-5 main points)
            2. Important updates or changes
            3. Relevant trends or patterns
            4. Action items or follow-ups needed

            Format the summary in a clear, professional manner suitable for email.
            """,
            input_variables=["text"]
        )

        self.summarize_chain = load_summarize_chain(
            llm=self.llm,
            chain_type="map_reduce",
            map_prompt=self.summary_prompt,
            combine_prompt=self.summary_prompt
        )

    def create_daily_summary(self, topic_filter: str = "") -> dict:
        """Create daily summary of new content"""

        # Get content from the last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        new_content = self.db_manager.get_content_since(yesterday, topic_filter)

        if not new_content:
            return {
                "summary": "No new content found for the specified period.",
                "content_count": 0,
                "sources": []
            }

        # Prepare content for summarization
        content_text = "\n\n".join([
            f"Title: {item['title']}\nSource: {item['url']}\nContent: {item['content'][:500]}..."
            for item in new_content
        ])

        # Generate summary
        summary = self.summarize_chain.run(content_text)

        # Extract sources
        sources = [{"title": item['title'], "url": item['url']} for item in new_content]

        return {
            "summary": summary,
            "content_count": len(new_content),
            "sources": sources,
            "generated_at": datetime.now().isoformat(),
            "topic_filter": topic_filter
        }

    def create_topic_summary(self, topic: str, days_back: int = 7) -> dict:
        """Create focused summary for specific topic"""

        since_date = datetime.now() - timedelta(days=days_back)
        topic_content = self.db_manager.search_content_by_topic(topic, since_date)

        if not topic_content:
            return {
                "summary": f"No content found for topic '{topic}' in the last {days_back} days.",
                "content_count": 0,
                "sources": []
            }

        # Topic-specific prompt
        topic_prompt = f"""
        Create a focused summary about "{topic}" based on the following content:

        {{text}}

        Please provide:
        1. Overview of {topic} developments
        2. Key insights and trends
        3. Notable changes or updates
        4. Future implications or predictions

        Focus specifically on {topic} and filter out unrelated information.
        """

        content_text = "\n\n".join([
            f"Title: {item['title']}\nSource: {item['url']}\nContent: {item['content']}"
            for item in topic_content
        ])

        summary = self.llm.predict(topic_prompt.format(text=content_text))
        sources = [{"title": item['title'], "url": item['url']} for item in topic_content]

        return {
            "summary": summary,
            "topic": topic,
            "content_count": len(topic_content),
            "sources": sources,
            "period_days": days_back,
            "generated_at": datetime.now().isoformat()
        }
