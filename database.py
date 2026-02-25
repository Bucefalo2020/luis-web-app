import os
import psycopg2


def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Habilita extensión para UUID si no existe
    cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # Tabla versionable de preguntas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preguntas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pregunta_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            nivel TEXT NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'activo',
            contenido JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (pregunta_id, version)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
