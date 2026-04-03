import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO
import time

# --- CONFIGURACIÓN DE IA ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets (GEMINI_API_KEY).")

# --- FUNCIONES DE SOPORTE ---
def extraer_contenido_completo(archivos):
    texto_total = ""
    for archivo in archivos:
        doc = Document(archivo)
        for p in doc.paragraphs:
            if p.text.strip():
                texto_total += p.text + "\n"
        for tabla in doc.tables:
            for fila in tabla.rows:
                texto_total += " | ".join(celda.text.strip() for celda in fila.cells) + "\n"
    return texto_total

def crear_word_descargable(contenido_texto):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)
    for linea in contenido_texto.split('\n'):
        doc.add_paragraph(linea)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- INTERFAZ ---
st.set_page_config(page_title="Licitador Pro", layout="wide", page_icon="⚖️")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_actual' not in st.session_state: st.session_state.anexo_actual = 1
if 'historial_datos' not in st.session_state: st.session_state.historial_datos = {}
if 'texto_bases' not in st.session_state: st.session_state.texto_bases = ""

st.title("⚖️ Asistente de Licitaciones")

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases")
    archivo = st.file_uploader("Cargar archivo .docx", type=["docx"])
    if archivo and st.button("Analizar Documento"):
        with st.spinner("Procesando archivos..."):
            st.session_state.texto_bases = extraer_contenido_completo([archivo])
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: SELECCIÓN DE ANEXO ---
elif st.session_state.paso == 2:
    n = st.session_state.anexo_actual
    st.header(f"2️⃣ Validación: ANEXO N° {n}")
    
    if f'opciones_n{n}' not in st.session_state:
        with st.spinner(f"Buscando versiones del Anexo {n}..."):
            prompt_check = (
                f"Busca en el texto todas las versiones del 'ANEXO N° {n}'. "
                "Si hay varias (Individual vs Consorcio), devuelve los nombres separados por punto y coma (;). "
                "Si solo hay una, responde 'Versión Única'."
            )
            res_raw = model.generate_content([prompt_check, st.session_state.texto_bases]).text
            if "Única" in res_raw:
                st.session_state[f'opciones_n{n}'] = [f"ANEXO N° {n} (Único)"]
            else:
                st.session_state[f'opciones_n{n}'] = [opt.strip().replace("*", "") for opt in res_raw.split(';') if "ANEXO" in opt.upper()]

    opcion_elegida = st.selectbox("Seleccione la versión:", st.session_state[f'opciones_n{n}'])

    if st.button("Confirmar Formato"):
        st.session_state.anexo_nombre_especifico = opcion_elegida
        st.session_state.paso = 3
        st.rerun()

# --- PASO 3: FORMULARIO (CORREGIDO) ---
elif st.session_state.paso == 3:
    st.header(f"3️⃣ Datos para: {st.session_state.anexo_nombre_especifico}")
    
    if 'campos_actuales' not in st.session_state:
        with st.spinner("Detectando campos..."):
            prompt_campos = (
                f"Analiza el '{st.session_state.anexo_nombre_especifico}'. Lista los campos vacíos "
                "(tablas, [ ], ....) separados por comas, sin explicaciones."
            )
            res = model.generate_content([prompt_campos, st.session_state.texto_bases])
            st.session_state.campos_actuales = [c.strip().replace("*", "") for c in res.text.split(',') if c.strip()]

    # El formulario debe contener TODO, incluido el botón
    with st.form(key=f"form_anexo_{st.session_state.anexo_actual}"):
        nuevas_respuestas = {}
        cols = st.columns(2)
        
        for i, campo in enumerate(st.session_state.campos_actuales):
            with cols[i % 2]:
                valor_previo = st.session_state.historial_datos.get(campo, "")
                # Usamos una KEY única combinando el nombre del anexo y el campo para evitar Duplicados
                clave_input = f"{st.session_state.anexo_nombre_especifico}_{campo}_{i}"
                
                if "MYPE" in campo.upper():
                    nuevas_respuestas[campo] = st.selectbox(campo, ["NO", "SÍ"], index=0 if valor_previo != "SÍ" else 1, key=clave_input)
                else:
                    nuevas_respuestas[campo] = st.text_input(campo, value=valor_previo, key=clave_input)
        
        # Botón de envío indispensable dentro del bloque 'with st.form'
        submit_button = st.form_submit_button(label="Generar Documento")

    if submit_button:
        st.session_state.respuestas_del_momento = nuevas_respuestas
        st.session_state.historial_datos.update(nuevas_respuestas)
        st.session_state.paso = 4
        st.rerun()

# --- PASO 4: RESULTADO ---
elif st.session_state.paso == 4:
    st.header(f"4️⃣ Resultado: {st.session_state.anexo_nombre_especifico}")
    
    if 'resultado_texto' not in st.session_state:
        with st.spinner("Redactando..."):
            datos_str = "\n".join([f"{k}: {v}" for k, v in st.session_state.respuestas_del_momento.items()])
            prompt_redactar = (
                f"Redacta el {st.session_state.anexo_nombre_especifico} completo. "
                f"DATOS: {datos_str}. ESTRUCTURA: {st.session_state.texto_bases}. "
                "REGLAS: Recrea las tablas, no dejes corchetes, marca MYPE con (X)."
            )
            st.session_state.resultado_texto = model.generate_content(prompt_redactar).text

    st.text_area("Vista Previa:", st.session_state.resultado_texto, height=400)
    
    word_bin = crear_word_descargable(st.session_state.resultado_texto)
    st.download_button(label="⬇️ Descargar Word", data=word_bin, file_name=f"Anexo_{st.session_state.anexo_actual}.docx")
    
    if st.button("Siguiente Anexo ➡️"):
        st.session_state.anexo_actual += 1
        # Limpiar estados específicos
        if 'campos_actuales' in st.session_state: del st.session_state.campos_actuales
        if 'resultado_texto' in st.session_state: del st.session_state.resultado_texto
        st.session_state.paso = 2
        st.rerun()
