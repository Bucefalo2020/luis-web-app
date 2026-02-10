import streamlit as st
import google.generativeai as genai
import os

# 1. Configuración de la API Key (Puente Railway-Streamlit)
api_key_env = os.environ.get("GOOGLE_API_KEY")
api_key_input = st.sidebar.text_input("Ingresa tu API Key de Google", type="password")

# Prioridad: Si hay algo en la caja usa eso, si no, usa lo de Railway
api_key = api_key_input if api_key_input else api_key_env

def llamar_a_luis(prompt_usuario, modo_seleccionado):
    # Si no hay llave en ningún lado, avisar
    if not api_key:
        return "⚠️ Por favor, configura la GOOGLE_API_KEY en Railway o ingrésala en la barra lateral."
    
    try:
        # Configuración con transporte 'rest' para máxima compatibilidad
        genai.configure(api_key=api_key, transport='rest')
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        instruccion_base = (
            "Eres Luis, Coach experto de Zurich Santander México. "
            "Tu objetivo es ayudar con el producto Hogar Protegido 2020. "
            "Responde de forma profesional, amable y precisa."
        )
        
        contexto = f"{instruccion_base} Modo actual: {modo_seleccionado}."
        
        # Llamada al modelo
        response = model.generate_content(f"{contexto}\n\nUsuario: {prompt_usuario}")
        return response.text

    except Exception as e:
        return f"❌ Error de Conexión: {str(e)}"

# --- INTERFAZ DE STREAMLIT ---
st.title("🛡️ Coach Luis")
st.write("¡Hola! Soy Luis, tu Coach de Zurich Santander. ¿En qué te puedo ayudar hoy con Hogar Protegido?")

modo = st.sidebar.radio("Selecciona el Modo:", ["Taller", "Evaluador"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
