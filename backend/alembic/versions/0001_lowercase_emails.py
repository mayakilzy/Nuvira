"""Lowercase all stored emails so lookups are case-insensitive

Revision ID: 0001_lowercase_emails
Revises: (none — first migration in this repo)
Create Date: 2026-10-13

SAFETY: refuses to run if two different accounts would collide after
lowercasing (e.g. 'Ali@x.com' and 'ali@x.com'). Those accounts must be
merged/resolved manually first; the migration aborts with a clear message.

Equivalent raw SQL (for review / manual DBA use):

    -- step 1: duplicate check (must return 0 rows before proceeding)
    SELECT LOWER(TRIM(email)) AS normalized, COUNT(*) AS n
    FROM users
    GROUP BY LOWER(TRIM(email))
    HAVING COUNT(*) > 1;

    -- step 2: the actual fix
    UPDATE users SET email = LOWER(TRIM(email));
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_lowercase_emails"
down_revision = None
branch_labels = None
depends_on = None

DUP_CHECK = sa.text(
    """
    SELECT LOWER(TRIM(email)) AS normalized, COUNT(*) AS n
    FROM users
    GROUP BY LOWER(TRIM(email))
    HAVING COUNT(*) > 1
    """
)


def upgrade() -> None:
    conn = op.get_bind()

    # --- Step 1: abort on case-insensitive duplicates BEFORE touching data ---
    duplicates = conn.execute(DUP_CHECK).fetchall()
    if duplicates:
        sample = ", ".join(repr(row.normalized) for row in duplicates[:10])
        more = "" if len(duplicates) <= 10 else f" (+{len(duplicates) - 10} more)"
        raise RuntimeError(
            f"\nABORT: {len(duplicates)} group(s) of case-insensitive duplicate "
            f"emails found: {sample}{more}.\n"
            "Lowercasing would violate the UNIQUE constraint on users.email.\n"
            "Resolve these accounts manually first (merge their data, deactivate "
            "or rename the duplicates), then re-run this migration."
        )

    # --- Step 2: lowercase every stored email ---
    op.execute("UPDATE users SET email = LOWER(TRIM(email))")


def downgrade() -> None:
    # Original casing is not recoverable — lowercase is the canonical form.
    pass
