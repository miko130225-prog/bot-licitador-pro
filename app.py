import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# --- CONFIGURACIÓN DE IA ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor de Licitaciones Pro", page_icon="⚖️", layout="wide")

# Inicialización de estados para el flujo
if 'paso' not in st.session_state:
    st.session_state.paso = 1  # 1: Carga, 2: Perfil, 3: Generación
if 'texto_bases' not in st.session_state:
    st.session_state.texto_bases = ""
if 'perfil' not in st.session_state:
    st.session_state.perfil = {}

def leer_pdf(archivos):
    texto = ""
    for arc in archivos:
        reader = PdfReader(arc)
        for page in reader.pages:
            texto += page.extract_text() + "\n"
    return texto

# --- DISEÑO ---
st.title("⚖️ Asistente Inteligente de Postulación")
st.markdown("---")

# --- PASO 1: CARGA Y PROCESAMIENTO ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Documentación")
    archivos = st.file_uploader("Sube las bases de la licitación (PDF)", type="pdf", accept_multiple_files=True)
    
    if archivos:
        with st.spinner("Procesando archivos técnicos..."):
            st.session_state.texto_bases = leer_pdf(archivos)
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: DEFINICIÓN DEL POSTOR ---
elif st.session_state.paso == 2:
    st.header("2️⃣ Configuración del Postor")
    st.info("Documentos procesados con éxito. Ahora, define tu perfil para ajustar la generación de documentos.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tipo_postor = st.selectbox(
            "¿Cómo te presentarás a este proceso?",
            ["Selecciona una opción", "Persona Jurídica (Empresa Nacional)", "Persona Jurídica (Extranjera)", "Persona Natural (Consultor/Individual)", "Consorcio"]
        )
        
        es_mype = st.radio("¿Eres una MYPE inscrita en el REMYPE?", ["No", "Sí"])
    
    with col2:
        st.markdown("**Resumen detectado en las bases:**")
        # Pequeño resumen automático para ayudar al usuario a decidir
        if st.button("Verificar compatibilidad rápida"):
            with st.spinner("Analizando restricciones de las bases..."):
                res = model.generate_content([
                    "Analiza brevemente si estas bases permiten Personas Naturales y Consorcios.", 
                    st.session_state.texto_bases
                ])
                st.write(res.text)

    if tipo_postor != "Selecciona una opción":
        if st.button("Confirmar Perfil y Continuar"):
            st.session_state.perfil = {"tipo": tipo_postor, "mype": es_mype}
            st.session_state.paso = 3
            st.rerun()
    
    if st.button("⬅️ Volver a cargar archivos"):
        st.session_state.paso = 1
        st.rerun()

# --- PASO 3: GENERACIÓN DE DOCUMENTOS ---
elif st.session_state.paso == 3:
    st.header(f"3️⃣ Panel de Generación: {st.session_state.perfil['tipo']}")
    
    st.success(f"Configuración activa: **{st.session_state.perfil['tipo']}** | MYPE: **{st.session_state.perfil['mype']}**")
    
    tab1, tab2, tab3 = st.tabs(["📋 Requisitos Específicos", "✍️ Borrador de Anexos", "✅ Check-list Final"])
    
    with tab1:
        st.subheader("Documentos exigidos para tu perfil")
        if st.button("Generar Lista de Documentos"):
            prompt = f"Basado en las bases, lista solo los documentos que debe presentar una {st.session_state.perfil['tipo']} (MYPE: {st.session_state.perfil['mype']})."
            with st.spinner("Filtrando pliego..."):
                res = model.generate_content([prompt, st.session_state.texto_bases])
                st.markdown(res.text)

    with tab2:
        st.subheader("Borradores de Anexos")
        opcion_anexo = st.selectbox("¿Qué anexo deseas redactar?", ["Anexo 1 - Datos del Postor", "Anexo 2 - Declaración Jurada", "Anexo de Experiencia"])
        
        if st.button(f"Redactar {opcion_anexo}"):
            prompt = (
                f"Redacta el {opcion_anexo} siguiendo el formato de las bases para una {st.session_state.perfil['tipo']}. "
                "Usa [CORCHETES] para los datos que el usuario debe completar manualmente."
            )
            with st.spinner("Generando borrador legal..."):
                res = model.generate_content([prompt, st.session_state.texto_bases])
                st.code(res.text, language="text")

    with tab3:
        st.subheader("Preguntas de Control")
        if st.button("¿Qué me falta responder?"):
            prompt = "Haz una lista de 5 preguntas clave que debo responderme antes de cerrar mi oferta para evitar ser descalificado según estas bases."
            res = model.generate_content([prompt, st.session_state.texto_bases])
            st.markdown(res.text)

    if st.button("⬅️ Cambiar Perfil / Reiniciar"):
        st.session_state.paso = 2
        st.rerun()

st.markdown("---")
st.caption("Flujo de trabajo estructurado para Licitaciones Públicas | Modelo: " + MODELO_TÉCNICO)
