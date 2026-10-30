
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    password TEXT,
    signup_at DATETIME,
    signup_from TEXT,
    signup_using TEXT,
    last_login_at DATETIME,
    last_login_from TEXT,
    last_login_using TEXT,
    stripe_customer_id TEXT,
    plan TEXT,
    tutorial_completed BOOLEAN DEFAULT false,
    period_query_count INTEGER NOT NULL DEFAULT 0,
    period_end DATETIME,
    max_queries INTEGER NOT NULL DEFAULT 0,
    max_databases INTEGER NOT NULL DEFAULT 0,
    theme TEXT,
    db_role TEXT,
    db_password TEXT
);

CREATE UNIQUE INDEX users_email ON users (email);

CREATE TABLE user_oauth_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    access_token TEXT,
    expires_at INTEGER,
    refresh_token TEXT,
    refresh_expires_in INTEGER,
    token_type TEXT,
    scope TEXT,
    integration TEXT
);

CREATE INDEX user_oauth_tokens_user_id ON user_oauth_tokens (user_id);

CREATE TABLE databases (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name TEXT,
    slug TEXT,
    integration TEXT,
    suggestion TEXT
);

CREATE INDEX databases_user_id ON databases (user_id);
CREATE INDEX databases_slug ON databases (slug);

CREATE TABLE notebook_queries (
    id INTEGER PRIMARY KEY,
    database_id INTEGER REFERENCES databases(id),
    stmt TEXT,
    created_at DATETIME
);

CREATE INDEX notebook_queries_database_id ON notebook_queries (database_id);
