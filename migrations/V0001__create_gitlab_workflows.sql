-- migrations/V0001__create_gitlab_workflows.sql

CREATE TABLE sekai_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    discord_user_display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE github_workflow_runs (
    request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    github_run_id BIGINT UNIQUE,
    github_run_url TEXT,

    discord_user_id BIGINT NOT NULL,
    discord_channel_id BIGINT NOT NULL,

    conclusion TEXT,

    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
