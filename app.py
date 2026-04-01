import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import time

# --- CONFIGURACIÓN INICIAL ---
# Usamos la versión Lite que es la más estable para el Free Tier en 2026
MODELO_PRINCIPAL = 'gemini-2.0-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_PRINCIPAL)
except Exception as e:
    st.error("⚠️ Configura tu API Key en los 'Secrets' de Streamlit Cloud.")

# --- INTERFAZ TROPICAL/ESTADO PERUANO ---
st.set_page_config(page_title="Licitador Pro - Perú", page_icon="🇵🇪", layout="wide")

# Estilo visual cálido (Amarillo/Tropical)
st.markdown("""
    <style>
    .main { background-color: #FFFEF2; }
    .stButton>button { background-color: #FFC107; color: black; font-weight: bold; border-radius: 8px; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Analista de Licitaciones Pro")
st.caption("Especializado en el marco legal del Estado Peruano y Juegos Bolivarianos 2026")

# --- SECCIÓN DE DIAGNÓSTICO DE CUOTAS ---
with st.expander("🛠️ Diagnóstico de mi API Key (Ver cuotas y modelos)"):
    if st.button("Listar modelos con consulta gratuita"):
        try:
            modelos_disponibles = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    modelos_disponibles.append(m.name.replace('models/', ''))
            st.write("✅ Tu cuenta permite usar estos modelos:")
            st.json(modelos_disponibles)
        except Exception as e:
            st.error(f"No se pudo conectar con Google: {e}")

st.markdown("---")

# --- FUNCIONES TÉCNICAS ---
def extraer_texto_pdf(archivos):
    texto_acumulado = ""
    for archivo in archivos:
        try:
            pdf = PdfReader(archivo)
            for pagina in pdf.pages:
                texto_acumulado += pagina.extract_text() + "\n"
        except Exception as e:
            st.error(f"Error al leer {archivo.name}: {e}")
    return texto_acumulado

def consultar_gemini_con_retry(prompt, contexto):
    """Intenta la consulta y maneja el error de cuota 429"""
    try:
        # Enviamos el prompt y el texto del PDF
        response = model.generate_content([prompt, contexto])
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "ERROR_CUOTA"
        else:
            return f"Error inesperado: {str(e)}"

# --- CUERPO DE LA APP ---
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📂 Carga de Bases")
    archivos_pdf = st.file_uploader("Sube los PDFs de la licitación", type="pdf", accept_multiple_files=True)
    
    if archivos_pdf:
        with st.spinner("Leyendo documentos..."):
            texto_bases = extraer_texto_pdf(archivos_pdf)
        st.success(f"Lectura completada: {len(texto_bases)} caracteres detectados.")

with col2:
    st.header("⚖️ Análisis y Decisiones")
    
    if archivos_pdf:
        # BOTÓN 1: Perfil Legal
        if st.button("🔍 Identificar Perfil Legal (Natural/Jurídica)"):
            prompt = (
                "Analiza estas bases del Estado Peruano. Dime si el postor puede ser Persona Natural o Jurídica. "
                "Detalla requisitos de RNP, Vigencia de Poder y si hay bonos para MYPEs. Sé muy estructurado."
            )
            with st.spinner("Analizando bases..."):
                resultado = consultar_gemini_con_retry(prompt, texto_bases)
                
                if resultado == "ERROR_CUOTA":
                    st.error("⏳ **Cuota Excedida (Error 429).** Google ha pausado las consultas gratuitas momentáneamente.")
                    st.warning("Espera 30 segundos y vuelve a presionar el botón. Esto ocurre porque el PDF es muy extenso.")
                else:
                    st.info("### Resultado del Análisis")
                    st.markdown(resultado)

        # BOTÓN 2: Cuestionario para Anexos
        if st.button("📝 Generar Cuestionario para Anexos"):
            prompt = (
                "Basado en estas bases, genera una lista de preguntas para que el usuario me dé los datos "
                "necesarios para llenar el Anexo 1 (Datos del Postor) y el Anexo de Experiencia."
            )
            with st.spinner("Generando preguntas..."):
                resultado = consultar_gemini_con_retry(prompt, texto_bases)
                if resultado == "ERROR_CUOTA":
                    st.error("⏳ Error de cuota. Por favor reintenta en 30 segundos.")
                else:
                    st.warning("### Completa esta información:")
                    st.markdown(resultado)
    else:
        st.info("Sube un archivo PDF en la columna de la izquierda para habilitar el análisis.")

st.markdown("---")
st.caption("Desarrollado para la gestión eficiente de licitaciones públicas | Modelo: " + MODELO_PRINCIPAL)
