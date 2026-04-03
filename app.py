import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO

# --- CONFIGURACIÓN ---
MODELO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO)
except Exception as e:
    st.error("Falta la API Key en st.secrets.")

# --- UTILIDADES ---
def obtener_texto(archivo):
    doc = Document(archivo)
    full_text = []
    for p in doc.paragraphs:
        full_text.append(p.text)
    for t in doc.tables:
        for r in t.rows:
            full_text.append(" | ".join(c.text.strip() for c in r.cells))
    return "\n".join(full_text)

def exportar_word(texto):
    doc = Document()
    for line in texto.split('\n'):
        p = doc.add_paragraph(line)
        p.style.font.name = 'Arial'
        p.style.font.size = Pt(10)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- INTERFAZ ---
st.set_page_config(page_title="Licitador Simple", layout="centered")
st.title("⚖️ Asistente de Anexos")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'memoria' not in st.session_state: st.session_state.memoria = {}

# PASO 1: CARGA
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases (.docx)", type="docx")
    if archivo and st.button("Analizar Anexos"):
        st.session_state.raw_text = obtener_texto(archivo)
        st.session_state.paso = 2
        st.rerun()

# PASO 2: SELECCIÓN DE VERSIÓN (Solo si hay más de una)
elif st.session_state.paso == 2:
    n = st.session_state.anexo_n
    st.subheader(f"Configurando Anexo N° {n}")
    
    prompt_v = f"¿Cuántas versiones distintas del ANEXO N° {n} existen en este texto? Si hay más de una, lístalas brevemente separadas por ';'. Si es única, responde 'UNICA'."
    res_v = model.generate_content([prompt_v, st.session_state.raw_text]).text
    
    if "UNICA" in res_v.upper():
        st.session_state.version_txt = f"ANEXO N° {n}"
        st.session_state.paso = 3
        st.rerun()
    else:
        opciones = [o.strip() for o in res_v.split(';') if len(o) > 2]
        seleccion = st.radio("Se detectaron varias versiones. ¿Cuál llenamos?", opciones)
        if st.button("Confirmar Selección"):
            st.session_state.version_txt = seleccion
            st.session_state.paso = 3
            st.rerun()

# PASO 3: ENTREVISTA Y LLENADO
elif st.session_state.paso == 3:
    st.subheader(f"Datos para: {st.session_state.version_txt}")
    
    # Extraer campos necesarios
    if 'campos' not in st.session_state:
        p_campos = f"Lista solo los nombres de los campos vacíos, entre corchetes o líneas de puntos en el {st.session_state.version_txt}. Separa por comas."
        res_c = model.generate_content([p_campos, st.session_state.raw_text]).text
        st.session_state.campos = [c.strip() for c in res_c.split(',') if c.strip()]

    with st.form("form_final"):
        respuestas = {}
        for i, campo in enumerate(st.session_state.campos):
            # Key única para evitar el error StreamlitDuplicateElementId
            val_prev = st.session_state.memoria.get(campo, "")
            respuestas[campo] = st.text_input(campo, value=val_prev, key=f"in_{n}_{i}")
        
        if st.form_submit_button("Generar Documento"):
            st.session_state.memoria.update(respuestas)
            p_final = f"Redacta el {st.session_state.version_txt} completo. Usa estos datos: {respuestas}. Respeta estrictamente el formato de tabla y texto de las bases: {st.session_state.raw_text}. No dejes campos vacíos."
            st.session_state.docx_ready = model.generate_content(p_final).text
            st.session_state.paso = 4
            st.rerun()

# PASO 4: DESCARGA Y SIGUIENTE
elif st.session_state.paso == 4:
    st.success("¡Documento generado!")
    st.text_area("Previsualización", st.session_state.docx_ready, height=300)
    
    st.download_button("⬇️ Descargar Word", 
                       data=exportar_word(st.session_state.docx_ready), 
                       file_name=f"Anexo_{st.session_state.anexo_n}.docx")
    
    if st.button("Ir al Siguiente Anexo ➡️"):
        st.session_state.anexo_n += 1
        # Limpiar claves específicas para resetear el formulario
        for k in ['campos', 'version_txt', 'docx_ready']: 
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
