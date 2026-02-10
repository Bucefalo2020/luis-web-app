import streamlit as st
import google.generativeai as genai
import os

# 1. Configuración de página
st.set_page_config(page_title="Coach Luis - Zurich Santander", layout="wide")

def llamar_a_luis(prompt_usuario, modo_seleccionado, api_key_manual):
    # BUSCAMOS LA LLAVE JUSTO ANTES DE HABLAR CON GOOGLE
    # Prioridad 1: Lo que escribas en la caja blanca
    # Prioridad 2: Lo que guardaste en Railway
    api_key_final = api_key_manual if api_key_manual else os.environ.get("GOOGLE_API_KEY")

    if not api_key_final:
        return "⚠️ Error: No detecto tu llave. Asegúrate de que en Railway se llame GOOGLE_API_KEY."
    
    try:
        genai.configure(api_key=api_key_final, transport='rest')
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        instruccion = (
            "Eres Luis, Coach experto de Zurich Santander México. "
            "Producto: Hogar Protegido 2020. Responde de forma amable y técnica."
        )
        
        response = model.generate_content(f"{instruccion}\nModo: {modo_seleccionado}\nUsuario: {prompt_usuario}")
        return response.text
    except Exception as e:
        return f"❌ Error de Conexión: {str(e)}"

# --- INTERFAZ ---
st.title("🛡️ Coach Luis")

with st.sidebar:
    st.title("⚙️ Configuración")
    # Capturamos la llave manual aquí
    key_input = st.text_input("Ingresa tu API Key (opcional si está en Railway)", type="password")
    modo = st.radio("Selecciona el Modo:", ["Taller", "Evaluador"])

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            # LE PASAMOS LA LLAVE MANUAL A LA FUNCIÓN
            respuesta = llamar_a_luis(prompt, modo, key_input)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
