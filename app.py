import streamlit as st
import os
from google import genai

# ======================================================
# Configuración página
# ======================================================
st.set_page_config(
    page_title="Coach Luis - Zurich Santander",
    layout="wide"
)

# ======================================================
# API KEY
# ======================================================
api_key_env = os.environ.get("GEMINI_API_KEY")

if not api_key_env:
    st.error("GEMINI_API_KEY no está definida en el entorno")
    st.stop()

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuración")
    api_key_input = st.text_input("API Key manual (opcional)", type="password")
    modo = st.radio("Modo:", ["Taller", "Evaluador"])

api_key_final = api_key_input if api_key_input else api_key_env

# ======================================================
# Cliente Gemini moderno
# ======================================================
@st.cache_resource
def get_client(api_key):
    return genai.Client(api_key=api_key)

client = get_client(api_key_final)

# ======================================================
# Motor de respuesta
# ======================================================
@st.cache_data(ttl=300)
def llamar_a_luis(prompt_usuario, modo_sel):

    if modo_sel == "Evaluador":
        prompt_usuario = (
            "Evalúa técnicamente lo siguiente:\n\n"
            + prompt_usuario
        )

    system_prompt = (
        "Eres Luis, Coach experto de Zurich Santander México. "
        "Producto: Hogar Protegido 2020. "
        "Responde de forma clara, profesional y técnica."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"{system_prompt}\n\n{prompt_usuario}"
    )

    return response.text

# ======================================================
# Interfaz
# ======================================================
st.title("🛡️ Coach Luis")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy con Hogar Protegido?"}
    ]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Escribe tu duda técnica..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consultando manuales..."):
            respuesta = llamar_a_luis(prompt, modo)
            st.markdown(respuesta)

    st.session_state.messages.append(
        {"role": "assistant", "content": respuesta}
    )
