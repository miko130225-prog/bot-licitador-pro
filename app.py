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
        if p.text.strip(): full_text.append(p.text)
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
st.set_page_config(page_title="Licitador Pro", layout="wide")
st.title("⚖️ Asistente de Anexos Inteligente")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'memoria' not in st.session_state: st.session_state.memoria = {}
if 'feedback_usuario' not in st.session_state: st.session_state.feedback_usuario = ""

# PASO 1: CARGA
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases (.docx)", type="docx")
    if archivo and st.button("Analizar Anexos"):
        st.session_state.raw_text = obtener_texto(archivo)
        st.session_state.paso = 2
        st.rerun()

# PASO 2: SELECCIÓN Y CORRECCIÓN
elif st.session_state.paso == 2:
    n = st.session_state.anexo_n
    st.subheader(f"Validando ANEXO N° {n}")
    
    # Análisis de la IA con el feedback del usuario incluido
    prompt_v = (
        f"Analiza el texto y busca versiones del 'ANEXO N° {n}'. "
        f"REGLA CRÍTICA: Solo incluye los que se llamen explícitamente ANEXO N° {n}. "
        f"Comentario del usuario para corregir el análisis: {st.session_state.feedback_usuario}. "
        "Si hay varios, lístalos brevemente separados por ';'. Si es único, responde 'UNICA'."
    )
    res_v = model.generate_content([prompt_v, st.session_state.raw_text]).text
    
    if "UNICA" in res_v.upper() and not st.session_state.feedback_usuario:
        st.session_state.version_txt = f"ANEXO N° {n}"
        st.session_state.paso = 3
        st.rerun()
    else:
        opciones = [o.strip().replace("*", "") for o in res_v.split(';') if len(o) > 5]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            seleccion = st.radio("Versiones detectadas:", opciones)
            if st.button("Confirmar Selección"):
                st.session_state.version_txt = seleccion
                st.session_state.paso = 3
                st.rerun()
        
        with col2:
            st.info("¿El análisis es incorrecto?")
            nuevo_feedback = st.text_area("Explica la equivocación (ej: 'Solo hay 2 anexos, ignora el Pacto de Integridad'):")
            if st.button("Corregir Análisis"):
                st.session_state.feedback_usuario = nuevo_feedback
                st.rerun()

# PASO 3: FORMULARIO
elif st.session_state.paso == 3:
    st.subheader(f"Completando: {st.session_state.version_txt}")
    
    if 'campos' not in st.session_state:
        p_campos = (
            f"Basado en el formato de {st.session_state.version_txt} en las bases, "
            "lista todos los campos a llenar (tablas, corchetes, líneas). Separa por comas."
        )
        res_c = model.generate_content([p_campos, st.session_state.raw_text]).text
        st.session_state.campos = [c.strip() for c in res_c.split(',') if c.strip()]

    with st.form("form_datos"):
        respuestas = {}
        # Usamos columnas para que se vea más ordenado
        c1, c2 = st.columns(2)
        for i, campo in enumerate(st.session_state.campos):
            target_col = c1 if i % 2 == 0 else c2
            val_prev = st.session_state.memoria.get(campo, "")
            with target_col:
                respuestas[campo] = st.text_input(campo, value=val_prev, key=f"in_{n}_{i}")
        
        if st.form_submit_button("Generar Word con estos datos"):
            st.session_state.memoria.update(respuestas)
            p_final = (
                f"Redacta el {st.session_state.version_txt} íntegro. Usa estos datos: {respuestas}. "
                f"Formato original: {st.session_state.raw_text}. "
                "No dejes ningún campo vacío ni con corchetes."
            )
            st.session_state.docx_ready = model.generate_content(p_final).text
            st.session_state.paso = 4
            st.rerun()

# PASO 4: RESULTADO
elif st.session_state.paso == 4:
    st.success("Documento generado correctamente.")
    st.text_area("Vista previa", st.session_state.docx_ready, height=350)
    
    st.download_button("⬇️ Descargar Archivo Word", 
                       data=exportar_word(st.session_state.docx_ready), 
                       file_name=f"{st.session_state.version_txt}.docx")
    
    if st.button("Ir al Siguiente Anexo ➡️"):
        st.session_state.anexo_n += 1
        st.session_state.feedback_usuario = "" # Resetear feedback para el nuevo anexo
        for k in ['campos', 'version_txt', 'docx_ready']: 
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
