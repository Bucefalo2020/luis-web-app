import streamlit as st
import os
from pypdf import PdfReader
from google import genai

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------

st.set_page_config(
    page_title="Coach Luis - Zurich Santander",
    layout="wide"
)

# --------------------------------------------------
# API KEY
# --------------------------------------------------

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("GEMINI_API_KEY no está definida en el entorno")
    st.stop()

client = genai.Client(api_key=api_key)

# --------------------------------------------------
# CARGA DEL DOCUMENTO BASE (PDF)
# --------------------------------------------------

@st.cache_resource
def cargar_documento():
    ruta = "docs/ZuytULVsGrYSvmro_HogarProtegidoSantander_CondicionesGenerales.pdf"
    reader = PdfReader(ruta)

    texto = ""
    for page in reader.pages:
        contenido = page.extract_text()
        if contenido:
            texto += contenido + "\n"

    return texto

DOCUMENTO_BASE = cargar_documento()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("⚙️ Configuración")
    modo = st.radio("Modo de respuesta:", ["Asesor", "Evaluador"])

# --------------------------------------------------
# FUNCIÓN PRINCIPAL IA
# --------------------------------------------------

@st.cache_data(ttl=300)
def llamar_a_luis(pregunta, modo):

    contexto = DOCUMENTO_BASE[:12000]

    if modo == "Evaluador":
        instruccion_modo = "Analiza técnicamente y evalúa la respuesta."
    else:
        instruccion_modo = "Responde como asesor experto."

    system_prompt = f"""
Eres Luis, coach experto del producto Hogar Protegido 2020 de Zurich Santander México.

Reglas estrictas:
- Responde SOLO usando información contenida en el documento
- Si no está en el documento responde exactamente:
"No encontré esa información en las condiciones generales."
- Cuando cites cláusulas hazlo textual

Documento:
{contexto}

Modo:
{instruccion_modo}
"""

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=f"{system_prompt}\n\nPregunta del usuario: {pregunta}",
        config={"temperature": 0.2}
    )

    return response.text

# --------------------------------------------------
# INTERFAZ CHAT
# --------------------------------------------------

st.title("🛡️ Coach Luis")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy con Hogar Protegido?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu pregunta técnica..."):

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando documento oficial..."):

            respuesta = llamar_a_luis(prompt, modo)

            st.markdown(respuesta)

            st.session_state.messages.append(
                {"role": "assistant", "content": respuesta}
            )
