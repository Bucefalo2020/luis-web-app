import os
import psycopg2
import psycopg2.extras


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


def insert_question_version(pregunta_id, version, nivel, tipo, contenido):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO preguntas (pregunta_id, version, nivel, tipo, contenido)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (pregunta_id, version) DO NOTHING;
    """, (
        pregunta_id,
        version,
        nivel,
        tipo,
        psycopg2.extras.Json(contenido)
    ))

    conn.commit()
    cur.close()
    conn.close()


def seed_nivel_1_questions():
    preguntas = [
        {
            "pregunta_id": "ZS_N1_001",
            "contenido": {
                "eje": "Elegibilidad y Perfilamiento",
                "escenario": "Un ejecutivo comercial recibe la solicitud de un cliente interesado en contratar el producto asegurador ofrecido bajo el convenio Zurich Santander. El cliente cumple parcialmente con los criterios de perfilamiento establecidos en el documento.",
                "pregunta": "Explique qué verificaciones deben realizarse antes de confirmar la elegibilidad del cliente y cómo se documenta correctamente el análisis conforme a los lineamientos institucionales.",
                "conceptos_clave": [
                    "criterios de elegibilidad",
                    "perfilamiento del cliente",
                    "validación documental",
                    "análisis de riesgo",
                    "lineamientos internos"
                ],
                "min_palabras": 120
            }
        },
        {
            "pregunta_id": "ZS_N1_002",
            "contenido": {
                "eje": "Coberturas y Alcance Contractual",
                "escenario": "Un cliente interpreta que determinada situación está cubierta automáticamente por la póliza, aunque el documento establece condiciones específicas para su activación.",
                "pregunta": "Describa cómo debe analizarse el alcance real de la cobertura y qué elementos contractuales deben explicarse al cliente para evitar interpretaciones incorrectas.",
                "conceptos_clave": [
                    "condiciones de cobertura",
                    "exclusiones",
                    "limites asegurados",
                    "terminos contractuales",
                    "comunicacion clara"
                ],
                "min_palabras": 120
            }
        },
        {
            "pregunta_id": "ZS_N1_003",
            "contenido": {
                "eje": "Suscripcion Simplificada",
                "escenario": "Durante una campaña comercial, se aplican mecanismos de suscripción simplificada para agilizar la colocación del producto.",
                "pregunta": "Explique cuáles son los controles mínimos que deben mantenerse activos aun bajo esquemas simplificados y por qué son relevantes para la sostenibilidad del portafolio.",
                "conceptos_clave": [
                    "suscripcion",
                    "controles minimos",
                    "evaluacion de riesgo",
                    "sostenibilidad tecnica",
                    "politicas internas"
                ],
                "min_palabras": 120
            }
        },
        {
            "pregunta_id": "ZS_N1_004",
            "contenido": {
                "eje": "Gestion de Informacion y Cumplimiento",
                "escenario": "Un asesor omite registrar información relevante proporcionada por el cliente durante el proceso de contratación.",
                "pregunta": "Explique las implicaciones técnicas y operativas de una omisión en el registro de información y cómo debe prevenirse conforme al documento institucional.",
                "conceptos_clave": [
                    "registro de informacion",
                    "trazabilidad",
                    "cumplimiento normativo",
                    "documentacion",
                    "control interno"
                ],
                "min_palabras": 120
            }
        },
        {
            "pregunta_id": "ZS_N1_005",
            "contenido": {
                "eje": "Transparencia Comercial",
                "escenario": "Un cliente manifiesta inconformidad argumentando que no comprendió adecuadamente las condiciones del producto al momento de la contratación.",
                "pregunta": "Describa qué prácticas deben implementarse durante el proceso comercial para garantizar transparencia y alineación con las disposiciones del documento Zurich Santander.",
                "conceptos_clave": [
                    "transparencia",
                    "informacion clara",
                    "consentimiento informado",
                    "condiciones contractuales",
                    "responsabilidad comercial"
                ],
                "min_palabras": 120
            }
        }
    ]

    for p in preguntas:
        insert_question_version(
            pregunta_id=p["pregunta_id"],
            version=1,
            nivel="nivel_1",
            tipo="open",
            contenido=p["contenido"]
        )

def get_random_active_question(nivel):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT *
        FROM preguntas
        WHERE nivel = %s
          AND estado = 'activo'
        ORDER BY RANDOM()
        LIMIT 1;
    """, (nivel,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result
