import streamlit as st
import google.generativeai as genai
import os
from google.api_core import client_options

# =========================================================
# 1. Configuración general de la página
# =========================================================
st.set_page_config(
    page_title="Coach Luis - Zurich Santander",
    layout="wide"
)

# =========================================================
# 2. Obtención de la API Key desde el entorno
# =========================================================
api_key_env = os.environ.get("GEMINI_API_KEY")

if not api_key_env:
    st.error("GEMINI_API_KEY no está definida en el entorno")
    st.stop()

# =========================================================
# 3. Sidebar de configuración
# =========================================================
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

# API Key efectiva (prioridad a input manual)
api_key_final = api_key_input if api_key_input else api_key_env

# =========================================================
# 4. Inicialización del modelo Gemini (cacheado y versionado)
# =========================================================
@st.cache_resource
def get_gemini_model(api_key: str, model_version: str):
    options = client_options.ClientOptions(
        api_endpoint="generativelanguage.googleapis.com"
    )
    genai.configure(
        api_key=api_key,
        client_options=options
    )
    return genai.GenerativeModel(model_version)

# ⚠️ El segundo parámetro invalida caches antiguos
model = get_gemini_model(api_key_final, "gemini-pro")

# =========================================================
# 5. Función principal de inferencia (cache de datos)
# =========================================================
@st.cache_data(ttl=300)
def llamar_a_luis(prompt_usuario: str, modo_seleccionado: str):
    if modo_seleccionado == "Evaluador":
        prompt_final = (
            "Evalúa técnicamente lo siguiente, detectando errores, "
            "omisiones y áreas de mejora:\n\n"
            f"{prompt_usuario}"
        )
    else:
        prompt_final = prompt_usuario

    instruccion = (
        "Eres Luis, Coach experto de Zurich Santander México. "
        "Producto: Hogar Protegido 2020. "
        "Responde de forma clara, profesional y técnicamente precisa."
    )

    response = model.generate_content(
        f"{instruccion}\n\n{prompt_final}"
    )
    return response.text

# =========================================================
# 6. Interfaz de chat
# =========================================================
st.title("🛡️ Coach Luis")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "¡Hola! Soy Luis. "
                "¿En qué puedo ayudarte hoy con Hogar Protegido?"
            )
        }
    ]

# Mostrar historial de conversación
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
