import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO
import re

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
st.set_page_config(page_title="Licitador Pro - Flujo Estricto", layout="wide")
st.title("⚖️ Asistente de Licitaciones: Paso a Paso")

# Inicialización de estados
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'memoria_datos' not in st.session_state: st.session_state.memoria_datos = {}
if 'feedback_actual' not in st.session_state: st.session_state.feedback_actual = ""

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases Integradas para iniciar (.docx)", type="docx")
    if archivo and st.button("Iniciar Análisis de Anexos"):
        with st.spinner("Procesando documento..."):
            st.session_state.raw_text = obtener_texto_completo(archivo)
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: IDENTIFICACIÓN OBLIGATORIA DE VARIANTES ---
elif st.session_state.paso == 2:
    num = st.session_state.anexo_n
    st.header(f"Fase de Identificación: ANEXO N° {num}")
    
    with st.spinner(f"Detectando modelos para el Anexo {num}..."):
        prompt_v = (
            f"Busca en las bases todas las versiones del 'ANEXO N° {num}'. "
            f"Instrucción del usuario: {st.session_state.feedback_actual}. "
            "Si hay más de una (ej. Persona Jurídica, Consorcio), lístalas separadas por ';'. "
            "Si es única, responde estrictamente: UNICA."
        )
        res_v = model.generate_content([prompt_v, st.session_state.raw_text]).text
    
    # Solo salta automáticamente si es ÚNICA y NO hay corrección pendiente
    if "UNICA" in res_v.upper() and not st.session_state.feedback_actual:
        st.session_state.version_elegida = f"ANEXO N° {num}"
        st.session_state.paso = 3
        st.rerun()
    else:
        opciones = [o.strip().replace("*", "") for o in res_v.split(';') if len(o) > 5]
        
        col_sel, col_corr = st.columns([2, 1])
        with col_sel:
            st.markdown("##### Seleccione la variante que desea llenar:")
            seleccion = st.radio("Opciones encontradas:", opciones, key=f"radio_n{num}")
            if st.button("Confirmar Selección de Variante"):
                st.session_state.version_elegida = seleccion
                st.session_state.paso = 3
                st.rerun()
        
        with col_corr:
            st.info("¿Ajuste necesario?")
            txt_fb = st.text_area("Explique la observación (ej: 'Solo existen 2 modelos de Anexo 1'):", key=f"fb_n{num}")
            if st.button("Registrar y Reanalizar"):
                st.session_state.feedback_actual = txt_fb
                st.rerun()

# --- PASO 3: ENTREVISTA CONTEXTUAL ---
elif st.session_state.paso == 3:
    num = st.session_state.anexo_n
    st.header(f"Completando: {st.session_state.version_elegida}")

    if 'campos_contexto' not in st.session_state:
        with st.spinner("Analizando texto para la entrevista..."):
            prompt_c = (
                f"Extrae el texto completo de la variante '{st.session_state.version_elegida}'. "
                "Identifica las etiquetas a llenar como [CONSIGNAR...], [DATOS...], etc. "
                "Devuelve el fragmento de texto para referencia y la lista de etiquetas."
            )
            res_c = model.generate_content([prompt_c, st.session_state.raw_text]).text
            
            # Buscamos corchetes con contenido descriptivo (ej. [CONSIGNAR CIUDAD])
            # Ignoramos basura como [.........]
            encontrados = re.findall(r'\[[^\]]+\]', res_c)
            st.session_state.campos_contexto = [c for c in encontrados if any(char.isalpha() for char in c)]
            st.session_state.texto_referencia = res_c

    st.markdown("---")
    st.info("Complete la información solicitada para este formato:")
    
    with st.form(key=f"form_ctx_{num}"):
        respuestas = {}
        # Mostramos los campos de forma organizada
        c1, c2 = st.columns(2)
        for i, campo in enumerate(st.session_state.campos_contexto):
            col_target = c1 if i % 2 == 0 else c2
            val_prev = st.session_state.memoria_datos.get(campo, "")
            with col_target:
                respuestas[campo] = st.text_input(f"Dato para {campo}:", value=val_prev, key=f"inp_{num}_{i}")
        
        if st.form_submit_button("Finalizar y Generar Documento"):
            st.session_state.memoria_datos.update(respuestas)
            with st.spinner("Redactando anexo final..."):
                prompt_f = (
                    f"Redacta el {st.session_state.version_elegida} completo. "
                    f"Usa estos datos: {respuestas}. "
                    f"Asegúrate de que el formato sea idéntico a: {st.session_state.texto_referencia}. "
                    "Elimina todos los corchetes y entrega el texto final limpio."
                )
                st.session_state.docx_final = model.generate_content(prompt_f).text
                st.session_state.paso = 4
                st.rerun()

# --- PASO 4: DESCARGA Y SIGUIENTE ---
elif st.session_state.paso == 4:
    st.success(f"Anexo {st.session_state.anexo_n} generado con éxito.")
    st.text_area("Vista previa:", st.session_state.docx_final, height=400)
    
    doc_bin = exportar_word(st.session_state.docx_final)
    st.download_button("⬇️ Descargar Anexo en Word", data=doc_bin, file_name=f"Anexo_{st.session_state.anexo_n}.docx")
    
    st.markdown("---")
    if st.button("Continuar al siguiente número de Anexo (Anexo N° " + str(st.session_state.anexo_n + 1) + ") ➡️"):
        st.session_state.anexo_n += 1
        st.session_state.feedback_actual = ""
        # Limpiamos estados específicos del anexo terminado
        for k in ['campos_contexto', 'texto_referencia', 'version_elegida', 'docx_final']:
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
