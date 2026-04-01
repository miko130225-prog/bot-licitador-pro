import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import time

# --- CONFIGURACIÓN DEL MODELO GANADOR ---
# gemini-2.5-flash-lite es el que tiene más cuota para PDFs pesados en 2026
MODELO_ELEGIDO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_ELEGIDO)
except Exception as e:
    st.error("Configura tu API Key en los Secrets de Streamlit.")

# --- CONFIGURACIÓN DE INTERFAZ (ESTILO TROPICAL) ---
st.set_page_config(page_title="Licitador Pro 2026", page_icon="🌴", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #FFF9E6; } /* Fondo amarillo cálido */
    .stButton>button { 
        background-color: #FF8F00; 
        color: white; 
        border-radius: 20px; 
        border: none;
        font-weight: bold;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button:hover { background-color: #E65100; color: white; }
    h1 { color: #2E7D32; font-family: 'Trebuchet MS'; } /* Verde palmera */
    </style>
    """, unsafe_allow_html=True)

st.title("🗿 Asistente de Gestión Exotikeh")
st.caption("Analista experto en el Estado Peruano y Grandes Eventos")
st.markdown("---")

# --- FUNCIONES ---
def extraer_texto(archivos):
    texto_full = ""
    for arc in archivos:
        try:
            reader = PdfReader(arc)
            for page in reader.pages:
                texto_full += page.extract_text() + "\n"
        except Exception as e:
            st.error(f"Error en {arc.name}: {e}")
    return texto_full

# --- COLUMNAS DE TRABAJO ---
col_carga, col_analisis = st.columns([1, 2])

with col_carga:
    st.header("📂 Carga de Bases")
    subidos = st.file_uploader("Sube los PDFs de la licitación", type="pdf", accept_multiple_files=True)
    
    if subidos:
        with st.spinner("🏝️ Navegando por el documento..."):
            contexto = extraer_texto(subidos)
        st.success(f"¡Listo! {len(subidos)} archivos leídos.")
        
        # Diagnóstico rápido de cuota (Opcional)
        if st.checkbox("Verificar salud de conexión"):
            st.write(f"Conectado a: **{MODELO_ELEGIDO}**")

with col_analisis:
    st.header("⚖️ Análisis Legal")
    
    if subidos:
        # BOTÓN 1: Perfil Legal
        if st.button("🔍 Identificar Perfil (¿Natural o Jurídica?)"):
            prompt = (
                "Eres un experto en contrataciones del Estado Peruano. Analiza estas bases y dime: "
                "1. ¿Se permite postular como Persona Natural? "
                "2. Si es Persona Jurídica, ¿qué documentos específicos de SUNARP pide? "
                "3. ¿Hay restricciones por el monto o garantías? "
                "Responde con viñetas claras."
            )
            with st.spinner("Consultando al oráculo..."):
                try:
                    res = model.generate_content([prompt, contexto])
                    st.info("### Perfil Requerido")
                    st.markdown(res.text)
                except Exception as e:
                    if "429" in str(e):
                        st.error("⚠️ Cuota llena. Espera 20 segundos. El archivo es pesado.")
                    else:
                        st.error(f"Error: {e}")

        # BOTÓN 2: Anexos
        if st.button("📝 Generar Cuestionario para Anexos"):
            prompt = "Basado en las bases, dime qué 5 datos específicos debo darte para rellenar el Anexo 1 hoy mismo."
            try:
                res = model.generate_content([prompt, contexto])
                st.warning("### Datos faltantes:")
                st.markdown(res.text)
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("Sube un PDF para activar el análisis tropical.")

st.markdown("---")
st.caption("Ecosistema Exotikeh 2026 | Powered by Gemini 2.5 Flash-Lite")
