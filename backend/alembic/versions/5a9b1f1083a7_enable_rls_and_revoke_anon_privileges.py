"""enable_rls_and_revoke_anon_privileges

Revision ID: 5a9b1f1083a7
Revises: e7c2a19d4b8f
Create Date: 2026-09-17 11:50:43.096740

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5a9b1f1083a7'
down_revision: Union[str, Sequence[str], None] = 'e7c2a19d4b8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema:
    1. Enable Row Level Security (RLS) on public.incidents.
    2. Revoke all privileges on public.incidents from Supabase web roles (anon, authenticated).
    3. Enable Row Level Security (RLS) on public.alembic_version.
    4. Revoke all privileges on public.alembic_version from Supabase web roles (anon, authenticated).
    """
    # 1. Enable RLS on public.incidents
    op.execute("ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;")

    # 3. Enable RLS on public.alembic_version (if table exists)
    op.execute("ALTER TABLE IF EXISTS public.alembic_version ENABLE ROW LEVEL SECURITY;")

    # 2 & 4. Revoke ALL privileges from anon and authenticated roles
    # PL/pgSQL DO block checks if the roles exist, guaranteeing compatibility
    # across both managed Supabase environments (where anon/authenticated exist) and standard
    # PostgreSQL environments (e.g. local Docker Compose, CI) where these roles do not exist.
    op.execute(
        """
        DO $$
        BEGIN
            -- Revoke privileges from 'anon' if role exists
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                REVOKE ALL ON TABLE public.incidents FROM anon;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version') THEN
                    REVOKE ALL ON TABLE public.alembic_version FROM anon;
                END IF;
            END IF;

            -- Revoke privileges from 'authenticated' if role exists
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                REVOKE ALL ON TABLE public.incidents FROM authenticated;
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version') THEN
                    REVOKE ALL ON TABLE public.alembic_version FROM authenticated;
                END IF;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """
    Downgrade schema:
    Disable Row Level Security (RLS) on public.incidents and public.alembic_version.
    """
    op.execute("ALTER TABLE IF EXISTS public.alembic_version DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.incidents DISABLE ROW LEVEL SECURITY;")

