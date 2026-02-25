import os
import psycopg2

def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_db():
    print(">>> INIT_DB EJECUTANDOSE")

    try:
        conn = get_connection()
        cur = conn.cursor()

        print(">>> CONEXION EXITOSA")

        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        print(">>> EXTENSION OK")

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

        print(">>> TABLA CREADA O VERIFICADA")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(">>> ERROR EN INIT_DB:", e)
