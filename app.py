import streamlit as st
import google.generativeai as genai
import os

# 1. Configuración de página
st.set_page_config(page_title="Coach Luis - Zurich Santander", layout="wide")

# 2. Obtención de la llave (Prioridad Railway, luego Manual)
api_key_env = os.environ.get("GOOGLE_API_KEY")
with st.sidebar:
    st.title("⚙️ Configuración")
    api_key_input = st.text_input("Ingresa tu API Key de Google (opcional si está en Railway)", type="password")
    modo = st.radio("Selecciona el Modo:", ["Taller", "Evaluador"])

# La llave que usaremos finalmente
api_key_final = api_key_input if api_key_input else api_key_env

def llamar_a_luis(prompt_usuario, modo_seleccionado):
    if not api_key_final:
        return "⚠️ Error: No se encontró la API Key. Por favor, revísala en Railway o la barra lateral."
    
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

# 3. Interfaz de Chat
st.title("🛡️ Coach Luis")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy con Hogar Protegido?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda técnica aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
