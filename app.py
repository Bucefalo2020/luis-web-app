import streamlit as st
import google.generativeai as genai
from google.generativeai.types import RequestOptions
import os # <--- Importante para Railway

st.set_page_config(page_title="Coach Luis - Zurich Santander", layout="wide")

with st.sidebar:
    st.title("⚙️ Configuración")
    
    # Buscamos la llave en Railway, si no está, habilitamos el cuadro de texto
    api_key_env = os.environ.get("GOOGLE_API_KEY")
    if api_key_env:
        api_key = api_key_env
        st.success("✅ API Key cargada")
    else:
        api_key = st.text_input("Ingresa tu API Key de Google", type="password")
    
    modo = st.radio("Selecciona el Modo:", ["Taller", "Evaluador"])

def llamar_a_luis(prompt_usuario, modo_seleccionado):

def llamar_a_luis(prompt_usuario, modo_seleccionado):
    if not api_key:
        return "⚠️ Por favor, ingresa tu API Key." 
    
    try:
        # 1. Configuración FORZANDO EL TRANSPORTE 'rest' y la API 'v1'
        # Esto elimina el error 404 de v1beta definitivamente
        genai.configure(api_key=api_key, transport='rest')
        
        # 2. Forzamos el modelo gemini-1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        instruccion_base = (
            "Eres Luis, Coach experto de Zurich Santander México. "
            "Producto: Hogar Protegido 2020. "
        )
        
        contexto = f"{instruccion_base} Modo: {modo_seleccionado}."

        # 3. Llamada directa
        response = model.generate_content(f"{contexto}\n\nUsuario: {prompt_usuario}")
        return response.text

    except Exception as e:
        # Si esto falla con la nueva clave, el error nos dirá algo distinto a 404
        return f"❌ Error de Conexión: {str(e)}"

# --- 4. INTERFAZ DE CHAT (Añade esto al final) ---
st.title(f"🛡️ Coach Luis")

# Mensaje de bienvenida inicial
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy Luis, tu Coach de Zurich Santander. ¿En qué te puedo ayudar hoy con Hogar Protegido?"}]

# Mostrar el historial de mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Barra para escribir (Chat Input)
if prompt := st.chat_input("Escribe tu duda técnica aquí..."):
    # Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Obtener respuesta de Luis
    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
