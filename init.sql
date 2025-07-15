-- init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables
CREATE TABLE IF NOT EXISTS monitored_urls (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    added_by TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    tags TEXT[],
    check_frequency INTEGER DEFAULT 24,
    last_checked TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_records (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    content_hash TEXT,
    content TEXT,
    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    word_count INTEGER,
    CONSTRAINT fk_url FOREIGN KEY (url) REFERENCES monitored_urls(url) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT,
    sources JSONB DEFAULT '[]',
    confidence TEXT,
    response_time FLOAT,
    user_feedback INTEGER CHECK (user_feedback >= 1 AND user_feedback <= 5),
    session_id TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    evaluation_date DATE NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    component TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_content_records_url ON content_records(url);
CREATE INDEX IF NOT EXISTS idx_content_records_retrieved_at ON content_records(retrieved_at);
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_monitored_urls_active ON monitored_urls(is_active);

-- Insert some sample URLs for testing
INSERT INTO monitored_urls (url, added_by, tags) VALUES
('https://news.ycombinator.com', 'system', ARRAY['tech', 'news']),
('https://techcrunch.com', 'system', ARRAY['tech', 'startup']),
('https://www.reuters.com/technology', 'system', ARRAY['tech', 'news'])
ON CONFLICT (url) DO NOTHING;
