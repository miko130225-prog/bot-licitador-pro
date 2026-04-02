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

# --- FUNCIONES DE SOPORTE ---
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

def crear_word(texto_contenido):
    doc = Document()
    for linea in texto_contenido.split('\n'):
        doc.add_paragraph(linea)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- CONFIGURACIÓN DE SESIÓN ---
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'texto_bases' not in st.session_state: st.session_state.texto_bases = ""
if 'anexos_validos' not in st.session_state: st.session_state.anexos_validos = []
if 'datos_recolectados' not in st.session_state: st.session_state.datos_recolectados = {}

st.set_page_config(page_title="Generador de Anexos Pro", layout="wide")
st.title("⚖️ Gestor Inteligente de Anexos de Licitación")

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases Integradas")
    archivos = st.file_uploader("Subir PDF o Word de la convocatoria", type=["pdf", "docx"], accept_multiple_files=True)
    if archivos and st.button("Procesar Documentación"):
        st.session_state.texto_bases = leer_archivos(archivos)
        st.session_state.paso = 2
        st.rerun()

# --- PASO 2: FILTRO LEGAL Y ENTREVISTA ---
elif st.session_state.paso == 2:
    st.header("2️⃣ Clasificación y Recolección de Datos")
    
    # El Bot analiza qué anexos aplican realmente
    if not st.session_state.anexos_validos:
        with st.spinner("Analizando qué anexos son obligatorios para ti..."):
            prompt_filtro = (
                "Analiza las bases e identifica los anexos obligatorios. "
                "Descarta los que son opcionales o para casos específicos que no aplican (ej. si no se menciona consorcio, descartar anexos de consorcio). "
                "Devuelve una lista de los nombres de anexos necesarios y para cada uno, los datos que el usuario debe proveer. "
                "Formato: ANEXO X: dato1, dato2 | ANEXO Y: dato1, dato2"
            )
            res = model.generate_content([prompt_filtro, st.session_state.texto_bases])
            # Guardamos la estructura para el formulario
            st.session_state.anexos_validos = res.text.split('|')

    st.info("Responde a los campos solicitados para los anexos identificados:")
    
    with st.form("entrevista_anexos"):
        for bloque in st.session_state.anexos_validos:
            if ":" in bloque:
                nombre_anexo, campos = bloque.split(":", 1)
                st.subheader(nombre_anexo.strip())
                for campo in campos.split(','):
                    c_clean = campo.strip()
                    if c_clean:
                        key = f"{nombre_anexo.strip()}_{c_clean}"
                        st.session_state.datos_recolectados[key] = st.text_input(f"Dato para {nombre_anexo}: {c_clean}", key=key)
        
        if st.form_submit_button("Generar Archivos Word"):
            st.session_state.paso = 3
            st.rerun()

# --- PASO 3: GENERACIÓN Y DESCARGA ---
elif st.session_state.paso == 3:
    st.header("3️⃣ Documentos Generados")
    st.success("Se han procesado los formatos con la información proporcionada.")

    # Agrupamos datos por anexo para la generación
    anexos_finales = {}
    for key, valor in st.session_state.datos_recolectados.items():
        nombre_anexo = key.split('_')[0]
        if nombre_anexo not in anexos_finales: anexos_finales[nombre_anexo] = ""
        anexos_finales[nombre_anexo] += f"{key.split('_')[1]}: {valor}\n"

    for nombre, datos_txt in anexos_finales.items():
        with st.expander(f"Previsualizar {nombre}"):
            prompt_doc = (
                f"Redacta el {nombre} completo basándote en el formato de las bases: {st.session_state.texto_bases}. "
                f"Usa estos datos del usuario: {datos_txt}. "
                "Devuelve solo el texto legal final, listo para un documento oficial."
            )
            contenido_anexo = model.generate_content(prompt_doc).text
            st.text(contenido_anexo)
            
            # Botón de Descarga Word
            word_data = crear_word(contenido_anexo)
            st.download_button(
                label=f"⬇️ Descargar {nombre} (.docx)",
                data=word_data,
                file_name=f"{nombre.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    if st.button("⬅️ Volver a Clasificación"):
        st.session_state.paso = 2
        st.rerun()

st.markdown("---")
st.caption("Generación Documental Automática 2026 | Licitaciones Perú")
