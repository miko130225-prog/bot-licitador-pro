import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
import io

# --- CONFIGURACIÓN DE IA ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets.")

# --- FUNCIONES DE LECTURA ---
def leer_documentos(archivos):
    texto_total = ""
    for archivo in archivos:
        if archivo.name.endswith('.pdf'):
            reader = PdfReader(archivo)
            for page in reader.pages:
                texto_total += page.extract_text() + "\n"
        elif archivo.name.endswith('.docx'):
            doc = Document(archivo)
            for para in doc.paragraphs:
                texto_total += para.text + "\n"
    return texto_total

# --- INTERFAZ ---
st.set_page_config(page_title="Gestor de Licitaciones Pro", layout="wide")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'texto_bases' not in st.session_state: st.session_state.texto_bases = ""
if 'datos_usuario' not in st.session_state: st.session_state.datos_usuario = {}

st.title("⚖️ Generador Automático de Anexos")
st.markdown("---")

# PASO 1: CARGA MULTIFORMATO
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases Integradas")
    st.info("Puedes subir el PDF de la convocatoria o el Word con los formatos de anexos.")
    archivos = st.file_uploader("Sube tus archivos (PDF o Word)", type=["pdf", "docx"], accept_multiple_files=True)
    
    if archivos:
        if st.button("Procesar y Extraer Formatos"):
            with st.spinner("Analizando estructura de los anexos..."):
                st.session_state.texto_bases = leer_documentos(archivos)
                st.session_state.paso = 2
                st.rerun()

# PASO 2: ENTREVISTA DINÁMICA
elif st.session_state.paso == 2:
    st.header("2️⃣ Información Requerida para los Anexos")
    st.markdown("El bot ha detectado los campos necesarios en las bases. Por favor, completa los datos:")
    
    # Pedimos a la IA que identifique qué datos faltan según las bases
    if 'preguntas' not in st.session_state:
        with st.spinner("Identificando campos obligatorios en los anexos..."):
            prompt_campos = (
                "Analiza los anexos al final de estas bases. Genera una lista de campos de información "
                "que el postor debe proveer (ej: RUC, DNI del representante, Dirección, Correo, etc.). "
                "Devuélvelos como una lista simple separada por comas."
            )
            res = model.generate_content([prompt_campos, st.session_state.texto_bases])
            st.session_state.preguntas = res.text.split(',')

    # Formulario dinámico
    with st.form("form_datos"):
        for campo in st.session_state.preguntas:
            campo_limpio = campo.strip().replace("*", "")
            if campo_limpio:
                st.session_state.datos_usuario[campo_limpio] = st.text_input(f"Ingrese: {campo_limpio}")
        
        enviar = st.form_submit_button("Confirmar Datos y Generar Anexos")
        if enviar:
            st.session_state.paso = 3
            st.rerun()

    if st.button("⬅️ Volver a cargar"):
        st.session_state.paso = 1
        st.rerun()

# PASO 3: GENERACIÓN FINAL
elif st.session_state.paso == 3:
    st.header("3️⃣ Anexos Generados")
    st.success("Tus datos han sido integrados en los formatos de las bases.")
    
    # Botón para redactar el Anexo 1 con los datos reales
    if st.button("📄 Redactar Anexo 1 Completo"):
        datos_str = "\n".join([f"{k}: {v}" for k, v in st.session_state.datos_usuario.items()])
        prompt_final = (
            f"Usando estos datos del usuario:\n{datos_str}\n\n"
            f"Y basándote en el formato de Anexo 1 de estas bases:\n{st.session_state.texto_bases}\n\n"
            "Redacta el Anexo 1 completo, reemplazando todos los campos vacíos con la información provista. "
            "Mantén el rigor legal del Estado Peruano."
        )
        with st.spinner("Redactando documento final..."):
            res = model.generate_content([prompt_final, st.session_state.texto_bases])
            st.text_area("Copia este texto en tu Word de postulación:", res.text, height=400)

    if st.button("⬅️ Editar datos o perfil"):
        st.session_state.paso = 2
        st.rerun()

st.markdown("---")
st.caption("Soporte para PDF/Word | Análisis de Bases Integradas 2026")
