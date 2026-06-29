# Database Schema — Phase 0.1

Engine: PostgreSQL 16
ORM: SQLAlchemy 2 (async)
Migrations: Alembic

## Tables

### users
Primary identity table. Synced from Clerk on first login.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | VARCHAR(255) UNIQUE | |
| username | VARCHAR(100) UNIQUE | |
| password_hash | TEXT | Empty for Clerk-only users |
| is_active | BOOLEAN | Default true |
| is_verified | BOOLEAN | Default false |
| clerk_id | VARCHAR(255) UNIQUE NULL | Clerk user ID |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### profiles
One-to-one with users.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | CASCADE DELETE |
| full_name | VARCHAR(200) NULL | |
| avatar_url | TEXT NULL | |
| bio | TEXT NULL | |
| timezone | VARCHAR(100) | Default UTC |
| language | VARCHAR(10) | Default en |
| created_at / updated_at | TIMESTAMPTZ | |

### settings
One-to-one with users.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | CASCADE DELETE |
| theme | VARCHAR(20) | dark / light / system |
| notifications_enabled | BOOLEAN | Default true |
| llm_model | VARCHAR(100) | Default llama-3.3-70b-versatile |
| temperature | FLOAT | Default 0.7 |
| created_at / updated_at | TIMESTAMPTZ | |

### conversations
A thread of messages belonging to one user.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | CASCADE DELETE, indexed |
| title | VARCHAR(500) NULL | Auto-set from first message |
| is_archived | BOOLEAN | Default false |
| created_at / updated_at | TIMESTAMPTZ | |

### messages
Individual messages within a conversation.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| conversation_id | UUID FK → conversations | CASCADE DELETE, indexed |
| role | VARCHAR(20) | CHECK IN ('user','assistant','system') |
| content | TEXT | |
| token_count | INTEGER NULL | |
| created_at | TIMESTAMPTZ | |

### sessions
JWT session tracking (for future denylist support).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users | CASCADE DELETE |
| token_hash | TEXT | |
| ip_address | VARCHAR(45) NULL | |
| user_agent | TEXT NULL | |
| expires_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### audit_logs
Records of actions for security and compliance.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK → users NULL | SET NULL on delete |
| action | VARCHAR(100) | e.g., user.login |
| resource | VARCHAR(100) NULL | |
| ip_address | VARCHAR(45) NULL | |
| status_code | INTEGER NULL | |
| metadata | JSONB NULL | |
| created_at | TIMESTAMPTZ | |

### system_logs
Structured application logs mirrored to DB for audit purposes.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| level | VARCHAR(20) | INFO / WARNING / ERROR |
| message | TEXT | |
| context | JSONB NULL | |
| created_at | TIMESTAMPTZ | |

### prompt_templates
Configurable LLM prompts. Never hardcoded.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) UNIQUE | e.g., default_system |
| description | TEXT NULL | |
| template | TEXT | The prompt body |
| variables | JSONB NULL | List of variable names |
| is_active | BOOLEAN | Default true |
| created_at / updated_at | TIMESTAMPTZ | |

### api_usage
LLM token consumption per request.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK NULL | SET NULL on delete |
| provider | VARCHAR(50) | groq / openai / etc |
| model | VARCHAR(100) | |
| prompt_tokens | INTEGER | |
| completion_tokens | INTEGER | |
| total_tokens | INTEGER | |
| latency_ms | INTEGER NULL | |
| created_at | TIMESTAMPTZ | |

## Running Migrations

```bash
# Apply all migrations
cd apps/api && alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "describe change"

# Rollback one step
alembic downgrade -1
```

## Seed Data

```bash
python scripts/seed.py
```

Seeds the default `prompt_templates` row (`default_system`).
