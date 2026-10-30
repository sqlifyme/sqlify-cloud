DROP INDEX users_email;
DROP INDEX user_oauth_tokens_user_id;
DROP INDEX databases_user_id;
DROP INDEX databases_slug;
DROP INDEX notebook_queries_database_id;

ALTER TABLE users RENAME TO users_old;
ALTER TABLE user_oauth_tokens RENAME TO user_oauth_tokens_old;
ALTER TABLE databases RENAME TO databases_old;
ALTER TABLE notebook_queries RENAME TO notebook_queries_old;


CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    db_password TEXT,
    first_integration_completed BOOLEAN DEFAULT FALSE
);

CREATE UNIQUE INDEX users_email ON users (email);


CREATE TABLE user_oauth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name TEXT,
    slug TEXT,
    integration TEXT,
    suggestion TEXT,
    init_script TEXT
);

CREATE INDEX databases_user_id ON databases (user_id);
CREATE INDEX databases_slug ON databases (slug);


CREATE TABLE notebook_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    database_id INTEGER REFERENCES databases(id) ON DELETE CASCADE,
    stmt TEXT,
    created_at DATETIME
);

CREATE INDEX notebook_queries_database_id ON notebook_queries (database_id);


INSERT INTO users SELECT * FROM users_old;
INSERT INTO user_oauth_tokens SELECT * FROM user_oauth_tokens_old;
INSERT INTO databases SELECT * FROM databases_old;
INSERT INTO notebook_queries SELECT * FROM notebook_queries_old;

DROP TABLE users_old;
DROP TABLE user_oauth_tokens_old;
DROP TABLE databases_old;
DROP TABLE notebook_queries_old;
