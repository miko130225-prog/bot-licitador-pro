import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from docx import Document
from io import BytesIO

# --- CONFIGURACIÓN DE IA ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")

# --- FUNCIONES TÉCNICAS ---
def leer_archivos(archivos):
    texto = ""
    for arc in archivos:
        if arc.name.endswith('.pdf'):
            reader = PdfReader(arc)
            for page in reader.pages:
                texto += page.extract_text() + "\n"
        elif arc.name.endswith('.docx'):
            doc = Document(arc)
            for p in doc.paragraphs:
                texto += p.text + "\n"
    return texto

def generar_word_resultado(texto_completo):
    doc = Document()
    for linea in texto_completo.split('\n'):
        doc.add_paragraph(linea)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- ESTADO DE SESIÓN ---
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'texto_bases' not in st.session_state: st.session_state.texto_bases = ""
if 'modalidad' not in st.session_state: st.session_state.modalidad = None

st.set_page_config(page_title="Generador de Anexos Licitación", layout="wide")
st.title("⚖️ Asistente de Postulación: Gran Teatro Nacional")

# --- PASO 1: PROCESAMIENTO ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases Integradas")
    archivos = st.file_uploader("Sube las bases (PDF o Word)", type=["pdf", "docx"], accept_multiple_files=True)
    if archivos and st.button("Analizar Documentación"):
        st.session_state.texto_bases = leer_archivos(archivos)
        st.session_state.paso = 2
        st.rerun()

# --- PASO 2: DECISIÓN ESTRATÉGICA ---
elif st.session_state.paso == 2:
    st.header("2️⃣ Definición de la Modalidad de Postulación")
    st.info("Bases analizadas. Según el reglamento de contrataciones, primero debemos definir su estructura de postor.")
    
    col1, col2 = st.columns(2)
    with col1:
        eleccion = st.radio(
            "¿Cómo se presentará a este concurso?",
            ["Seleccione...", "Postor Individual (Empresa única)", "Consorcio (Unión de dos o más empresas)"],
            index=0
        )
    
    if eleccion != "Seleccione...":
        if st.button("Confirmar y Filtrar Anexos"):
            st.session_state.modalidad = eleccion
            st.session_state.paso = 3
            st.rerun()

# --- PASO 3: RECOLECCIÓN DE DATOS Y GENERACIÓN ---
elif st.session_state.paso == 3:
    st.header(f"3️⃣ Formulario de Datos: {st.session_state.modalidad}")
    
    # La IA identifica los campos según la modalidad elegida
    if 'campos_necesarios' not in st.session_state:
        with st.spinner("Buscando formatos de anexos en las bases..."):
            es_consorcio = "SÍ" if "Consorcio" in st.session_state.modalidad else "NO"
            prompt_campos = (
                f"El postor aplicará como Consorcio: {es_consorcio}. "
                "Basado estrictamente en los formatos al final de las bases, identifica los datos específicos "
                "que requiere el ANEXO 1 para esta modalidad (Individual o Consorcio). "
                "Devuelve solo los nombres de los campos separados por comas."
            )
            res = model.generate_content([prompt_campos, st.session_state.texto_bases])
            st.session_state.campos_necesarios = res.text.split(',')

    st.warning(f"Complete la información para generar el **Anexo 1**:")
    
    datos_finales = {}
    with st.form("datos_anexo"):
        for campo in st.session_state.campos_necesarios:
            campo_limpio = campo.strip()
            if campo_limpio:
                datos_finales[campo_limpio] = st.text_input(campo_limpio)
        
        if st.form_submit_button("Generar Archivo Word Completo"):
            # Generación del contenido legal
            with st.spinner("Redactando Anexo con validez legal..."):
                datos_str = "\n".join([f"{k}: {v}" for k, v in datos_finales.items()])
                prompt_redaccion = (
                    f"Redacta el ANEXO 1 completo (Declaración Jurada de Datos del Postor) para un {st.session_state.modalidad}. "
                    f"Usa estos datos proporcionados: {datos_str}. "
                    f"Sigue fielmente el formato encontrado en las bases: {st.session_state.texto_bases}. "
                    "No dejes espacios vacíos, rellena todo con los datos dados."
                )
                contenido_final = model.generate_content(prompt_redaccion).text
                
                st.session_state.documento_listo = contenido_final
                st.session_state.paso = 4
                st.rerun()

# --- PASO 4: DESCARGA ---
elif st.session_state.paso == 4:
    st.header("4️⃣ Descarga de Documento Final")
    st.text_area("Previsualización del Anexo:", st.session_state.documento_listo, height=400)
    
    word_bin = generar_word_resultado(st.session_state.documento_listo)
    
    st.download_button(
        label="⬇️ Descargar Anexo 1 en Word (.docx)",
        data=word_bin,
        file_name="Anexo_1_Datos_Postor.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    
    if st.button("Reiniciar proceso"):
        st.session_state.paso = 1
        st.rerun()
