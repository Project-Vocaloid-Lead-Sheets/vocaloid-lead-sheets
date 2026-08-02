-- migrations/V0001__create_github_workflows.sql

CREATE TABLE sekai_log (
    id INTEGER PRIMARY KEY,

    discord_user_id INTEGER NOT NULL,
    discord_user_display_name TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE github_workflow_runs (
    request_id INTEGER PRIMARY KEY,

    github_run_id INTEGER NOT NULL UNIQUE,
    github_run_url TEXT NOT NULL,

    discord_user_id INTEGER NOT NULL,
    discord_channel_id INTEGER NOT NULL,

    conclusion TEXT,

    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);
