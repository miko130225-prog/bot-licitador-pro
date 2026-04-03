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
def obtener_texto_completo(archivo):
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

# --- INTERFAZ ---
st.set_page_config(page_title="Licitador Pro: Flujo Secuencial", layout="wide")
st.title("⚖️ Asistente de Licitaciones: Llenado de Anexos")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'memoria_datos' not in st.session_state: st.session_state.memoria_datos = {}
if 'feedback_actual' not in st.session_state: st.session_state.feedback_actual = ""

# PASO 1: CARGA
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases Integradas para iniciar (.docx)", type="docx")
    if archivo and st.button("Comenzar con el Anexo N° 1"):
        with st.spinner("Analizando bases..."):
            st.session_state.raw_text = obtener_texto_completo(archivo)
            st.session_state.paso = 2
            st.rerun()

# PASO 2: IDENTIFICAR VARIANTES DEL ANEXO ACTUAL
elif st.session_state.paso == 2:
    num = st.session_state.anexo_n
    st.subheader(f"Anexo Actual: N° {num}")
    
    with st.spinner(f"Buscando modelos del Anexo {num}..."):
        prompt_v = (
            f"Analiza el texto y detecta cuántos modelos o variantes diferentes existen para el 'ANEXO N° {num}'. "
            f"Toma en cuenta esta instrucción del usuario: {st.session_state.feedback_actual}. "
            "Si hay más de uno (ej. Individual y Consorcio), lístalos separados por ';'. "
            "Si es un modelo único para este número, responde estrictamente: UNICA."
        )
        res_v = model.generate_content([prompt_v, st.session_state.raw_text]).text
    
    if "UNICA" in res_v.upper() and not st.session_state.feedback_actual:
        st.session_state.version_elegida = f"ANEXO N° {num}"
        st.session_state.paso = 3
        st.rerun()
    else:
        opciones = [o.strip().replace("*", "") for o in res_v.split(';') if len(o) > 5]
        
        col_sel, col_corr = st.columns([2, 1])
        with col_sel:
            seleccion = st.radio(f"Se han identificado estas variantes para el Anexo {num}. Selecciona una:", opciones)
            if st.button("Elegir esta variante"):
                st.session_state.version_elegida = seleccion
                st.session_state.paso = 3
                st.rerun()
        with col_corr:
            st.info("¿El bot detectó mal las variantes?")
            txt_fb = st.text_area("Explica el error (ej: 'Solo hay 2 modelos de Anexo 1, el tercero no existe'):")
            if st.button("Corregir Detección"):
                st.session_state.feedback_actual = txt_fb
                st.rerun()

# PASO 3: ENTREVISTA DE CAMPOS (SOLO DEL MODELO ELEGIDO)
elif st.session_state.paso == 3:
    st.subheader(f"Completando: {st.session_state.version_elegida}")
    num = st.session_state.anexo_n

    if 'campos_modelo' not in st.session_state:
        with st.spinner("Extrayendo solo los campos de esta variante..."):
            prompt_c = (
                f"Dentro de las bases, ubica la sección del '{st.session_state.version_elegida}'. "
                "Identifica TODOS los campos vacíos, tablas con datos faltantes, corchetes [...] y líneas de puntos .... "
                "Lista los nombres de estos campos separados por comas. No expliques nada."
            )
            res_c = model.generate_content([prompt_c, st.session_state.raw_text]).text
            st.session_state.campos_modelo = [c.strip() for c in res_c.split(',') if c.strip()]

    with st.form(key=f"form_anexo_{num}"):
        respuestas = {}
        c1, c2 = st.columns(2)
        for i, campo in enumerate(st.session_state.campos_modelo):
            target = c1 if i % 2 == 0 else c2
            # Autocompletado si el dato ya existe en la memoria (ej. RUC)
            val_prev = st.session_state.memoria_datos.get(campo, "")
            with target:
                respuestas[campo] = st.text_input(campo, value=val_prev, key=f"inp_{num}_{i}")
        
        if st.form_submit_button("Finalizar llenado y generar Anexo"):
            st.session_state.memoria_datos.update(respuestas)
            with st.spinner("Generando documento final..."):
                prompt_f = (
                    f"Redacta el {st.session_state.version_elegida} completo. "
                    f"Usa estos datos: {respuestas}. "
                    f"Copia fielmente el formato (tablas y texto) de: {st.session_state.raw_text}. "
                    "Limpia corchetes y líneas, entrega el anexo listo para firmar."
                )
                st.session_state.docx_final = model.generate_content(prompt_f).text
                st.session_state.paso = 4
                st.rerun()

# PASO 4: RESULTADO Y TRANSICIÓN
elif st.session_state.paso == 4:
    st.success(f"¡{st.session_state.version_elegida} generado!")
    st.text_area("Vista previa:", st.session_state.docx_final, height=350)
    
    st.download_button("⬇️ Descargar Anexo en Word", 
                       data=exportar_word(st.session_state.docx_final), 
                       file_name=f"{st.session_state.version_elegida}.docx")
    
    st.markdown("---")
    if st.button("Continuar al siguiente número de Anexo ➡️"):
        # Limpieza de estados del anexo anterior
        st.session_state.anexo_n += 1
        st.session_state.feedback_actual = ""
        for k in ['campos_modelo', 'version_elegida', 'docx_final']:
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
