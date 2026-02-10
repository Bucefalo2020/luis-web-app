import streamlit as st
import google.generativeai as genai
import os

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Coach Luis v2 - Zurich Santander", layout="wide")

def llamar_a_luis(prompt_usuario, modo_seleccionado, api_key_manual):
    # Buscamos la llave en Railway o Manual
    api_key_final = api_key_manual if api_key_manual else os.environ.get("GOOGLE_API_KEY")

    if not api_key_final:
        return "⚠️ Error: No se encontró la API Key. Por favor, revísala en Railway."
    
    try:
        # CONFIGURACIÓN CRÍTICA: Forzamos la versión 1 estable
        genai.configure(api_key=api_key_final)
        
        # Usamos el modelo con su nombre técnico completo para no dejar dudas
        model = genai.GenerativeModel(
            model_name='models/gemini-1.5-flash'
        )
        
        instruccion = (
            "Eres Luis, Coach experto de Zurich Santander México. "
            "Producto: Hogar Protegido 2020. Responde de forma amable y técnica."
        )
        
        # Llamada directa al modelo
        response = model.generate_content(f"{instruccion}\nModo: {modo_seleccionado}\nUsuario: {prompt_usuario}")
        return response.text
    except Exception as e:
        # Si el error 404 persiste, este mensaje nos dará más pistas
        return f"❌ Detalle del Error: {str(e)}"

# --- INTERFAZ ---
st.title("🛡️ Coach Luis")

with st.sidebar:
    st.title("⚙️ Configuración")
    key_input = st.text_input("Ingresa tu API Key (opcional)", type="password")
    modo = st.radio("Modo:", ["Taller", "Evaluador"])

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo, key_input)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
