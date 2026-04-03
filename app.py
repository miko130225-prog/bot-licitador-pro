import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO

# --- CONFIGURACIÓN DE IA ---
MODELO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO)
except Exception as e:
    st.error("Falta la API Key en st.secrets (GEMINI_API_KEY).")

# --- FUNCIONES TÉCNICAS ---
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
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)
    for line in texto.split('\n'):
        doc.add_paragraph(line)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Licitador Pro", layout="wide")
st.title("⚖️ Asistente de Anexos: Gran Teatro Nacional")

# Inicialización de estados
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'memoria' not in st.session_state: st.session_state.memoria = {}
if 'feedback' not in st.session_state: st.session_state.feedback = ""

# PASO 1: CARGA DE ARCHIVO
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases (.docx)", type="docx")
    if archivo and st.button("Analizar Documento"):
        with st.spinner("Leyendo bases..."):
            st.session_state.raw_text = obtener_texto(archivo)
            st.session_state.paso = 2
            st.rerun()

# PASO 2: SELECCIÓN DE VERSIÓN (CON FEEDBACK)
elif st.session_state.paso == 2:
    num_anexo = st.session_state.anexo_n
    st.subheader(f"Validando ANEXO N° {num_anexo}")
    
    with st.spinner("Buscando formatos..."):
        prompt_v = (
            f"Busca en el texto versiones del 'ANEXO N° {num_anexo}'. "
            f"REGLA: Solo incluye los que se llamen explícitamente ANEXO N° {num_anexo}. "
            f"Instrucción adicional del usuario: {st.session_state.feedback}. "
            "Si hay varios, lístalos separados por ';'. Si es único, responde 'UNICA'."
        )
        res_v = model.generate_content([prompt_v, st.session_state.raw_text]).text
    
    if "UNICA" in res_v.upper() and not st.session_state.feedback:
        st.session_state.version_txt = f"ANEXO N° {num_anexo}"
        st.session_state.paso = 3
        st.rerun()
    else:
        opciones = [o.strip().replace("*", "") for o in res_v.split(';') if len(o) > 5]
        
        col1, col2 = st.columns([2, 1])
        with col1:
            seleccion = st.radio("Versiones encontradas:", opciones)
            if st.button("Confirmar este Anexo"):
                st.session_state.version_txt = seleccion
                st.session_state.paso = 3
                st.rerun()
        
        with col2:
            st.warning("¿El análisis es incorrecto?")
            txt_corr = st.text_area("Indica la corrección (ej: 'Solo hay 2 anexos, ignora el tercero'):")
            if st.button("Aplicar Corrección"):
                st.session_state.feedback = txt_corr
                st.rerun()

# PASO 3: FORMULARIO DE LLENADO
elif st.session_state.paso == 3:
    st.subheader(f"Completando: {st.session_state.version_txt}")
    num_anexo = st.session_state.anexo_n
    
    if 'campos' not in st.session_state:
        with st.spinner("Extrayendo campos vacíos..."):
            p_campos = f"Lista los campos a llenar en el {st.session_state.version_txt} (tablas, corchetes, líneas). Separa por comas."
            res_c = model.generate_content([p_campos, st.session_state.raw_text]).text
            st.session_state.campos = [c.strip() for c in res_c.split(',') if c.strip()]

    # Formulario unificado para evitar errores de Submit
    with st.form(key=f"form_anexo_{num_anexo}"):
        respuestas = {}
        c1, c2 = st.columns(2)
        for i, campo in enumerate(st.session_state.campos):
            target_col = c1 if i % 2 == 0 else c2
            val_prev = st.session_state.memoria.get(campo, "")
            with target_col:
                # Usamos una key única inquebrantable
                respuestas[campo] = st.text_input(campo, value=val_prev, key=f"input_{num_anexo}_{i}")
        
        enviar = st.form_submit_button("Generar Word Final")
        
        if enviar:
            st.session_state.memoria.update(respuestas)
            with st.spinner("Redactando documento..."):
                p_final = (
                    f"Redacta el {st.session_state.version_txt} completo. Datos: {respuestas}. "
                    f"Formato original de las bases: {st.session_state.raw_text}. "
                    "No dejes campos vacíos ni corchetes."
                )
                st.session_state.docx_ready = model.generate_content(p_final).text
                st.session_state.paso = 4
                st.rerun()

# PASO 4: DESCARGA
elif st.session_state.paso == 4:
    st.success("Anexo generado con éxito.")
    st.text_area("Vista previa", st.session_state.docx_ready, height=300)
    
    doc_bin = exportar_word(st.session_state.docx_ready)
    st.download_button(f"⬇️ Descargar {st.session_state.version_txt}", data=doc_bin, file_name="Anexo_Lleno.docx")
    
    if st.button("Siguiente Anexo ➡️"):
        st.session_state.anexo_n += 1
        st.session_state.feedback = ""
        for k in ['campos', 'version_txt', 'docx_ready']: 
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
