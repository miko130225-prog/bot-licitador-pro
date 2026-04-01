import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Configuración del Modelo (Versión 2026)
# Usamos el modelo 2.0 que es el vigente y gratuito en AI Studio
MODEL_NAME = 'gemini-2.0-flash' 

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"Error al configurar la API Key: {e}")

st.set_page_config(page_title="Licitador Pro Perú", page_icon="⚖️", layout="centered")

st.title("🤖 Analista de Licitaciones Pro")
st.markdown("---")

# Función optimizada para extraer texto de los PDF
def extraer_texto(archivos_subidos):
    texto_completo = ""
    for archivo in archivos_subidos:
        try:
            reader = PdfReader(archivo)
            for pagina in reader.pages:
                texto_completo += pagina.extract_text() + "\n"
        except Exception as e:
            st.error(f"No se pudo leer el archivo {archivo.name}: {e}")
    return texto_completo

# --- INTERFAZ DE CARGA ---
archivos = st.file_uploader("Sube las Bases de Requisitos (PDF)", type="pdf", accept_multiple_files=True)

if archivos:
    with st.spinner("Procesando documentos..."):
        contexto_bases = extraer_texto(archivos)
    
    st.success(f"Se han procesado {len(archivos)} archivo(s).")

    # BOTÓN 1: Identificación de Perfil (Lógica de decisión)
    if st.button("🔍 Identificar Perfil Legal (¿Natural o Jurídica?)"):
        prompt_perfil = (
            "Actúa como un experto en contrataciones del Estado Peruano. "
            "Lee las bases adjuntas y responde: "
            "1. ¿El postor puede ser Persona Natural o solo Persona Jurídica? "
            "2. ¿Qué documentos de identidad o registros (RNP, Vigencia de Poder) son obligatorios? "
            "3. ¿Existe algún beneficio para MYPEs en este proceso? "
            "Responde de forma clara y estructurada."
        )
        with st.spinner("Analizando requisitos legales..."):
            try:
                response = model.generate_content([prompt_perfil, contexto_bases])
                st.info("### Resultado del Análisis de Perfil")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error al consultar el modelo {MODEL_NAME}: {e}")

    # BOTÓN 2: Generar preguntas para Anexos
    if st.button("📝 Generar Preguntas para Documentos"):
        prompt_preguntas = (
            "Basado en los requisitos de estas bases, genera una lista de preguntas "
            "específicas que el usuario debe responder para completar el Anexo de Datos del Postor. "
            "Solo pide información que NO esté en los documentos (como nombre del apoderado, RUC, cuenta CCI, etc.)."
        )
        with st.spinner("Creando cuestionario..."):
            try:
                response = model.generate_content([prompt_preguntas, contexto_bases])
                st.warning("### Datos necesarios para tus documentos:")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")

else:
    st.info("Por favor, sube uno o más archivos PDF para comenzar el análisis.")

st.markdown("---")
st.caption("Bot optimizado para el marco legal de Perú 2026 - Usando Gemini 2.0 Flash")
