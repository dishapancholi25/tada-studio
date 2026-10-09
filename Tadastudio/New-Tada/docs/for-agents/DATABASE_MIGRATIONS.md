# Database Migrations

This project does **NOT** use Alembic. The `backend/alembic/` directory is legacy and unused. Never create Alembic migration files.

## How It Works

Database schema management uses a two-phase custom system that runs on application startup via `init_db()` (called from `backend/app.py`).

### Phase 1: Table Creation

`Base.metadata.create_all(bind=engine)` creates any tables defined by SQLAlchemy models that don't yet exist. This is idempotent — existing tables are not modified.

### Phase 2: Custom Migrations

A registry of Python migration functions runs in order. Each function is idempotent and checks whether the change already exists before applying it.

## Key Files

| File | Purpose |
|------|---------|
| `backend/services/database/migrations/__init__.py` | `init_db()` entry point, advisory lock, two-phase execution |
| `backend/services/database/migrations/registry.py` | Ordered list of `Migration` objects |
| `backend/services/database/migrations/schema_updates.py` | Migration function implementations |
| `backend/models/` | SQLAlchemy model definitions (auto-discovered via `__init__.py`) |

## Adding a New Column to an Existing Table

Three steps are required:

### 1. Update the SQLAlchemy Model

Edit the model class in `backend/models/` to add the new column:

```python
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text

visible_to_groups = Column(
    JSONB, nullable=False, server_default=text("'[]'::jsonb")
)
```

> `create_all()` does not alter existing tables, so the model change alone won't add the column to a database that already has the table. The migration function (step 2) handles that.

### 2. Create a Migration Function

Add a function to `backend/services/database/migrations/schema_updates.py`. Follow this pattern:

```python
def add_my_new_column(conn: Connection) -> None:
    """Add my_column to my_table.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='my_table' AND column_name='my_column'
            """)
        )
        if not result.fetchone():
            logger.info("%s Adding my_column to my_table", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE my_table
                    ADD COLUMN my_column JSONB NOT NULL DEFAULT '[]'::jsonb
                """)
            )
            # Add indexes if needed
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_my_table_my_column
                    ON my_table USING GIN (my_column)
                """)
            )
            conn.commit()
            logger.info("%s Added my_column successfully", LOG_PREFIX)
        else:
            logger.debug("%s my_column already exists in my_table", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add my_column to my_table: %s", LOG_PREFIX, e)
```

Rules:

- Always check `information_schema.columns` (or `information_schema.tables` for new tables) before making changes
- Always wrap in try/except and log warnings on failure
- Call `conn.commit()` after the change
- Use `CREATE INDEX IF NOT EXISTS` for indexes

### 3. Register the Migration

In `backend/services/database/migrations/registry.py`:

1. Import the function at the top of the file
2. Append a new `Migration(...)` entry to the **end** of the `MIGRATIONS` list

```python
# In imports
from .schema_updates import add_my_new_column

# At the END of MIGRATIONS list
Migration(
    name="add_my_new_column",
    func=add_my_new_column,
    enabled=True,
),
```

> Order matters. Always append to the end of the list.

## Creating a New Table

For brand-new tables, `Base.metadata.create_all()` handles creation automatically from the SQLAlchemy model. A migration function is only needed if you also need to:

- Seed initial data
- Add special indexes not expressed in the model
- Backfill data from other tables

## Worker Safety

The system uses a PostgreSQL advisory lock (`pg_try_advisory_lock(123456789)`) so only one application worker runs migrations. Other workers wait briefly and continue without error.
