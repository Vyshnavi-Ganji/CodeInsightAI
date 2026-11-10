CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), email text UNIQUE NOT NULL,
  password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  encrypted_ai_key text, ai_base_url text, ai_model text
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS encrypted_ai_key text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_base_url text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_model text;
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL, description text NOT NULL DEFAULT '', repo_owner text NOT NULL, repo_name text NOT NULL,
  default_branch text NOT NULL, encrypted_token text, webhook_secret text NOT NULL,
  webhook_id bigint, index_status text NOT NULL DEFAULT 'pending', index_error text,
  last_indexed_at timestamptz, last_commit_sha text, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(owner_id, repo_owner, repo_name)
);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS webhook_id bigint;
ALTER TABLE projects ALTER COLUMN encrypted_token DROP NOT NULL;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS index_status text NOT NULL DEFAULT 'pending';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS index_error text;
CREATE TABLE IF NOT EXISTS commits (
  id bigserial PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  sha text NOT NULL, parent_sha text, message text NOT NULL, author text NOT NULL, committed_at timestamptz,
  file_count int NOT NULL DEFAULT 0, additions int NOT NULL DEFAULT 0, deletions int NOT NULL DEFAULT 0,
  impact jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, sha)
);
CREATE TABLE IF NOT EXISTS source_files (
  id bigserial PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  commit_sha text NOT NULL, path text NOT NULL, language text NOT NULL, size_bytes int NOT NULL DEFAULT 0,
  content text NOT NULL DEFAULT '', content_sha text NOT NULL, imports jsonb NOT NULL DEFAULT '[]'::jsonb,
  UNIQUE(project_id, commit_sha, path)
);
CREATE INDEX IF NOT EXISTS source_files_project_path ON source_files(project_id, path);
CREATE TABLE IF NOT EXISTS knowledge_versions (
  id bigserial PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  commit_sha text NOT NULL, documents jsonb NOT NULL, srs jsonb NOT NULL, graph jsonb NOT NULL,
  generated_at timestamptz NOT NULL DEFAULT now(), engine_version int NOT NULL DEFAULT 1, UNIQUE(project_id, commit_sha)
);
ALTER TABLE knowledge_versions ADD COLUMN IF NOT EXISTS engine_version int NOT NULL DEFAULT 1;
CREATE TABLE IF NOT EXISTS chat_messages (
  id bigserial PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE, role text NOT NULL CHECK(role IN ('user','assistant')),
  content text NOT NULL, citations jsonb NOT NULL DEFAULT '[]'::jsonb, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS webhook_events (
  id bigserial PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  delivery_id text NOT NULL, event text NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, delivery_id)
);
