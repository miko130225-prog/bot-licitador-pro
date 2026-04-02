import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO
import re

# --- CONFIGURACIÓN DE IA ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets de Streamlit.")

# --- FUNCIONES DE EXTRACCIÓN ---
def extraer_todo_el_contenido(archivos):
    texto = ""
    for arc in archivos:
        doc = Document(arc)
        for p in doc.paragraphs:
            texto += p.text + "\n"
        for tabla in doc.tables:
            for fila in tabla.rows:
                texto += " | ".join(celda.text.strip() for celda in fila.cells) + "\n"
    return texto

def crear_word_final(contenido):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(10)
    for linea in contenido.split('\n'):
        doc.add_paragraph(linea)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- INTERFAZ ---
st.set_page_config(page_title="Licitador Pro: Flujo de Anexos", layout="wide")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_actual' not in st.session_state: st.session_state.anexo_actual = 1
if 'historial_datos' not in st.session_state: st.session_state.historial_datos = {}

st.title("⚖️ Gestor de Anexos: Llenado de Tablas y Formatos")
st.markdown("---")

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Documentación")
    archivo = st.file_uploader("Sube las Bases Integradas (Word)", type=["docx"])
    if archivo and st.button("Analizar Documento"):
        with st.spinner("Leyendo estructura completa..."):
            st.session_state.texto_bases = extraer_todo_el_contenido([archivo])
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: DIFERENCIAL DE ANEXOS ---
elif st.session_state.paso == 2:
    n = st.session_state.anexo_actual
    st.header(f"2️⃣ Validación de Anexo N° {n}")
    
    # Preguntamos a la IA si hay duplicados
    with st.spinner(f"Verificando si existen versiones del Anexo {n}..."):
        prompt_check = (
            f"En estas bases, ¿cuántas versiones existen del 'ANEXO N° {n}'? "
            "A veces hay uno para individual y otro para consorcio. "
            "Responde con los nombres exactos o diferencias entre ellos. "
            "Si solo hay uno, di 'Único'."
        )
        res_check = model.generate_content([prompt_check, st.session_state.texto_bases]).text
    
    st.write(f"**Análisis de las Bases:** {res_check}")
    
    if "Único" not in res_check:
        opcion = st.selectbox("Se detectaron varias opciones. ¿Cuál desea completar?", 
                              res_check.split('\n'))
    else:
        opcion = f"Anexo N° {n}"

    if st.button("Confirmar e Iniciar Entrevista"):
        st.session_state.anexo_nombre_especifico = opcion
        st.session_state.paso = 3
        st.rerun()

# --- PASO 3: ENTREVISTA TOTAL (TABLAS + CORCHETES) ---
elif st.session_state.paso == 3:
    st.header(f"3️⃣ Formulario para: {st.session_state.anexo_nombre_especifico}")
    
    if 'campos_detectados' not in st.session_state:
        with st.spinner("Detectando tablas y campos en blanco..."):
            prompt_entrevista = (
                f"Analiza el '{st.session_state.anexo_nombre_especifico}' en las bases. "
                "Genera una lista de TODOS los datos que el usuario debe completar: "
                "1. Campos de las tablas (ej: RUC, Domicilio, MYPE). "
                "2. Textos entre corchetes [ ]. "
                "3. Líneas de puntos ........ "
                "Devuelve solo los nombres de los campos separados por comas."
            )
            res = model.generate_content([prompt_entrevista, st.session_state.texto_bases])
            st.session_state.campos_detectados = res.text.split(',')

    with st.form("entrevista_total"):
        st.info("Complete todos los campos del formato oficial:")
        respuestas_anexo = {}
        cols = st.columns(2)
        for i, campo in enumerate(st.session_state.campos_detectados):
            c = campo.strip()
            if c:
                with cols[i % 2]:
                    if "MYPE" in c.upper():
                        respuestas_anexo[c] = st.selectbox(c, ["NO", "SÍ"])
                    else:
                        respuestas_anexo[c] = st.text_input(c)
        
        if st.form_submit_button("Generar Word y Pasar al Siguiente"):
            with st.spinner("Redactando y llenando tablas..."):
                # Concatenamos historial para que la IA no olvide datos previos
                contexto_datos = str(st.session_state.historial_datos) + "\nNuevos: " + str(respuestas_anexo)
                
                prompt_redactar = (
                    f"Redacta el {st.session_state.anexo_nombre_especifico} completo. "
                    f"USA ESTE FORMATO DE TABLA Y TEXTO: {st.session_state.texto_bases}. "
                    f"DATOS A LLENAR: {contexto_datos}. "
                    "REGLAS: "
                    "1. No dejes corchetes [ ] ni líneas de puntos. "
                    "2. RECREA LA TABLA DE DATOS AL INICIO con la información del usuario. "
                    "3. Marca con (X) donde corresponda según las respuestas (ej. MYPE)."
                )
                st.session_state.resultado_actual = model.generate_content(prompt_redactar).text
                # Guardamos datos para que no los vuelva a pedir si son comunes
                st.session_state.historial_datos.update(respuestas_anexo)
                st.session_state.paso = 4
                st.rerun()

# --- PASO 4: RESULTADO Y TRANSICIÓN ---
elif st.session_state.paso == 4:
    st.header(f"4️⃣ Resultado: {st.session_state.anexo_nombre_especifico}")
    st.text_area("Vista previa profesional:", st.session_state.resultado_actual, height=400)
    
    word_bin = crear_word_final(st.session_state.resultado_actual)
    st.download_button(f"⬇️ Descargar {st.session_state.anexo_nombre_especifico} (.docx)", 
                       data=word_bin, file_name=f"{st.session_state.anexo_nombre_especifico}.docx")
    
    st.markdown("---")
    if st.button("Ir al Siguiente Anexo ➡️"):
        st.session_state.anexo_actual += 1
        # Limpiar datos específicos del paso previo
        del st.session_state.campos_detectados
        st.session_state.paso = 2
        st.rerun()

    if st.button("⬅️ Corregir datos"):
        st.session_state.paso = 3
        st.rerun()
