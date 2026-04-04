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
    for line in texto.split('\n'):
        p = doc.add_paragraph(line)
        p.style.font.name = 'Arial'
        p.style.font.size = Pt(10)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# --- INTERFAZ ---
st.set_page_config(page_title="Licitador Pro - Validación Estricta", layout="wide")
st.title("⚖️ Asistente de Licitaciones")

# Inicialización de estados
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'intentos_ajuste' not in st.session_state: st.session_state.intentos_ajuste = 0
if 'memoria_datos' not in st.session_state: st.session_state.memoria_datos = {}
if 'feedback_actual' not in st.session_state: st.session_state.feedback_actual = ""

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases Integradas (.docx)", type="docx")
    if archivo and st.button("Analizar Documento"):
        with st.spinner("Leyendo archivo..."):
            st.session_state.raw_text = obtener_texto_completo(archivo)
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: IDENTIFICACIÓN Y CONFIRMACIÓN OBLIGATORIA ---
elif st.session_state.paso == 2:
    num = st.session_state.anexo_n
    st.header(f"Validación de ANEXO N° {num}")
    
    # Control de errores: Bloqueo tras 2 intentos fallidos de ajuste
    if st.session_state.intentos_ajuste >= 2:
        st.error("⚠️ Se han detectado dificultades técnicas persistentes para identificar las variantes de este anexo.")
        st.info("Por favor, **comuníquese con soporte técnico** para procesar este anexo de forma manual.")
        if st.button("Reiniciar desde el inicio"):
            for key in st.session_state.keys(): del st.session_state[key]
            st.rerun()
    else:
        with st.spinner(f"Buscando formatos para el Anexo {num}..."):
            prompt_v = (
                f"Busca en las bases todas las versiones del 'ANEXO N° {num}'. "
                f"Ajuste previo del usuario: {st.session_state.feedback_actual}. "
                "Para cada variante, extrae el nombre completo (ej: ANEXO N° 1 - Persona Jurídica). "
                "Responde listando las variantes separadas por ';'. "
                "Si solo hay una variante, lístala de igual forma."
            )
            res_v = model.generate_content([prompt_v, st.session_state.raw_text]).text
            opciones = [o.strip().replace("*", "") for o in res_v.split(';') if len(o) > 5]
        
        col_sel, col_corr = st.columns([2, 1])
        
        with col_sel:
            if opciones:
                st.markdown(f"##### Se han encontrado {len(opciones)} variante(s) para el Anexo {num}:")
                seleccion = st.radio("Seleccione el modelo a completar:", opciones, key=f"radio_n{num}")
                
                if st.button(f"Confirmar y empezar a llenar {num}"):
                    st.session_state.version_elegida = seleccion
                    st.session_state.paso = 3
                    st.session_state.intentos_ajuste = 0 # Reset al éxito
                    st.rerun()
            else:
                st.warning("No se pudieron identificar variantes automáticamente.")

        with col_corr:
            st.info("¿La información es incorrecta?")
            txt_fb = st.text_area("Describa qué anexos faltan o sobran:", key=f"fb_n{num}")
            if st.button("Registrar Observación y Reintentar"):
                st.session_state.feedback_actual = txt_fb
                st.session_state.intentos_ajuste += 1
                st.rerun()

# --- PASO 3: LLENADO CONTEXTUAL ---
elif st.session_state.paso == 3:
    num = st.session_state.anexo_n
    st.header(f"Completando: {st.session_state.version_elegida}")

    if 'campos_contexto' not in st.session_state:
        with st.spinner("Extrayendo estructura del párrafo..."):
            prompt_c = f"Extrae el texto completo del '{st.session_state.version_elegida}'. Identifica etiquetas [CONSIGNAR...]."
            res_c = model.generate_content([prompt_c, st.session_state.raw_text]).text
            encontrados = re.findall(r'\[[^\]]+\]', res_c)
            st.session_state.campos_contexto = [c for c in encontrados if any(char.isalpha() for char in c)]
            st.session_state.texto_referencia = res_c

    with st.form(key=f"form_ctx_{num}"):
        respuestas = {}
        for i, campo in enumerate(st.session_state.campos_contexto):
            val_prev = st.session_state.memoria_datos.get(campo, "")
            respuestas[campo] = st.text_input(f"Dato para {campo}:", value=val_prev, key=f"inp_{num}_{i}")
        
        if st.form_submit_button("✅ Generar Anexo Final"):
            st.session_state.memoria_datos.update(respuestas)
            with st.spinner("Redactando..."):
                texto_final = st.session_state.texto_referencia
                for tag, valor in respuestas.items():
                    if valor: texto_final = texto_final.replace(tag, valor)
                
                st.session_state.docx_final = model.generate_content(f"Limpia este texto legal: {texto_final}").text
                st.session_state.paso = 4
                st.rerun()

# --- PASO 4: RESULTADO ---
elif st.session_state.paso == 4:
    st.success("¡Anexo generado!")
    st.text_area("Vista previa:", st.session_state.docx_final, height=400)
    
    doc_bin = exportar_word(st.session_state.docx_final)
    st.download_button("⬇️ Descargar Word", data=doc_bin, file_name=f"Anexo_{st.session_state.anexo_n}.docx")
    
    if st.button(f"Pasar al Siguiente Anexo ➡️"):
        st.session_state.anexo_n += 1
        st.session_state.feedback_actual = ""
        st.session_state.intentos_ajuste = 0
        for k in ['campos_contexto', 'texto_referencia', 'version_elegida', 'docx_final']:
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
