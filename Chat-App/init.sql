CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    author TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
