import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# Configuración de la API desde los Secrets de Streamlit
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# Usamos Gemini 2.5 Flash por su eficiencia en bases legales
model = genai.GenerativeModel('gemini-1.5-flash') # Puedes probar 'gemini-1.5-flash' o el que tengas habilitado

st.set_page_config(page_title="Analista Licitaciones Perú", page_icon="⚖️")
st.title("🤖 Asistente de Licitaciones Pro")

def leer_pdf(file):
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    return texto

# --- INTERFAZ ---
archivos = st.file_uploader("Carga las bases (Juegos Bolivarianos, etc.)", type="pdf", accept_multiple_files=True)

if archivos:
    texto_total = ""
    for f in archivos:
        texto_total += leer_pdf(f)
    
    st.success("Documentos procesados.")

    # Botón 1: Análisis de Perfil
    if st.button("Identificar Perfil Legal"):
        prompt = (
            "Eres un experto en contrataciones del estado peruano. Analiza estas bases y "
            "determina si el postor debe ser Persona Natural o Jurídica. Enumera los "
            "documentos de identidad y registros (RNP, etc.) obligatorios según el pliego."
        )
        with st.spinner("Analizando requisitos..."):
            response = model.generate_content([prompt, texto_total])
            st.markdown(response.text)

    # Botón 2: Generar preguntas para Anexos
    if st.button("Generar Cuestionario para Anexos"):
        prompt = (
            "Basado en las bases, genera una lista de preguntas breves que el usuario debe "
            "responder para completar el Anexo 1 (Datos del Postor) y el Anexo de Experiencia. "
            "Solo pide los datos que no están en las bases (ej: Nombre del representante, RUC, etc)."
        )
        with st.spinner("Creando cuestionario..."):
            response = model.generate_content([prompt, texto_total])
            st.info("Responde a lo siguiente para generar tus documentos:")
            st.markdown(response.text)
