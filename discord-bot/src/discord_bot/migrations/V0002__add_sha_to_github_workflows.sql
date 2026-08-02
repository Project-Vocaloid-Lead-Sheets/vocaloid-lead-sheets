-- V0002__add_sha_to_github_workflows.sql

ALTER TABLE github_workflow_runs
ADD COLUMN git_sha TEXT default "???";
