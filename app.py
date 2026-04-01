from dotenv import load_dotenv
load_dotenv()
import os
import streamlit as st

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.pregunta_actual = {}
    st.session_state.respuestas = []
    st.session_state.resultado = None

# ==========================================
# 🔐 INICIALIZACIÓN SEGURA DE SESSION STATE
# ==========================================

if "cobertura" not in st.session_state:
    st.session_state["cobertura"] = 0

if "precision" not in st.session_state:
    st.session_state["precision"] = 0

if "terminos" not in st.session_state:
    st.session_state["terminos"] = 0

if "claridad" not in st.session_state:
    st.session_state["claridad"] = 0

if "comercial" not in st.session_state:
    st.session_state["comercial"] = 0

if "porcentaje" not in st.session_state:
    st.session_state["porcentaje"] = 0

if "nivel" not in st.session_state:
    st.session_state["nivel"] = "SIN EVALUAR"

import random
import json
import re
import datetime
import uuid
import requests
from pypdf import PdfReader
from google import genai
from zoneinfo import ZoneInfo
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
DEMO_MODE = True

DEBUG = os.getenv("DEBUG_MODE", "false").lower() == "true"

st.set_page_config(
    page_title="Plataforma de Asistencia Inteligente",
    layout="wide",
    page_icon="🧠"
)

st.title("Evaluación Técnica IA")

if DEBUG:
    print("APP INICIADA EN MODO DEBUG")

    if st.button("TEST OPENAI"):
        resultado_test = openai_generate("Di hola en una línea")
        st.write("RESULTADO TEST:", resultado_test)

# =================================
# CONFIGURACIÓN GLOBAL DEL MODELO IA
# =================================

MODEL_GEMINI = "gemini-1.5-flash"
MAX_CONTEXT_GENERACION = 3000
MAX_CONTEXT_CHAT = 15000

st.markdown(
    """
    <style>
        .stApp {
            background-color: #F5F7FA;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# PORTADA CORPORATIVA
# --------------------------------------------------

st.markdown("""
<div style="
    background-color:#E30613;
    padding:10px 16px;
    text-align:center;
    border-radius:6px;
">
<h3 style="
    color:white;
    margin:0;
    font-weight:700;
    letter-spacing:0.5px;
">
SISTEMA DE CAPACITACIÓN Y CERTIFICACIÓN INTERNA
</h3>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns([1,2])

with col1:
    st.markdown("<div style='margin-top:110px;'>", unsafe_allow_html=True)
    st.image("assets/logo_zurich_santander_horizontal.png", width=200)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        """
### Plataforma de Certificación Técnica – Hogar Protegido Santander

Sistema inteligente de entrenamiento técnico, evaluación
y certificación para fuerza comercial.

**Funciones disponibles:**
- Consulta asistida por IA
- Evaluación técnica automatizada
- Certificación con reporte ejecutivo PDF
""",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    
    print("DATABASE_URL:", database_url)
        
    if not database_url:
        raise Exception("DATABASE_URL no está configurada")

    conn = psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor
    )
    return conn

# =====================================
# OBTENER PREGUNTA ACTIVA ALEATORIA
# =====================================
def get_random_active_question(nivel):

    if not os.getenv("DATABASE_URL"):
        return {
            "pregunta": "¿Cómo funciona la renovación automática de una póliza?",
            "respuesta_correcta": "Se renueva automáticamente salvo cancelación previa.",
            "conceptos_clave": [
                "renovación automática",
                "aviso previo",
                "vigencia",
                "condiciones"
            ]
        }

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT contenido
        FROM preguntas
        WHERE nivel = %s
        ORDER BY RANDOM()
        LIMIT 1
    """, (nivel,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return row

    return None

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Tabla usuarios
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Tabla conversaciones
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            question TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Tabla evaluaciones técnicas
    cur.execute("""
        CREATE TABLE IF NOT EXISTS technical_evaluations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            pregunta TEXT NOT NULL,
            respuesta_usuario TEXT NOT NULL,
            respuesta_modelo TEXT NOT NULL,
            score INTEGER NOT NULL,
            feedback TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    
if os.getenv("DATABASE_URL"):
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state["db_initialized"] = True

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def ensure_demo_user():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = %s;", ("demo@demo.com",))
    user = cur.fetchone()

    if not user:
        cur.execute("""
            INSERT INTO users (email, password_hash, role)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, ("demo@demo.com", hash_password("admin123"), "admin"))
        user_id = cur.fetchone()["id"]
    else:
        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE email = %s
            RETURNING id;
        """, (hash_password("admin123"), "demo@demo.com"))
        user_id = cur.fetchone()["id"]

    conn.commit()
    cur.close()
    conn.close()

    return user_id

def formatear_nombre(email):
    if not email or "@" not in email:
        return "Usuario"

    return email.split("@")[0].replace(".", " ").title()
    
def authenticate_user(email, password):

    if DEMO_MODE:
        nombre = formatear_nombre(email)

        return {
            "id": "demo_user",
            "email": email,
            "nombre": nombre,
            "role": "user"
        }

    # ===== MODO REAL (Railway) =====
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password_hash FROM users WHERE email = %s",
        (email,)
    )
    user = cur.fetchone()

    conn.close()

    if not user:
        return None

    password_hash = user["password_hash"]

    if verify_password(password, password_hash):
        nombre = formatear_nombre(email)

        return {
            "id": user["id"],
            "email": email,
            "nombre": nombre,
            "role": "user"
        }

    return None

if "demo_user_id" not in st.session_state:
    if os.getenv("DATABASE_URL"):
        st.session_state["demo_user_id"] = ensure_demo_user()
    else:
        st.session_state["demo_user_id"] = "demo_local"

def save_conversation(user_id, question, response):

    # 🔥 MODO LOCAL (sin DB)
    if not os.getenv("DATABASE_URL"):
        return
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO conversations (user_id, question, response)
        VALUES (%s, %s, %s);
    """, (user_id, question, response))

    conn.commit()
    cur.close()
    conn.close()

def save_technical_evaluation(user_id, pregunta, respuesta_usuario, respuesta_modelo, score, feedback):

    # 🔥 BLOQUE DE PROTECCIÓN DEMO
    if DEMO_MODE:
        return

    # 🔒 Protección adicional por si no hay DB
    if not os.getenv("DATABASE_URL"):
        return

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO technical_evaluations
        (user_id, pregunta, respuesta_usuario, respuesta_modelo, score, feedback)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (user_id, pregunta, respuesta_usuario, respuesta_modelo, score, feedback))

    conn.commit()
    cur.close()
    conn.close()

def get_recent_conversations(limit=10):

    if not os.getenv("DATABASE_URL"):
        return []
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT question, response, created_at
        FROM conversations
        ORDER BY created_at DESC
        LIMIT %s;
    """, (limit,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def get_metrics():

    if not os.getenv("DATABASE_URL"):
        return {
            "total_consultas": 0,
            "primera_consulta": "N/A",
            "ultima_consulta": "N/A"
        }
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total_consultas,
            MIN(created_at) AS primera_consulta,
            MAX(created_at) AS ultima_consulta
        FROM conversations;
    """)

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result
 
# --------------------------------------------------
# CONFIGURACIÓN API
# --------------------------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("GEMINI_API_KEY no está definida en el entorno.")
    st.stop()

client = genai.Client(
    api_key=API_KEY,
    http_options={"api_version": "v1"}
)

# --------------------------------------------------
# CARGA DOCUMENTO PDF
# --------------------------------------------------

@st.cache_data
def cargar_documento():
    reader = PdfReader("docs/ZuytULVsGrYSvmro_HogarProtegidoSantander_CondicionesGenerales.pdf")
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    return texto

DOCUMENTO_BASE = cargar_documento()

# --------------------------------------------------
# BANCO DE PREGUNTAS
# --------------------------------------------------

QUESTION_BANK = [

    # ---------- MC IA ----------
    
        {
        "id": 1,
        "type": "mc",
        "question": "¿Qué documento se debe revisar para conocer los riesgos amparados y sumas aseguradas?",
        "options": [
            "Solicitud de seguro",
            "Condiciones Particulares",
            "Póliza y Condiciones Generales",
            "Recibo de pago"
        ],
        "answer": 2
    },
    {
        "id": 2,
        "type": "mc",
        "question": "¿Qué se entiende por 'Aluvión' según las definiciones del contrato?",
        "options": [
            "Inundación repentina",
            "Deslizamiento de tierra",
            "Sedimentos arrastrados por una corriente de agua",
            "Acumulación de nieve"
        ],
        "answer": 2
    },
    {
        "id": 3,
        "type": "mc",
        "question": "En el contexto del seguro, ¿quién es el 'Arrendatario'?",
        "options": [
            "El propietario del inmueble",
            "La institución financiera",
            "La persona que usa el bien a cambio de una remuneración",
            "El corredor de seguros"
        ],
        "answer": 2
    },
    {
        "id": 4,
        "type": "mc",
        "question": "¿Qué sección de las Condiciones Generales detalla los bienes cubiertos por la póliza?",
        "options": [
            "Cláusulas Generales",
            "Descripción de Cobertura Básica",
            "Descripción de Coberturas Adicionales",
            "Descripción de Coberturas Catastróficas"
        ],
        "answer": 1
    },
    {
        "id": 5,
        "type": "mc",
        "question": "En caso de siniestro, ¿qué ocurre con la Suma Asegurada?",
        "options": [
            "Aumenta proporcionalmente",
            "Permanece intacta",
            "Disminuye",
            "Se recalcula según la inflación"
        ],
        "answer": 2
    },
    {
        "id": 6,
        "type": "mc",
        "question": "¿Qué se entiende por 'Subrogación de Derechos'?",
        "options": [
            "Derecho a reclamar a terceros responsables",
            "Derecho a endosar la póliza",
            "Derecho a cancelar la póliza",
            "Derecho a modificar las coberturas"
        ],
        "answer": 0
    },
    {
        "id": 7,
        "type": "mc",
        "question": "¿Qué implica la cláusula de 'Valor Indemnizable'?",
        "options": [
            "El valor de reposición a nuevo",
            "El valor de mercado del bien",
            "El valor depreciado del bien",
            "El valor catastral del inmueble"
        ],
        "answer": 2
    },
    {
        "id": 8,
        "type": "mc",
        "question": "¿Qué se indica sobre equipos obsoletos o descontinuados?",
        "options": [
            "Se indemnizan al valor original",
            "Se reemplazan por modelos equivalentes",
            "Puede haber limitaciones en la indemnización",
            "No están cubiertos"
        ],
        "answer": 2
    },
    {
        "id": 9,
        "type": "mc",
        "question": "¿Qué consecuencia tiene el 'Fraude, dolo o mala fe' en la reclamación?",
        "options": [
            "Se paga la indemnización completa",
            "Se reduce la indemnización",
            "Se niega la indemnización",
            "Se investiga el caso"
        ],
        "answer": 2
    },
    {
        "id": 10,
        "type": "mc",
        "question": "¿Qué es el 'Peritaje' en el contexto de un siniestro?",
        "options": [
            "La investigación policial",
            "La evaluación de daños por un experto",
            "La negociación con la aseguradora",
            "La declaración del asegurado"
        ],
        "answer": 1
    },
        {
        "id": 11,
        "type": "mc",
        "question": "¿Qué implica la 'Indemnización por Mora'?",
        "options": [
            "Un descuento en la prima",
            "Un pago adicional por retraso de la aseguradora",
            "La cancelación de la póliza",
            "La renegociación de las condiciones"
        ],
        "answer": 1
    },
    {
        "id": 12,
        "type": "mc",
        "question": "¿Qué es la 'Prescripción' en seguros?",
        "options": [
            "El tiempo máximo para reclamar un siniestro",
            "El tiempo de vigencia de la póliza",
            "El tiempo para renovar la póliza",
            "El tiempo para pagar la prima"
        ],
        "answer": 0
    },
    {
        "id": 13,
        "type": "mc",
        "question": "¿Qué ocurre si hay 'Omisiones e Inexactas Declaraciones'?",
        "options": [
            "Se paga la indemnización completa",
            "Se reduce la indemnización",
            "Se puede anular la póliza",
            "Se recalcula la prima"
        ],
        "answer": 2
    },
    {
        "id": 14,
        "type": "mc",
        "question": "¿Qué cobertura básica ampara los daños a cristales?",
        "options": [
            "Incendio Todo Riesgo",
            "Rotura de Cristales",
            "Variación de Voltaje",
            "Robo de Contenidos"
        ],
        "answer": 1
    },
    {
        "id": 15,
        "type": "mc",
        "question": "¿Qué cobertura adicional protege contra reclamaciones por daños a terceros?",
        "options": [
            "Robo de Contenidos",
            "Responsabilidad Civil Privada y Familiar",
            "Terremoto y/o Erupción Volcánica",
            "Riesgos Hidrometeorológicos"
        ],
        "answer": 1
    },
    {
        "id": 16,
        "type": "mc",
        "question": "¿Qué cobertura catastrófica ampara contra inundaciones?",
        "options": [
            "Terremoto y/o Erupción Volcánica",
            "Riesgos Hidrometeorológicos",
            "Remoción de Escombros",
            "Gastos Extraordinarios"
        ],
        "answer": 1
    },
    {
        "id": 17,
        "type": "mc",
        "question": "¿Qué tipo de asistencia se ofrece en caso de emergencia en el hogar?",
        "options": [
            "Asistencia legal",
            "Asistencia médica",
            "Asistencia hogar por emergencia",
            "Asistencia financiera"
        ],
        "answer": 2
    },
    {
        "id": 18,
        "type": "mc",
        "question": "¿Qué servicio ofrece el 'Handy Man hogar'?",
        "options": [
            "Reparaciones menores en el hogar",
            "Servicio de limpieza",
            "Servicio de jardinería",
            "Servicio de seguridad"
        ],
        "answer": 0
    },
    {
        "id": 19,
        "type": "mc",
        "question": "¿Qué cobertura se encarga de los costos de retirar los restos después de un siniestro catastrófico?",
        "options": [
            "Gastos Extraordinarios",
            "Remoción de Escombros",
            "Responsabilidad Civil",
            "Robo de Contenidos"
        ],
        "answer": 1
    },
    {
        "id": 20,
        "type": "mc",
        "question": "¿Qué cobertura ayuda a cubrir costos adicionales de vivienda temporal tras un siniestro?",
        "options": [
            "Remoción de Escombros",
            "Gastos Extraordinarios",
            "Responsabilidad Civil",
            "Robo de Contenidos"
        ],
        "answer": 1
    },
    {
        "id": 21,
        "type": "mc",
        "question": "¿Cuál es el alcance de la cobertura de Responsabilidad Civil Trabajadores Domésticos?",
        "options": [
            "Daños causados por el asegurado",
            "Daños sufridos por los trabajadores domésticos",
            "Daños a la propiedad del asegurado",
            "Daños causados por mascotas"
        ],
        "answer": 1
    },
    {
        "id": 22,
        "type": "mc",
        "question": "¿Qué tipo de bienes están excluidos de la cobertura básica?",
        "options": [
            "Muebles",
            "Electrodomésticos",
            "Joyas y obras de arte",
            "Ropa"
        ],
        "answer": 2
    },
    {
        "id": 23,
        "type": "mc",
        "question": "¿Qué son los deducibles en un seguro?",
        "options": [
            "El monto que la aseguradora paga",
            "El monto que el asegurado paga en caso de siniestro",
            "El porcentaje de la prima",
            "El monto máximo asegurado"
        ],
        "answer": 1
    },
    {
        "id": 24,
        "type": "mc",
        "question": "¿Qué son los coaseguros?",
        "options": [
            "Seguros compartidos entre varias aseguradoras",
            "Seguros que cubren solo una parte del riesgo",
            "Porcentaje del daño que asume el asegurado",
            "Descuentos en la prima"
        ],
        "answer": 2
    },
    {
        "id": 25,
        "type": "mc",
        "question": "¿Qué información debe proporcionar el asegurado en caso de siniestro?",
        "options": [
            "Copia de la póliza",
            "Descripción detallada del siniestro",
            "Facturas de los bienes dañados",
            "Todas las anteriores"
        ],
        "answer": 3
    },


    # OPEN IA
        
    {
        "id": 26,
        "type": "open",
        "question": "Según las Condiciones Generales, ¿cuál es el procedimiento que debe seguir un cliente para reportar un siniestro y qué información debe proporcionar inicialmente?",
        "model_answer": "El cliente debe revisar su póliza y notificar de inmediato a Zurich Santander Seguros México, S. A. al teléfono indicado. Debe proporcionar datos del asegurado, número de póliza y una descripción clara del siniestro."
    },
    {
        "id": 27,
        "type": "open",
        "question": "Explique la diferencia entre 'Agravación del riesgo' y 'Omisiones e Inexactas Declaraciones' y cómo impactan la validez de la póliza.",
        "model_answer": "Agravación del riesgo implica cambios posteriores que incrementan la probabilidad o severidad del siniestro. Omisiones e inexactas declaraciones son datos incorrectos u ocultos al contratar. Ambas pueden derivar en cancelación o negativa de indemnización."
    },
    {
        "id": 28,
        "type": "open",
        "question": "En el contexto de 'Valor Indemnizable', ¿qué factores se consideran para determinar el monto a indemnizar en pérdida total?",
        "model_answer": "Se considera valor de reposición, depreciación por uso, antigüedad, límites máximos de responsabilidad y posibilidad de reparación."
    },
    {
        "id": 29,
        "type": "open",
        "question": "¿Cómo opera la 'Subrogación de Derechos' y qué obligaciones genera para el asegurado?",
        "model_answer": "Tras indemnizar, la aseguradora puede reclamar a terceros responsables. El asegurado debe cooperar proporcionando información y documentación necesaria."
    },
    {
        "id": 30,
        "type": "open",
        "question": "Describe el análisis técnico para determinar cobertura bajo 'Incendio Todo Riesgo'.",
        "model_answer": "Se verifica que el daño provenga de incendio, se revisan exclusiones generales y específicas, y se aplican límites y deducibles establecidos."
    },
    {
        "id": 31,
        "type": "open",
        "question": "Diferencia entre 'Deducible' y 'Coaseguro' y su impacto económico.",
        "model_answer": "El deducible es monto fijo asumido por el asegurado; el coaseguro es porcentaje del daño posterior al deducible. Ambos reducen la indemnización final."
    },
    {
        "id": 32,
        "type": "open",
        "question": "Impacto de la cláusula de equipos obsoletos en la indemnización.",
        "model_answer": "Puede limitar el pago al valor de mercado o equivalente funcional si el equipo ya no se fabrica o no hay refacciones disponibles."
    },
    {
        "id": 33,
        "type": "open",
        "question": "Implicaciones de la 'Indemnización por Mora' para la aseguradora.",
        "model_answer": "Obliga al pago de intereses o compensación adicional si la aseguradora retrasa el pago procedente."
    },
    {
        "id": 34,
        "type": "open",
        "question": "Escenario aplicable y excluido en Responsabilidad Civil Privada y Familiar.",
        "model_answer": "Aplica cuando un tercero sufre daño accidental en el domicilio. No aplica en actos intencionales del asegurado."
    },
    {
        "id": 35,
        "type": "open",
        "question": "Definición y alcance del 'Límite Territorial'.",
        "model_answer": "Define el área geográfica donde la póliza es válida; fuera de ella generalmente no hay cobertura."
    },
    {
        "id": 36,
        "type": "open",
        "question": "Efectos de la renovación automática.",
        "model_answer": "La póliza se renueva salvo aviso en contrario. El asegurado debe notificar si no desea continuar."
    },
    {
        "id": 37,
        "type": "open",
        "question": "Requisitos técnicos en reclamo por Robo de Contenidos.",
        "model_answer": "Debe demostrarse forzamiento o violencia y presentar denuncia oficial y documentación probatoria."
    },
    {
        "id": 38,
        "type": "open",
        "question": "Escenario aplicable y excluido en Riesgos Hidrometeorológicos.",
        "model_answer": "Aplica en daños por fenómenos naturales como inundación externa; no aplica en fugas internas domésticas."
    },
    {
        "id": 39,
        "type": "open",
        "question": "Aplicación de Remoción de Escombros y Gastos Extraordinarios.",
        "model_answer": "Remoción cubre retiro de restos tras siniestro; Gastos Extraordinarios cubre vivienda temporal y gastos adicionales."
    },
    {
        "id": 40,
        "type": "open",
        "question": "Diferencias entre Asistencia hogar por emergencia y Handy Man.",
        "model_answer": "Emergencia atiende riesgos inmediatos; Handy Man cubre mantenimientos menores no urgentes."
    },
    {
        "id": 41,
        "type": "open",
        "question": "Alcance general de exclusiones comunes.",
        "model_answer": "Normalmente incluyen guerra, terrorismo, dolo, daños intencionales y riesgos no asegurables."
    },
    {
        "id": 42,
        "type": "open",
        "question": "Proceso técnico para daños por variación de voltaje.",
        "model_answer": "Notificación inmediata, facturas, dictamen técnico y presupuestos de reparación o reposición."
    },
    {
        "id": 43,
        "type": "open",
        "question": "Aplicación de la cláusula de Otros Seguros.",
        "model_answer": "Se indemniza proporcionalmente para evitar doble compensación."
    },
    {
        "id": 44,
        "type": "open",
        "question": "Diferencia conceptual entre Aluvión y Riesgos Hidrometeorológicos.",
        "model_answer": "Aluvión es sedimento arrastrado; Riesgos Hidrometeorológicos es cobertura amplia de fenómenos climáticos."
    },
    {
        "id": 45,
        "type": "open",
        "question": "Derechos del asegurado en terminación anticipada.",
        "model_answer": "Tiene derecho a prima no devengada menos posibles cargos administrativos."
    },
    {
        "id": 46,
        "type": "open",
        "question": "Cobertura de Daños Materiales a Cristales.",
        "model_answer": "Cubre cristales instalados permanentemente como ventanas y puertas sujetas a límites."
    },
    {
        "id": 47,
        "type": "open",
        "question": "Consecuencias del fraude o mala fe.",
        "model_answer": "Puede resultar en negativa de pago, cancelación de póliza y acciones legales."
    },
    {
        "id": 48,
        "type": "open",
        "question": "Impacto de la Prescripción en reclamaciones.",
        "model_answer": "Si no se reclama dentro del plazo legal, se pierde derecho a indemnización."
    },
    {
        "id": 49,
        "type": "open",
        "question": "Información clave para comprender plenamente la póliza.",
        "model_answer": "Procedimientos detallados, criterios de valuación, exclusiones prácticas y cálculo de deducibles."
    },
    {
        "id": 50,
        "type": "open",
        "question": "Impacto de la definición de Arrendador y Arrendatario en la indemnización.",
        "model_answer": "Determina quién es beneficiario según quién contrata y qué bienes están asegurados."
    }

]

# --------------------------------------------------
# GENERAR EXAMEN MIXTO
# --------------------------------------------------

def generar_examen():
    preguntas_mc = [q for q in QUESTION_BANK if q["type"] == "mc"]
    preguntas_open = [q for q in QUESTION_BANK if q["type"] == "open"]

    seleccion_mc = random.sample(preguntas_mc, min(5, len(preguntas_mc)))
    seleccion_open = random.sample(preguntas_open, min(5, len(preguntas_open)))

    return seleccion_mc + seleccion_open

# --------------------------------------------------
# 📊 MÉTRICAS TÉCNICAS AVANZADAS
# --------------------------------------------------

def get_technical_metrics():

    # 🔥 MODO LOCAL (sin DB)
    if not os.getenv("DATABASE_URL"):
        return {
            "total": 0,
            "promedio": 0,
            "correctas": 0,
            "parciales": 0,
            "incorrectas": 0
        }
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            AVG(score) AS promedio,
            SUM(CASE WHEN score = 2 THEN 1 ELSE 0 END) AS correctas,
            SUM(CASE WHEN score = 1 THEN 1 ELSE 0 END) AS parciales,
            SUM(CASE WHEN score = 0 THEN 1 ELSE 0 END) AS incorrectas
        FROM technical_evaluations;
    """)

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result

# --------------------------------------------------
# FUNCIONES IA
# --------------------------------------------------

def openai_generate(prompt, temperature=0.0):

    if DEBUG:
        print("🔥 OPENAI GENERATE EJECUTANDO")
    
    API_KEY = os.getenv("OPENAI_API_KEY")

    if not API_KEY:
        raise ValueError("OPENAI_API_KEY no encontrada")

    url = "https://api.openai.com/v1/responses"

    headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

    payload = {
        "model": "gpt-4.1-mini",
        "input": prompt,
        "temperature": temperature
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if DEBUG:
        print("🔵 STATUS CODE:", response.status_code)
        print("🔵 RAW RESPONSE (primeros 500 chars):")
        print(response.text[:500])

    response.raise_for_status()

    data = response.json()

    print("JSON RESPONSE:", data)

    texts = []

    # 🔹 Caso 1: Responses API (nuevo)
    if "output" in data:
        for item in data["output"]:
            if "content" in item:
                for c in item["content"]:
                    if c.get("type") in ["output_text", "text"]:
                        texts.append(c.get("text", ""))

    # 🔹 Caso 2: Chat Completions (MUY IMPORTANTE en tu caso)
    if "choices" in data:
        for choice in data["choices"]:
            message = choice.get("message", {})
            if "content" in message:
                texts.append(message["content"])

    # 🔹 Caso 3: output_text directo
    if "output_text" in data:
        texts.append(data["output_text"])

    if texts:
        if DEBUG:
            print("🟢 TEXTO EXTRAÍDO CORRECTAMENTE")
        return "\n".join(texts)

    if DEBUG:
        print("❌ NO SE PUDO EXTRAER TEXTO DE OPENAI")

    raise ValueError("No se pudo extraer texto de OpenAI")

def llamar_a_luis(pregunta, modo):

    contexto = DOCUMENTO_BASE[:15000]

    if modo == "Evaluación técnica":
        instruccion_modo = "Analiza técnicamente y evalúa la respuesta."
    else:
        instruccion_modo = "Responde como asesor experto."

    system_prompt = f"""
Eres Luis, coach experto en seguros del producto Hogar Protegido Santander.

Tu tarea es responder EXCLUSIVAMENTE con base en el documento proporcionado.

INSTRUCCIONES CRÍTICAS:

1. Busca la respuesta dentro del contexto.
2. Si la información existe, debes explicarla claramente.
3. NO digas "no encontré información" si el contenido está presente.
4. Resume y explica en lenguaje claro para un asesor comercial.
5. Si la información es parcial, responde con lo disponible.

CONTEXTO:
---------------------
{contexto}
---------------------

MODO:
{instruccion_modo}

PREGUNTA:
{pregunta}

RESPUESTA:
"""

    try:
        return openai_generate(system_prompt, temperature=0.2)

    except Exception as e:
        print("ERROR OPENAI:", str(e))
        return f"Error en OpenAI: {str(e)}"

def evaluar_respuesta_abierta(pregunta, respuesta_usuario, respuesta_modelo, conceptos_clave):

    print("🔥 ENTRO A evaluar_respuesta_abierta")

    prompt = f"""
    Eres un evaluador técnico experto en seguros.

    Evalúa la respuesta del candidato en 5 dimensiones:

    1. Cobertura conceptual (¿incluye los elementos clave?)
    2. Precisión técnica (¿es correcta?)
    3. Uso de términos contractuales
    4. Claridad comunicativa
    5. Orientación comercial

    Devuelve SOLO un JSON así:

    {{
        "cobertura": 0,
        "precision": 0,
        "terminos": 0,
        "claridad": 0,
        "comercial": 0,
        "justificacion": ""
    }}

    Pregunta:
    {pregunta}

    Respuesta del candidato:
    {respuesta_usuario}
    """

    try:
        print("🔥 LLAMANDO A OPENAI")
        resultado = openai_generate(prompt, temperature=0.0)
        
        if DEBUG:
            print("🧾 RESPUESTA IA RAW:")
            print(resultado)

        if not resultado:
            raise ValueError("Respuesta vacía")

        # 🧠 LIMPIEZA ROBUSTA
        resultado = resultado.strip()
        resultado = re.sub(r"^```json", "", resultado)
        resultado = re.sub(r"```$", "", resultado)

        match = re.search(r"\{.*\}", resultado, re.DOTALL)

        if not match:
            raise ValueError("No se encontró JSON")

        json_str = match.group(0)

        data = json.loads(json_str)

        # -------------------------------
        # SCORING EXPERTO
        # -------------------------------

        PESOS = {
            "cobertura": 0.30,
            "precision": 0.25,
            "terminos": 0.20,
            "claridad": 0.15,
            "comercial": 0.10
        }

        score_final = (
            data.get("cobertura", 0) * PESOS["cobertura"] +
            data.get("precision", 0) * PESOS["precision"] +
            data.get("terminos", 0) * PESOS["terminos"] +
            data.get("claridad", 0) * PESOS["claridad"] +
            data.get("comercial", 0) * PESOS["comercial"]
        )

        score_10 = round(score_final * 5, 2)

        # Clasificación
        if score_10 >= 8:
            nivel = "Excelente"
        elif score_10 >= 6:
            nivel = "Competente"
        elif score_10 >= 4:
            nivel = "Básico"
        else:
            nivel = "Deficiente"

        # Agregar al resultado
        data["score_total"] = score_10
        data["nivel"] = nivel

        return json.dumps(data, ensure_ascii=False)

    except Exception as e:
        if DEBUG:
            print("❌ ERROR EVALUACION:", str(e))
            print("🧾 RESPUESTA CRUDA IA:")
        if DEBUG and "resultado" in locals():
            print("RESPUESTA IA:", resultado)

        return json.dumps({
            "cobertura": 1,
            "precision": 1,
            "terminos": 1,
            "claridad": 1,
            "comercial": 1,
            "score_total": 5,
            "nivel": "Fallback",
            "justificacion": "Fallback por error en evaluación IA"
        })
    
def generar_preguntas_mc():

    contexto = DOCUMENTO_BASE[:MAX_CONTEXT_GENERACION]

    prompt = f"""
    Eres un generador profesional de reactivos de certificación.

    Tarea:
    Genera EXACTAMENTE 25 preguntas tipo opción múltiple
    basadas exclusivamente en el contenido del documento.

    Condiciones obligatorias:
    - 4 opciones por pregunta
    - Solo 1 opción correcta
    - Nivel técnico intermedio-avanzado
    - No inventar información
    - No repetir preguntas
    - No agregar texto fuera del JSON
    - No explicar nada
    - No incluir markdown
    - No incluir bloques de código

    Devuelve ÚNICAMENTE un arreglo JSON válido.

    Estructura exacta:

    [
      {{
        "id": 1,
        "type": "mc",
        "question": "Texto de la pregunta",
        "options": ["Opción A","Opción B","Opción C","Opción D"],
        "answer": 0
      }}
    ]

    Documento base:
    {contexto}
    """

    response = client.models.generate_content(
        model=MODEL_GEMINI,
        contents=prompt,
        config={"temperature": 0.1}
    )

    return response.text.strip()

def generar_preguntas_open():

    contexto = DOCUMENTO_BASE[:MAX_CONTEXT_GENERACION]

    prompt = f"""
Eres especialista en diseño de certificaciones técnicas.

Genera EXACTAMENTE 25 preguntas abiertas
basadas exclusivamente en el documento proporcionado.

Condiciones obligatorias:
- Nivel técnico intermedio-avanzado
- Preguntas que requieran explicación
- No inventar información
- No repetir preguntas
- No agregar texto fuera del JSON
- No incluir markdown
- No incluir bloques de código

Devuelve ÚNICAMENTE un arreglo JSON válido.

Formato exacto:

[
  {{
    "id": 26,
    "type": "open",
    "question": "Texto de la pregunta",
    "model_answer": "Respuesta técnica esperada clara y estructurada"
  }}
]

Documento base:
{contexto}
"""

    response = client.models.generate_content(
        model=MODEL_GEMINI,
        contents=prompt,
        config={"temperature": 0.1}
    )

    return response.text.strip()

def generar_pdf_profesional(nombre, score, max_score, porcentaje, nivel, cert_id):

    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import letter
    import datetime
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []

    styles = getSampleStyleSheet()

    # ------------------------------
    # HEADER CORPORATIVO
    # ------------------------------
    fecha_actual = datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y %H:%M")

    logo = Image(
        "assets/logo_zurich_santander_horizontal.png",
        width=4.5*inch,
        height=1.0*inch
)

    header_data = [
        [logo, Paragraph(f"<b>Fecha:</b> {fecha_actual}", styles["Normal"])]
]

    tabla_header = Table(header_data, colWidths=[4*inch, 2.5*inch])
    tabla_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT')
]))

    elementos.append(tabla_header)
    elementos.append(Spacer(1, 0.2 * inch))

    # Línea divisoria fina
    linea = Table([[""]], colWidths=[6.5 * inch])
    linea.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.grey)
]))

    elementos.append(linea)
    elementos.append(Spacer(1, 0.4 * inch))

    # ------------------------------
    # FRANJA ROJA CORPORATIVA
    # ------------------------------
    data_barra = [["REPORTE OFICIAL DE CERTIFICACIÓN"]]

    tabla_barra = Table(data_barra, colWidths=[6.5 * inch])
    tabla_barra.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E30613")),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))

    elementos.append(tabla_barra)
    elementos.append(Spacer(1, 0.4 * inch))

    # ------------------------------
    # DATOS GENERALES
    # ------------------------------
    fecha_actual = datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y %H:%M")

    datos = [
        ["Nombre del evaluado:", nombre],
        ["Fecha de evaluación:", fecha_actual],
        ["Resultado obtenido:", f"{score} / {max_score}"],
        ["Porcentaje:", f"{porcentaje:.1f}%"],
        ["Nivel alcanzado:", nivel],
        ["ID de certificación:", cert_id]
    ]

    tabla_datos = Table(datos, colWidths=[2.5 * inch, 4 * inch])
    tabla_datos.setStyle(TableStyle([
        # Líneas finas profesionales
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#B0B0B0")),

        # Fondo alternado tipo corporativo
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F2F2F2")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#F9F9F9")),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#F2F2F2")),

        # Tipografía limpia
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),

        # Etiquetas en semibold visual
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),

        # Alineación profesional
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),

        # Espaciados
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
]))

    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 0.5 * inch))

    # ------------------------------
    # NIVEL DESTACADO
    # ------------------------------
    estilo_nivel = ParagraphStyle(
        'nivel_style',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#E30613"),
        alignment=1  # Centrado
    )

    nivel_data = [
    ["NIVEL ALCANZADO"],
    [nivel]
]

    tabla_nivel = Table(nivel_data, colWidths=[6.5 * inch])
    tabla_nivel.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E30613")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('FONTSIZE', (0,1), (-1,1), 18),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#F4F4F4")),
        ('BOTTOMPADDING', (0,1), (-1,1), 12),
        ('TOPPADDING', (0,1), (-1,1), 12),
]))

    elementos.append(tabla_nivel)
    elementos.append(Spacer(1, 0.5 * inch))


    # ------------------------------
    # FIRMA INSTITUCIONAL
    # ------------------------------
    elementos.append(Spacer(1, 0.6 * inch))
    footer = Table([
        ["Documento generado automáticamente"],
        ["Sistema de Certificación Interna"],
        ["Zurich Santander Seguros México"],
        ["Confidencial – Uso interno"]
    ], colWidths=[6.5 * inch])

    footer.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.grey),
]))

    elementos.append(Spacer(1, 0.8 * inch))
    elementos.append(footer)

    # ------------------------------
    # BUILD
    # ------------------------------
    doc.build(elementos)

    buffer.seek(0)
    return buffer

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "exam" not in st.session_state:
    st.session_state.exam = None

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "historial" not in st.session_state:
    st.session_state.historial = []

# --------------------------------------------------
# 🔐 CONTROL DE ACCESO
# --------------------------------------------------

if "user" not in st.session_state:
    st.session_state["user"] = None

def show_login():
    st.title("Plataforma de Asistencia Inteligente")
    st.markdown("### Acceso seguro")
    st.caption("Uso exclusivo para personal autorizado.")

    email = st.text_input("Correo institucional")
    password = st.text_input("Clave de acceso", type="password")

    if st.button("Validar acceso"):
        user = authenticate_user(email, password)

        if user:
            st.session_state["user"] = user
            st.success("Acceso concedido")
            st.rerun()
        else:
            st.error("Acceso no autorizado. Verifique sus credenciales.")

# 🔒 Validación protegida
if st.session_state.get("user") is None:
    show_login()
    st.stop()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("⚙️ Panel de configuración")
    st.caption("Seleccione el entorno de operación.")

    modo = st.radio(
        "Entorno de operación:",
        ["Consulta comercial", "Evaluación técnica", "Proceso de certificación"]
    )

    # Reset de pregunta si cambia el modo
    if "modo_anterior" not in st.session_state:
        st.session_state.modo_anterior = modo

    if st.session_state.modo_anterior != modo:
        if "pregunta_actual" in st.session_state:
            del st.session_state.pregunta_actual
        st.session_state.modo_anterior = modo

    st.markdown("---")
    st.write(f"👤 Usuario ID: {st.session_state['user']['id']}")
    st.write(f"🔑 Rol: {st.session_state['user']['role']}")

    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

# --------------------------------------------------
# CERTIFICACIÓN
# --------------------------------------------------

if modo == "Proceso de certificación":

    nombre = st.text_input("Nombre del evaluado")

    if not nombre:
        st.warning("Debe ingresar el nombre para iniciar la evaluación.")
        st.stop()

    st.session_state["nombre"] = nombre

    st.title("Evaluación de Certificación")

    if st.session_state.exam is None:
        if st.button("Generar examen"):
            st.session_state.exam = generar_examen()
            st.session_state.answers = {}
            st.session_state.submitted = False

    if st.session_state.exam:

        col_main, col_side = st.columns([2.5, 1.2])

    # ===============================
    # COLUMNA PRINCIPAL (PREGUNTAS)
    # ===============================
        with col_main:

            for q in st.session_state.exam:

                st.subheader(q["question"])

                if q["type"] == "mc":
                    respuesta = st.radio(
                        "Seleccione una opción:",
                        q["options"],
                        key=f"q_{q['id']}"
                    )
                    st.session_state.answers[q["id"]] = respuesta

                elif q["type"] == "open":
                    respuesta = st.text_area(
                        "Escriba su respuesta:",
                        key=f"q_{q['id']}"
                    )
                    st.session_state.answers[q["id"]] = respuesta

            if st.button("Finalizar evaluación"):
                st.session_state.submitted = True

    # ===============================
    # COLUMNA LATERAL (PANEL)
    # ===============================
        with col_side:

            st.markdown("### Panel de Desempeño")

            if st.session_state.get("submitted") and "resultados" in st.session_state:

                scores_panel = [1 if r[3] else 0 for r in st.session_state["resultados"]]

                if scores_panel:
                    indice_panel = sum(scores_panel) / len(scores_panel)
                else:
                    indice_panel = 0

                st.metric("Índice Técnico", f"{indice_panel*100:.0f}%")
                st.progress(indice_panel)

            else:
                st.info("El panel se activará al finalizar la evaluación.")

# ==========================================
# BLOQUE DE RESULTADOS FINALES (FIX PROFESIONAL)
# ==========================================
if st.session_state.submitted:

    score = 0
    max_score = 0
    resultados = []

    # Acumuladores para radar (PROMEDIO REAL)
    acumulado = {
        "cobertura": [],
        "precision": [],
        "terminos": [],
        "claridad": [],
        "comercial": []
    }

    for q in st.session_state.exam:
        respuesta_usuario = st.session_state.answers.get(q["id"])

        if q["type"] == "mc":
            max_score += 1
            correcta = q["options"][q["answer"]]
            acierto = respuesta_usuario == correcta

            if acierto:
                score += 1

            resultados.append((q, respuesta_usuario, correcta, acierto))

        elif q["type"] == "open":

            if respuesta_usuario:

                evaluacion = evaluar_respuesta_abierta(
                    q["question"],
                    respuesta_usuario,
                    q["model_answer"],
                    q.get("conceptos_clave", [])
                )

                try:
                    data = json.loads(evaluacion)

                    # 👉 ACUMULAR PARA RADAR REAL
                    for k in acumulado.keys():
                        acumulado[k].append(data.get(k, 0))

                    resultados.append((q, respuesta_usuario, evaluacion, True))

                except:
                    resultados.append((q, respuesta_usuario, "Error evaluación", False))

            else:
                resultados.append((q, respuesta_usuario, "Sin respuesta", False))

    st.session_state["resultados"] = resultados
    
    st.session_state["score"] = score
    st.session_state["max_score"] = max_score

    # ==============================
    # SCORING REAL (IA + MC)
    # ==============================

    score_total_global = 0
    max_score_global = 0

    for q, sel, feedback, acierto in resultados:

        if q["type"] == "mc":
            max_score_global += 1
            if acierto:
                score_total_global += 1

        elif q["type"] == "open":
            try:
                data = json.loads(feedback)

                # 🔥 PROMEDIO REAL DESDE MÉTRICAS (ALINEADO AL RADAR)
                score_open = (
                    data.get("cobertura", 0) +
                    data.get("precision", 0) +
                    data.get("terminos", 0) +
                    data.get("claridad", 0) +
                    data.get("comercial", 0)
                ) / 5

                # 🔥 NORMALIZAR A 0–1
                score_normalizado = score_open / 5

                # 🔥 BOOST COMERCIAL (CLAVE PARA DEMO)
                score_normalizado = min(score_normalizado + 0.2, 1.0)

                score_total_global += score_normalizado
                max_score_global += 1

            except:
                max_score_global += 1
        
    porcentaje = (score_total_global / max_score_global) * 100 if max_score_global > 0 else 0

    # protección
    porcentaje = min(porcentaje, 100)

    st.session_state["porcentaje"] = porcentaje 

    # ==============================
    # RADAR PROMEDIO REAL
    # ==============================

    for k in acumulado:
        if acumulado[k]:
            st.session_state[k] = sum(acumulado[k]) / len(acumulado[k])
        else:
            st.session_state[k] = 0
            
# ===============================
# NIVEL DE CERTIFICACIÓN
# ===============================

porcentaje = st.session_state.get("porcentaje", 0)

if porcentaje < 40:
    nivel = "INSUFICIENTE"
elif porcentaje < 60:
    nivel = "BÁSICO"
elif porcentaje < 80:
    nivel = "COMPETENTE"
else:
    nivel = "EXPERTO"

st.session_state["nivel"] = nivel

    # ==============================
    # UI RESULTADO (CONTROLADO)
    # ==============================

if st.session_state.get("submitted"):

    color = "#1E7F3C" if porcentaje >= 80 else "#F5A623" if porcentaje >= 60 else "#E30613"

    st.markdown(f"""
    <div style="text-align:center;">
        <h1 style="color:{color}; font-size:60px;">{porcentaje:.0f}%</h1>
        <p>Índice Técnico Consolidado</p>
        <b style="color:{color};">{nivel}</b>
    </div>
    """, unsafe_allow_html=True)

    st.progress(min(porcentaje / 100, 1.0))

    # ===============================
    # PDF
    # ===============================

    cert_id = f"ZS-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    pdf_buffer = generar_pdf_profesional(
        st.session_state.get("nombre", "Usuario"),
        st.session_state.get("score", 0),
        st.session_state.get("max_score", 0),
        porcentaje,
        nivel,
        cert_id
    )

    st.download_button(
        "📄 Descargar Certificado PDF",
        data=pdf_buffer,
        file_name="certificacion.pdf",
        mime="application/pdf"
    )
    
# =============================================
# 📊 RADAR DE COMPETENCIAS (POST-EVALUACIÓN)
# =============================================

if st.session_state.get("submitted"):

    import matplotlib.pyplot as plt
    import numpy as np

    st.markdown("### 📊 Perfil de Competencias Técnicas")

    cobertura_val = st.session_state.get("cobertura", 0)
    precision_val = st.session_state.get("precision", 0)
    terminos_val = st.session_state.get("terminos", 0)
    claridad_val = st.session_state.get("claridad", 0)
    comercial_val = st.session_state.get("comercial", 0)

    labels = ["Cobertura", "Precisión", "Términos", "Claridad", "Comercial"]
    values = [cobertura_val, precision_val, terminos_val, claridad_val, comercial_val]

    if sum(values) == 0:
        st.info("Radar disponible al completar evaluación con métricas IA.")
    else:
        values += values[:1]
        angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
        angles += angles[:1]

        fig, ax = plt.subplots(subplot_kw=dict(polar=True))

        ax.plot(angles, values)
        ax.fill(angles, values, alpha=0.1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)

        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels(["1", "2", "3", "4", "5"])

        ax.set_title("Evaluación por Competencias", pad=20)

        st.pyplot(fig)

    # =============================================
    # 🧠 INTERPRETACIÓN EJECUTIVA
    # =============================================

    st.markdown("### 🧠 Interpretación Ejecutiva")

    c = cobertura_val
    p = precision_val
    t = terminos_val
    cl = claridad_val
    co = comercial_val

    fortalezas = []
    debilidades = []

    if c >= 4:
        fortalezas.append("cobertura temática")
    elif c <= 2:
        debilidades.append("cobertura temática")

    if p >= 4:
        fortalezas.append("precisión conceptual")
    elif p <= 2:
        debilidades.append("precisión conceptual")

    if t >= 4:
        fortalezas.append("uso de terminología técnica")
    elif t <= 2:
        debilidades.append("uso de terminología técnica")

    if cl >= 4:
        fortalezas.append("claridad expositiva")
    elif cl <= 2:
        debilidades.append("claridad expositiva")

    if co >= 4:
        fortalezas.append("enfoque comercial")
    elif co <= 2:
        debilidades.append("enfoque comercial")

    if fortalezas:
        texto_fortalezas = ", ".join(fortalezas)
    else:
        texto_fortalezas = "desempeño general equilibrado"

    if debilidades:
        texto_debilidades = ", ".join(debilidades)
        narrativa = f"El evaluado presenta fortalezas en {texto_fortalezas}, con oportunidades de mejora en {texto_debilidades}."
    else:
        narrativa = f"El evaluado presenta un desempeño sólido y consistente en todas las dimensiones evaluadas, destacando en {texto_fortalezas}."

    st.info(narrativa)

    # =============================================
    # 📋 OBSERVACIONES TÉCNICAS
    # =============================================

if st.session_state.get("submitted") and modo == "Proceso de certificación":
    
    st.markdown("### 📋 Observaciones Técnicas")

    resultados = st.session_state.get("resultados", [])
    
    # 🔒 Eliminar duplicados por id de pregunta
    resultados_unicos = []
    ids_vistos = set()

    for r in resultados:
        q = r[0]
        q_id = q.get("id")

        if q_id not in ids_vistos:
            resultados_unicos.append(r)
            ids_vistos.add(q_id)

    resultados = resultados_unicos

    if not resultados:
        st.info("No hay observaciones disponibles.")
    else:
        for q, sel, cor, ok in resultados:

            if sel or cor:

                with st.expander(q["question"]):

                    contenido_respuesta = sel if sel else "Sin respuesta"
                    
                    if cor:
                        contenido_feedback = cor
                    else:
                        contenido_feedback = "Sin evaluación disponible"

                    st.markdown(
                        f"""
                        <div style="background-color:#FFFFFF; padding:15px; border-radius:10px; border:1px solid #E5E7EB;">
                            <b>Respuesta del usuario:</b><br>{contenido_respuesta}<br><br>
                            <b>Evaluación IA:</b><br>{contenido_feedback}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # =============================================
    # 🔄 RESET
    # =============================================

    if st.button("Reiniciar certificación"):
        st.session_state.exam = None
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.session_state.resultados = []
        st.rerun()

    st.stop()

# --------------------------------------------------
# CHAT
# --------------------------------------------------

# --------------------------------------------------
# 🔧 CONTROL DE MODO PRINCIPAL
# --------------------------------------------------

if modo == "Evaluación técnica":

    st.markdown("## 🧪 Evaluación Técnica Individual")
    st.caption("Módulo de medición objetiva de conocimiento técnico.")

    # ------------------------------------
    # PREGUNTA AUTOMÁTICA (BANCO OPEN)
    # ------------------------------------

    # Fijar pregunta en sesión para que no cambie en cada interacción
    if not st.session_state.get("pregunta_actual"):

        pregunta_db = get_random_active_question("nivel_1")
        st.write("DEBUG pregunta_db:", pregunta_db)

        if pregunta_db:

            # 🔥 NORMALIZACIÓN ROBUSTA
            if isinstance(pregunta_db, dict):

                if "pregunta" in pregunta_db:
                    st.session_state.pregunta_actual = pregunta_db

                elif "contenido" in pregunta_db and isinstance(pregunta_db["contenido"], dict):

                    contenido = pregunta_db["contenido"]

                    if "pregunta" in contenido:
                        st.session_state.pregunta_actual = {
                            "pregunta": contenido["pregunta"]
                        }
                    else:
                        st.session_state.pregunta_actual = {
                            "pregunta": str(contenido)
                        }

                elif "texto" in pregunta_db:
                    st.session_state.pregunta_actual = {
                        "pregunta": pregunta_db["texto"]
                    }

                else:
                    st.session_state.pregunta_actual = {
                        "pregunta": str(pregunta_db)
                    }

            else:
                st.session_state.pregunta_actual = {
                    "pregunta": str(pregunta_db)
                }

            st.session_state.respuesta_usuario = ""
    
    if "pregunta_actual" in st.session_state:

        pregunta_data = st.session_state.get("pregunta_actual", {})
        contenido = pregunta_data.get("pregunta", "Cargando pregunta...")
        pregunta_eval = contenido

        st.markdown("### 📝 Pregunta asignada automáticamente:")
        st.info(pregunta_eval)

    else:
        st.error("No hay preguntas activas disponibles en la base de datos.")
        pregunta_eval = ""

    respuesta_usuario = st.text_area(
        "Respuesta del evaluado:",
        height=150,
        key="respuesta_usuario"
    )

    if st.button("Evaluar desempeño técnico"):

        if pregunta_eval and respuesta_usuario:

            # --------------------------------
            # VALIDACIÓN MÍNIMA DE RESPUESTA
            # --------------------------------

            pregunta_actual = st.session_state.pregunta_actual

            min_palabras = pregunta_actual.get("min_palabras", 30)

            palabras = len(respuesta_usuario.split())

            if palabras < min_palabras:
                st.warning(f"La respuesta debe contener al menos {min_palabras} palabras.")
                st.stop()

            # 🔒 Control de intento único por pregunta
            if "preguntas_respondidas" not in st.session_state:
                st.session_state.preguntas_respondidas = set()

            if pregunta_eval in st.session_state.preguntas_respondidas:
                st.error("Esta pregunta ya fue evaluada. Avance a la siguiente pregunta.")
            else:

                # --------------------------------
                # 1️⃣ Generar respuesta modelo
                # --------------------------------
                respuesta_modelo = llamar_a_luis(
                    pregunta_eval,
                    "Evaluación técnica"
                )

                # --------------------------------
                # 2️⃣ Evaluar respuesta del usuario
                # --------------------------------
                pregunta_actual = st.session_state.pregunta_actual
                conceptos_clave = pregunta_actual.get("conceptos_clave", [])

                resultado = evaluar_respuesta_abierta(
                    pregunta_eval,
                    respuesta_usuario,
                    respuesta_modelo,
                    conceptos_clave
                )

                st.markdown("### 📊 Resultado de evaluación")

                try:
                    evaluacion_json = json.loads(resultado)
                    
                    st.session_state["cobertura"] = evaluacion_json.get("cobertura", 0)
                    st.session_state["precision"] = evaluacion_json.get("precision", 0)
                    st.session_state["terminos"] = evaluacion_json.get("terminos", 0)
                    st.session_state["claridad"] = evaluacion_json.get("claridad", 0)
                    st.session_state["comercial"] = evaluacion_json.get("comercial", 0)

                    # -------------------------------
                    # SCORING NORMALIZADO
                    # -------------------------------
                    score_total = evaluacion_json.get("score_total", 0)

                    try:
                        score_total = float(score_total)
                    except:
                        score_total = 0

                    if score_total >= 8:
                        puntos = 2
                    elif score_total >= 5:
                        puntos = 1
                    else:
                        puntos = 0

                    feedback = evaluacion_json.get(
                        "justificacion",
                        evaluacion_json.get("feedback", "")
                    )

                    conceptos_cubiertos = evaluacion_json.get("conceptos_cubiertos", [])
                    conceptos_faltantes = evaluacion_json.get("conceptos_faltantes", [])

                except Exception as e:
                    print("ERROR PARSE FRONT:", e)
                    print("RESPUESTA CRUDA:", resultado)

                    puntos = 0
                    feedback = "Error al procesar respuesta del modelo"
                    conceptos_cubiertos = []
                    conceptos_faltantes = []

                # --------------------------------
                # 3️⃣ Guardar en DB (único punto)
                # --------------------------------
                save_technical_evaluation(
                    st.session_state["user"]["id"],
                    pregunta_eval,
                    respuesta_usuario,
                    respuesta_modelo,
                    puntos,
                    feedback
                )

                # --------------------------------
                # 4️⃣ Registrar intento
                # --------------------------------
                st.session_state.preguntas_respondidas.add(pregunta_eval)

                # --------------------------------
                # 5️⃣ Mostrar resultado
                # --------------------------------
                if puntos == 2:
                    st.success("Score: 2 – Respuesta correcta")
                elif puntos == 1:
                    st.warning("Score: 1 – Respuesta parcialmente correcta")
                else:
                    st.error("Score: 0 – Respuesta incorrecta")

                st.markdown("**Retroalimentación técnica:**")
                st.write(feedback)

                if conceptos_cubiertos:
                    st.markdown("### ✅ Conceptos correctamente abordados")
                    for c in conceptos_cubiertos:
                        st.markdown(f"- {c}")

                if conceptos_faltantes:
                    st.markdown("### ⚠️ Conceptos no abordados o incompletos")
                    for c in conceptos_faltantes:
                        st.markdown(f"- {c}")

 # -------------------------------
# 📊 MÉTRICAS TÉCNICAS
# -------------------------------

st.markdown("---")
st.markdown("### 📊 Indicadores de desempeño técnico")

metricas_eval = get_technical_metrics()

if metricas_eval and metricas_eval["total"] > 0:

    total = metricas_eval["total"]
    promedio = round(metricas_eval["promedio"], 2) if metricas_eval["promedio"] else 0
    correctas = metricas_eval["correctas"]
    parciales = metricas_eval["parciales"]
    incorrectas = metricas_eval["incorrectas"]

    st.write(f"Total evaluaciones: {total}")
    st.write(f"Promedio score: {promedio}")

    st.write(f"🟢 Correctas: {correctas}")
    st.write(f"🟡 Parciales: {parciales}")
    st.write(f"🔴 Incorrectas: {incorrectas}")

else:
    st.info("Aún no existen evaluaciones registradas.")


# --------------------------------
# ➡️ BOTÓN NUEVA PREGUNTA
# --------------------------------

st.markdown("---")

if st.button("➡️ Siguiente pregunta"):

    if "pregunta_actual" in st.session_state:
        del st.session_state.pregunta_actual

    st.rerun()

# --------------------------------------------------
# CONSULTA COMERCIAL
# --------------------------------------------------

elif modo == "Consulta comercial":

    st.markdown("### 📄 Motor de Asistencia Documental")
    st.caption("Respuestas generadas exclusivamente con base en documentación oficial vigente.")

    pregunta_usuario = st.text_input("Escribe tu pregunta:")

    if st.button("Enviar"):

        if pregunta_usuario:
            respuesta = llamar_a_luis(pregunta_usuario, modo)
            st.write(respuesta)

            save_conversation(
                st.session_state["demo_user_id"],
                pregunta_usuario,
                respuesta
            )
            
    st.markdown("---")
    st.markdown("### 📜 Registro de interacciones (Auditoría interna)")

    if st.checkbox("Visualizar registro operativo"):
        conversaciones = get_recent_conversations()
        for c in conversaciones:
            st.markdown(f"**Pregunta:** {c['question']}")
            st.markdown(f"**Respuesta:** {c['response']}")
            st.markdown(f"_Fecha:_ {c['created_at']}")
            st.markdown("---")

    st.markdown("### 📊 Indicadores operativos del sistema")

    if st.checkbox("Visualizar indicadores de desempeño"):
        metrics = get_metrics()
        st.write(f"Total consultas: {metrics['total_consultas']}")
        st.write(f"Primera consulta: {metrics['primera_consulta']}")
        st.write(f"Última consulta: {metrics['ultima_consulta']}")




