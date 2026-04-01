import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# --- CONFIGURACIÓN DEL MOTOR DE IA ---
# Usamos gemini-2.5-flash-lite por su alta cuota para procesar PDFs extensos
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")

# --- CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Licitador Pro - Análisis de Bases", page_icon="⚖️", layout="wide")

# Estilo profesional y limpio
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stButton>button { 
        width: 100%;
        background-color: #004A99; 
        color: white; 
        border-radius: 5px;
    }
    .stButton>button:hover { background-color: #003366; color: white; }
    h1 { color: #1A1A1A; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Analista Experto en Licitaciones Públicas")
st.subheader("Procesamiento de Bases de Requisitos - Estado Peruano")
st.markdown("---")

# --- LÓGICA DE EXTRACCIÓN ---
def extraer_contenido_pdf(archivos):
    texto_total = ""
    for archivo in archivos:
        try:
            lector = PdfReader(archivo)
            for pagina in lector.pages:
                texto_total += pagina.extract_text() + "\n"
        except Exception as e:
            st.error(f"Error al leer el archivo {archivo.name}: {e}")
    return texto_total

# --- ESTRUCTURA DE LA APLICACIÓN ---
col_archivo, col_resultados = st.columns([1, 2])

with col_archivo:
    st.header("📂 Documentación")
    archivos_subidos = st.file_uploader("Cargar Bases Administrativas (PDF)", type="pdf", accept_multiple_files=True)
    
    if archivos_subidos:
        with st.spinner("Extrayendo texto técnico..."):
            contexto_legal = extraer_contenido_pdf(archivos_subidos)
        st.success(f"Análisis listo: {len(archivos_subidos)} documento(s) cargado(s).")

with col_resultados:
    st.header("📝 Análisis de Cumplimiento")
    
    if archivos_subidos:
        # BOTÓN 1: Identificación de Perfil Legal
        if st.button("🔍 Determinar Perfil Legal (Persona Natural/Jurídica)"):
            prompt_perfil = (
                "Actúa como un experto en contrataciones del Estado Peruano. "
                "Analiza exhaustivamente las bases adjuntas y responde con precisión técnica: "
                "1. ¿El postor puede participar como Persona Natural o es exclusivo para Persona Jurídica? "
                "2. Enumera los requisitos de capacidad legal (RNP, Vigencia de Poder, DNI). "
                "3. Indica si existen impedimentos o restricciones específicas mencionadas en el pliego."
            )
            with st.spinner("Procesando criterios de evaluación..."):
                try:
                    respuesta = model.generate_content([prompt_perfil, contexto_legal])
                    st.info("### Resultado del Análisis de Perfil")
                    st.markdown(respuesta.text)
                except Exception as e:
                    if "429" in str(e):
                        st.error("⏳ Límite de cuota alcanzado. Por favor, reintente en 30 segundos debido a la extensión del PDF.")
                    else:
                        st.error(f"Error en la consulta: {e}")

        # BOTÓN 2: Cuestionario de Datos para Anexos
        if st.button("📋 Generar Check-list para Anexos"):
            prompt_anexos = (
                "Basado en las bases cargadas, genera un cuestionario con los datos específicos que el usuario "
                "debe proporcionar para completar correctamente el Anexo de Datos del Postor y el Anexo de Experiencia. "
                "No incluyas datos que ya figuren claramente en las bases."
            )
            with st.spinner("Identificando campos requeridos..."):
                try:
                    respuesta = model.generate_content([prompt_anexos, contexto_legal])
                    st.warning("### Datos faltantes para el expediente:")
                    st.markdown(respuesta.text)
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("Cargue las bases en formato PDF para iniciar el análisis automático de requisitos.")

st.markdown("---")
st.caption("Herramienta de soporte para licitaciones públicas | Modelo: Gemini 2.5 Flash-Lite")
