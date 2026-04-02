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

def generar_word_resultado(texto_contenido):
    doc = Document()
    for linea in texto_contenido.split('\n'):
        doc.add_paragraph(linea)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- ESTADO DE SESIÓN (PERSISTENCIA) ---
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_actual' not in st.session_state: st.session_state.anexo_actual = 1
if 'datos_por_anexo' not in st.session_state: st.session_state.datos_por_anexo = {}
if 'modalidad' not in st.session_state: st.session_state.modalidad = None

st.set_page_config(page_title="Licitador Automático Pro", layout="wide")
st.title("⚖️ Generador de Expedientes de Licitación")

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases")
    archivos = st.file_uploader("Sube las bases (PDF o Word)", type=["pdf", "docx"], accept_multiple_files=True)
    if archivos and st.button("Iniciar Análisis de Bases"):
        st.session_state.texto_bases = leer_archivos(archivos)
        st.session_state.paso = 2
        st.rerun()

# --- PASO 2: MODALIDAD ---
elif st.session_state.paso == 2:
    st.header("2️⃣ Definición de Postulación")
    eleccion = st.radio("¿Cómo postularás?", ["Seleccione...", "Empresa Única", "Consorcio"])
    if eleccion != "Seleccione..." and st.button("Confirmar Modalidad"):
        st.session_state.modalidad = eleccion
        st.session_state.paso = 3
        st.rerun()

# --- PASO 3: ENTREVISTA Y GENERACIÓN POR ANEXO ---
elif st.session_state.paso == 3:
    num_anexo = st.session_state.anexo_actual
    st.header(f"3️⃣ Completando ANEXO N° {num_anexo}")
    
    # 1. El bot identifica qué versión del anexo corresponde y qué datos pide
    if f'campos_anexo_{num_anexo}' not in st.session_state:
        with st.spinner(f"Analizando requisitos del Anexo {num_anexo}..."):
            prompt_campos = (
                f"Analiza las bases. El postor es {st.session_state.modalidad}. "
                f"Busca el formato del ANEXO N° {num_anexo}. "
                f"Lista todos los datos que el usuario debe llenar para este anexo específicamente. "
                "Responde solo la lista de campos separada por comas."
            )
            res = model.generate_content([prompt_campos, st.session_state.texto_bases])
            st.session_state[f'campos_anexo_{num_anexo}'] = res.text.split(',')

    # 2. Formulario para el Anexo Actual
    with st.form(f"form_anexo_{num_anexo}"):
        st.subheader(f"Datos para el Anexo {num_anexo}")
        respuestas = {}
        for campo in st.session_state[f'campos_anexo_{num_anexo}']:
            if campo.strip():
                respuestas[campo.strip()] = st.text_input(campo.strip())
        
        if st.form_submit_button(f"Generar Word del Anexo {num_anexo}"):
            # 3. Generar el texto legal con los datos insertados
            datos_str = "\n".join([f"{k}: {v}" for k, v in respuestas.items()])
            prompt_llenado = (
                f"Redacta el ANEXO N° {num_anexo} completo para {st.session_state.modalidad}. "
                f"Usa estos datos: {datos_str}. "
                f"Sigue el formato exacto de las bases: {st.session_state.texto_bases}. "
                "NO uses corchetes, integra la información directamente en el texto."
            )
            st.session_state[f'resultado_anexo_{num_anexo}'] = model.generate_content(prompt_llenado).text
            st.rerun()

    # 4. Mostrar resultado y permitir descarga
    if f'resultado_anexo_{num_anexo}' in st.session_state:
        st.success(f"¡Anexo {num_anexo} listo!")
        st.text_area("Vista Previa:", st.session_state[f'resultado_anexo_{num_anexo}'], height=300)
        
        word_file = generar_word_resultado(st.session_state[f'resultado_anexo_{num_anexo}'])
        st.download_button(
            label=f"⬇️ Descargar Anexo {num_anexo} (.docx)",
            data=word_file,
            file_name=f"Anexo_{num_anexo}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        st.markdown("---")
        if st.button(f"Continuar al Anexo N° {num_anexo + 1} ➡️"):
            st.session_state.anexo_actual += 1
            # Limpiamos para el siguiente anexo
            st.rerun()

    if st.button("⬅️ Cambiar Modalidad"):
        st.session_state.paso = 2
        st.rerun()
