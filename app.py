import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO
import re

# --- CONFIGURACIÓN ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets.")

def leer_texto_completo(archivos):
    texto = ""
    for arc in archivos:
        doc = Document(arc)
        for p in doc.paragraphs:
            texto += p.text + "\n"
        for tabla in doc.tables:
            for fila in tabla.rows:
                for celda in fila.cells:
                    texto += celda.text + " "
                texto += "\n"
    return texto

def crear_word_profesional(contenido):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(10)
    
    for linea in contenido.split('\n'):
        p = doc.add_paragraph(linea)
    
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

st.set_page_config(page_title="Licitador Pro - Formatos Reales", layout="wide")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_actual' not in st.session_state: st.session_state.anexo_actual = 1

st.title("⚖️ Generador de Anexos: Formato Oficial")

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases")
    archivo = st.file_uploader("Sube el Word de las Bases Integradas", type=["docx"])
    if archivo and st.button("Analizar Estructura de Tablas"):
        st.session_state.texto_bases = leer_texto_completo([archivo])
        st.session_state.paso = 2
        st.rerun()

# --- PASO 2: MODALIDAD ---
elif st.session_state.paso == 2:
    st.header("2️⃣ Modalidad de Postulación")
    modalidad = st.radio("Seleccione escenario:", ["Individual", "Consorcio"])
    if st.button("Confirmar y Buscar Campos de Tabla"):
        st.session_state.modalidad = modalidad
        st.session_state.paso = 3
        st.rerun()

# --- PASO 3: ENTREVISTA DETALLADA ---
elif st.session_state.paso == 3:
    n = st.session_state.anexo_actual
    st.header(f"3️⃣ Datos para el ANEXO N° {n}")
    
    if f'campos_n{n}' not in st.session_state:
        with st.spinner("Escaneando tablas y espacios en blanco..."):
            prompt = (
                f"Analiza el ANEXO {n} para {st.session_state.modalidad} en estas bases. "
                "Identifica TODOS los campos, incluyendo los de la tabla (RUC, Domicilio, MYPE, etc.) "
                "y los espacios del cuerpo del texto. Responde solo los nombres separados por comas."
            )
            res = model.generate_content([prompt, st.session_state.texto_bases])
            st.session_state[f'campos_n{n}'] = res.text.split(',')

    with st.form(f"f_{n}"):
        respuestas = {}
        # Dividimos en columnas para que no sea una lista infinita
        cols = st.columns(2)
        for i, campo in enumerate(st.session_state[f'campos_n{n}']):
            c = campo.strip()
            if c:
                with cols[i % 2]:
                    # Manejo especial para MYPE
                    if "MYPE" in c.upper():
                        respuestas[c] = st.selectbox(c, ["NO", "SÍ"])
                    else:
                        respuestas[c] = st.text_input(c)
        
        if st.form_submit_button("Generar Anexo con Formato"):
            with st.spinner("Construyendo documento..."):
                datos_ctx = "\n".join([f"{k}: {v}" for k, v in respuestas.items()])
                prompt_final = (
                    f"Redacta el ANEXO {n} para {st.session_state.modalidad}. "
                    f"DATOS DEL USUARIO: {datos_ctx}. "
                    f"ESTRUCTURA ORIGINAL: {st.session_state.texto_bases}. "
                    "INSTRUCCIONES CRÍTICAS: "
                    "1. Mantén la TABLA DE DATOS al inicio si existe en las bases. "
                    "2. Si es MYPE SI, marca con una 'X' el paréntesis (X). "
                    "3. Usa un lenguaje formal y legal. No inventes datos, usa solo los provistos."
                )
                st.session_state[f"res_n{n}"] = model.generate_content(prompt_final).text
                st.rerun()

    if f"res_n{n}" in st.session_state:
        st.info("### Previsualización del Documento")
        st.text(st.session_state[f"res_n{n}"])
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.download_button("⬇️ Descargar Anexo en Word", 
                             data=crear_word_profesional(st.session_state[f"res_n{n}"]), 
                             file_name=f"Anexo_{n}.docx")
        with btn_col2:
            if st.button("Siguiente Anexo ➡️"):
                st.session_state.anexo_actual += 1
                st.rerun()
