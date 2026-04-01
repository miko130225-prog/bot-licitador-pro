import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import time

# --- CONFIGURACIÓN DE MODELO 2026 ---
# Usamos 'flash-lite' para evitar el bloqueo de cuota 0 del modelo 'flash' normal
MODEL_NAME = 'gemini-2.0-flash-lite' 

try:
    # Obtener API Key de los Secrets de Streamlit
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"Configura tu API Key en los Secrets de Streamlit: {e}")

# Configuración de página con estilo "Tropical/Tiki" (Warm colors)
st.set_page_config(page_title="Asistente de Licitaciones Pro", page_icon="🌴", layout="centered")

# Estilo visual personalizado
st.markdown("""
    <style>
    .main { background-color: #FFF9E6; }
    .stButton>button { background-color: #FFB300; color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🗿 Analista de Licitaciones (Modo Eficiente)")
st.subheader("Carga las bases y deja que la IA trabaje")
st.markdown("---")

# Función para extraer y limpiar texto
def extraer_texto(archivos_subidos):
    texto_completo = ""
    for archivo in archivos_subidos:
        try:
            reader = PdfReader(archivo)
            for pagina in reader.pages:
                # Limpiamos espacios extra para ahorrar tokens de cuota
                texto_completo += pagina.extract_text().strip() + "\n"
        except Exception as e:
            st.error(f"Error al leer {archivo.name}: {e}")
    return texto_completo

# --- INTERFAZ DE CARGA ---
archivos = st.file_uploader("Adjunta los PDFs de las Bases (Juegos Bolivarianos, etc.)", type="pdf", accept_multiple_files=True)

if archivos:
    with st.spinner("Procesando documentos..."):
        contexto_bases = extraer_texto(archivos)
    
    st.success(f"✅ Se han procesado {len(archivos)} archivo(s).")

    # BOTÓN: Identificación de Perfil
    if st.button("🔍 Identificar Perfil Legal"):
        prompt = (
            "Eres un experto senior en contrataciones del Estado Peruano. "
            "Analiza estas bases de licitación y responde con precisión: "
            "1. ¿El postor puede ser Persona Natural o Jurídica? "
            "2. Lista los documentos de identidad, vigencia de poder o RNP solicitados. "
            "3. ¿Qué garantías (fiel cumplimiento o seriedad) se exigen?"
        )
        
        with st.spinner("Consultando a Gemini 2.0 Lite..."):
            try:
                # Ejecución de la consulta
                response = model.generate_content([prompt, contexto_bases])
                st.info("### ⚖️ Análisis Legal de las Bases")
                st.markdown(response.text)
            except Exception as e:
                # Manejo inteligente del error 429 de cuota
                if "429" in str(e):
                    st.error("⚠️ **Cuota de Google excedida.** Por favor, espera 60 segundos antes de volver a intentar. Esto sucede porque el archivo es muy pesado para el plan gratuito.")
                    st.warning("Consejo: Prueba subiendo solo las páginas de 'Requisitos del Postor' del PDF.")
                else:
                    st.error(f"Se produjo un error: {e}")

    # BOTÓN: Generar Anexo 1
    if st.button("📝 Preparar Datos para Anexos"):
        prompt_anexos = (
            "Basado en estas bases, hazme una lista de los datos que me faltan para llenar el Anexo 1. "
            "Pídemelos en formato de cuestionario simple."
        )
        try:
            response = model.generate_content([prompt_anexos, contexto_bases])
            st.warning("### Responde esto para completar tu expediente:")
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("👋 Sube tus bases en PDF para comenzar.")

st.markdown("---")
st.caption("Powered by Gemini 2.0 Flash-Lite | Optimizado para el Estado Peruano 2026")
