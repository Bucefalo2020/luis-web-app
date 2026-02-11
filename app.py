import streamlit as st
import google.generativeai as genai
import os
from google.api_core import client_options

# 1. Configuración de página
st.set_page_config(
    page_title="Coach Luis - Zurich Santander",
    layout="wide"
)

# 2. Obtención de la llave desde Railway
api_key_env = os.environ.get("GEMINI_API_KEY")

if not api_key_env:
    st.error("GEMINI_API_KEY no está definida en el entorno")
    st.stop()

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuración")
    api_key_input = st.text_input(
        "Ingresa tu API Key (opcional)",
        type="password"
    )
    modo = st.radio(
        "Selecciona el Modo:",
        ["Taller", "Evaluador"]
    )

# API key efectiva
api_key_final = api_key_input if api_key_input else api_key_env

# 3. Inicialización del modelo (recurso cacheado)
@st.cache_resource
def get_gemini_model(api_key: str):
    options = client_options.ClientOptions(
        api_endpoint="generativelanguage.googleapis.com"
    )
    genai.configure(api_key=api_key, client_options=options)
    return genai.GenerativeModel("gemini-pro")

model = get_gemini_model(api_key_final)

# 4. Llamada al modelo (datos cacheados)
@st.cache_data(ttl=300)
def llamar_a_luis(prompt_usuario: str, modo_seleccionado: str):
    instruccion = (
        "Eres Luis, Coach experto de Zurich Santander México. "
        "Producto: Hogar Protegido 2020. "
        "Responde de forma amable, clara y técnica."
    )

    if modo_seleccionado == "Evaluador":
        prompt = f"EVALÚA LO SIGUIENTE:\n{prompt_usuario}"
    else:
        prompt = prompt_usuario

    final_prompt = (
        f"{instruccion}\n"
        f"Modo: {modo_seleccionado}\n"
        f"Usuario: {prompt}"
    )

    response = model.generate_content(final_prompt)
    return response.text

# 5. Interfaz de chat
st.title("🛡️ Coach Luis")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy con Hogar Protegido?"
        }
    ]

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del usuario
if prompt := st.chat_input("Escribe tu duda técnica aquí..."):
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo)
            st.markdown(respuesta)
            st.session_state.messages.append(
                {"role": "assistant", "content": respuesta}
            )
