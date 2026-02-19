import streamlit as st
import os
import random
import json
import re
import datetime
from pypdf import PdfReader
from google import genai
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

# CONFIGURACIÓN GLOBAL DE LA APP
st.set_page_config(
    page_title="Plataforma de Asistencia Inteligente",
    layout="wide",
    page_icon="🏢"
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
"""
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL no está configurada")

    conn = psycopg2.connect(
        database_url,
        cursor_factory=RealDictCursor
    )
    return conn

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

def authenticate_user(email, password):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, password_hash, role
        FROM users
        WHERE email = %s;
    """, (email,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and user["password_hash"] == hash_password(password):
        return {
            "id": user["id"],
            "role": user["role"]
        }

    return None

if "demo_user_id" not in st.session_state:
    st.session_state["demo_user_id"] = ensure_demo_user()

def save_conversation(user_id, question, response):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO conversations (user_id, question, response)
        VALUES (%s, %s, %s);
    """, (user_id, question, response))

    conn.commit()
    cur.close()
    conn.close()

# --------------------------------------------------
# CONFIGURACIÓN API
# --------------------------------------------------

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("GEMINI_API_KEY no está definida en el entorno.")
    st.stop()

client = genai.Client(api_key=API_KEY)

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
# FUNCIONES IA
# --------------------------------------------------

def llamar_a_luis(pregunta, modo):

    contexto = DOCUMENTO_BASE[:15000]

    if modo == "Evaluación técnica":
        instruccion_modo = "Analiza técnicamente y evalúa la respuesta."
    else:
        instruccion_modo = "Responde como asesor experto."

    system_prompt = f"""
Eres Luis, coach experto del producto Hogar Protegido 2020.

Reglas:
- Usa solo información del documento.
- Si no está en el documento responde:
"No encontré esa información en las condiciones generales."

Documento:
{contexto}

Modo:
{instruccion_modo}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"{system_prompt}\n\nPregunta: {pregunta}",
        config={"temperature": 0.2}
    )

    return response.text


def evaluar_respuesta_abierta(pregunta, respuesta_usuario, respuesta_modelo):

    prompt = f"""
Eres evaluador técnico de certificaciones.

Pregunta:
{pregunta}

Respuesta modelo:
{respuesta_modelo}

Respuesta del usuario:
{respuesta_usuario}

Califica:
0 = Incorrecta
1 = Parcial
2 = Correcta

Devuelve únicamente JSON válido:

{{
  "score": 0-2,
  "feedback": "explicación técnica clara"
}}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"temperature": 0.0}
    )

    return response.text.strip()


def generar_preguntas_mc():

    contexto = DOCUMENTO_BASE[:15000]

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
        model="gemini-2.0-flash",
        contents=prompt,
        config={"temperature": 0.1}
    )

    return response.text.strip()

def generar_preguntas_open():

    contexto = DOCUMENTO_BASE[:15000]

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
        model="gemini-2.0-flash",
        contents=prompt,
        config={"temperature": 0.1}
    )

    return response.text.strip()

def generar_pdf_profesional(nombre, score, max_score, porcentaje, nivel):

    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
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
    fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

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
    fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    datos = [
        ["Nombre del evaluado:", nombre],
        ["Fecha de evaluación:", fecha_actual],
        ["Resultado obtenido:", f"{score} / {max_score}"],
        ["Porcentaje:", f"{porcentaje:.1f}%"],
        ["Nivel alcanzado:", nivel]
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

if not st.session_state["user"]:
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

    st.markdown("---")
    st.write(f"👤 Usuario ID: {st.session_state['user']['id']}")
    st.write(f"🔑 Rol: {st.session_state['user']['role']}")

    if st.button("Cerrar sesión"):
        st.session_state["user"] = None
        st.rerun()

# --------------------------------------------------
# CERTIFICACIÓN
# --------------------------------------------------

if modo == "Proceso de certificación":

    nombre = st.text_input("Nombre del evaluado")

    if not nombre:
        st.warning("Debe ingresar el nombre para iniciar la evaluación.")
        st.stop()

    st.title("Evaluación de Certificación")

    if st.session_state.exam is None:
        if st.button("Generar examen"):
            st.session_state.exam = generar_examen()
            st.session_state.answers = {}
            st.session_state.submitted = False

    if st.session_state.exam:

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

        if st.session_state.submitted:

            score = 0
            max_score = 0
            resultados = []

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

                    max_score += 2

                    if respuesta_usuario:

                        evaluacion = evaluar_respuesta_abierta(
                            q["question"],
                            respuesta_usuario,
                            q["model_answer"]
                        )

                        json_match = re.search(r'\{.*\}', evaluacion, re.DOTALL)

                        if json_match:
                            evaluacion_json = json.loads(json_match.group())
                            puntos = int(evaluacion_json.get("score", 0))
                            feedback = evaluacion_json.get("feedback", "Sin retroalimentación.")
                        else:
                            puntos = 0
                            feedback = evaluacion

                        score += puntos
                        acierto = puntos > 0

                        resultados.append((q, respuesta_usuario, feedback, acierto))

                    else:
                        resultados.append((q, respuesta_usuario, "Sin respuesta", False))

            porcentaje = (score / max_score) * 100

            if porcentaje < 40:
                nivel = "INSUFICIENTE"
            elif porcentaje < 60:
                nivel = "BÁSICO"
            elif porcentaje < 80:
                nivel = "COMPETENTE"
            else:
                nivel = "EXPERTO"

            import datetime

            st.session_state.historial.append({
                "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "nombre": nombre,
                "score": score,
                "max_score": max_score,
                "porcentaje": porcentaje,
                "nivel": nivel
            })

            st.success(f"Puntuación final: {score}/{max_score} ({porcentaje:.1f}%)")

            st.markdown(f"### Nivel de desempeño: **{nivel}**")

            if nivel == "INSUFICIENTE":
                st.error("No alcanza el nivel mínimo de competencia. Se recomienda reforzar conocimientos y repetir la evaluación.")
            elif nivel == "BÁSICO":
                st.warning("Nivel básico alcanzado. Se recomienda profundizar en las condiciones generales.")
            elif nivel == "COMPETENTE":
                st.info("Buen nivel de dominio técnico. Puede seguir avanzando en contenidos especializados.")
            else:
                st.success("Nivel experto alcanzado. Dominio sólido del producto y condiciones contractuales.")

            pdf_buffer = generar_pdf_profesional(
                nombre,
                score,
                max_score,
                porcentaje,
                nivel
)

            st.download_button(
                label="Descargar reporte PDF",
                data=pdf_buffer,
                file_name=f"Reporte_Certificacion_{nombre}.pdf",
                mime="application/pdf"
)

            st.subheader("Resultados detallados")

            for q, sel, cor, ok in resultados:
                icono = "Correcto" if ok else "Incorrecto"
                st.write(f"{icono} — {q['question']}")
                st.write(f"Tu respuesta: {sel}")
                st.write(f"Resultado: {cor}")
                st.divider()

            if st.button("Reiniciar certificación"):
                st.session_state.exam = None
                st.session_state.answers = {}
                st.session_state.submitted = False
                st.rerun()

    st.stop()

# --------------------------------------------------
# CHAT
# --------------------------------------------------

# --------------------------------------------------
# 🧪 EVALUACIÓN TÉCNICA
# --------------------------------------------------

if modo == "Evaluación técnica":

    st.markdown("## 🧪 Evaluación Técnica Individual")
    st.caption("Módulo de medición objetiva de conocimiento técnico.")

    pregunta_eval = st.text_input("Ingrese la pregunta técnica a evaluar:")

    respuesta_usuario = st.text_area(
        "Respuesta del evaluado:",
        height=150
    )

    if st.button("Evaluar desempeño técnico"):

        if pregunta_eval and respuesta_usuario:

            # 1️⃣ Generar respuesta modelo
            respuesta_modelo = llamar_a_luis(
                pregunta_eval,
                "Evaluación técnica"
            )

            # 2️⃣ Evaluar respuesta del usuario
            resultado = evaluar_respuesta_abierta(
                pregunta_eval,
                respuesta_usuario,
                respuesta_modelo
            )

            st.markdown("### 📊 Resultado de evaluación")

            try:
                import re
                import json

                json_match = re.search(r"\{.*\}", resultado, re.DOTALL)

                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No se encontró JSON válido")

                score = data.get("score")
                feedback = data.get("feedback")

                if score == 2:
                    st.success(f"Score: {score} – Respuesta correcta")
                elif score == 1:
                    st.warning(f"Score: {score} – Respuesta parcialmente correcta")
                else:
                    st.error(f"Score: {score} – Respuesta incorrecta")

                st.markdown("**Retroalimentación técnica:**")
                st.write(feedback)

            except Exception as e:
                st.error("No se pudo interpretar el resultado de evaluación.")
                st.write("Detalle técnico:", e)

if modo == "Consulta comercial":

    st.markdown("### Motor de Asistencia Documental")
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

def get_recent_conversations(limit=10):
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

