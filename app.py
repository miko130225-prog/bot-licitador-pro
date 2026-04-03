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
st.set_page_config(page_title="Licitador Pro", layout="wide")
st.title("⚖️ Asistente de Licitaciones: Entrevista Contextual")

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

# PASO 2: IDENTIFICAR VARIANTES
elif st.session_state.paso == 2:
    num = st.session_state.anexo_n
    st.subheader(f"Anexo Actual: N° {num}")
    
    with st.spinner(f"Buscando modelos del Anexo {num}..."):
        prompt_v = (
            f"Analiza el texto y detecta cuántos modelos diferentes existen para el 'ANEXO N° {num}'. "
            f"Instrucción del usuario: {st.session_state.feedback_actual}. "
            "Si hay varios, lístalos por nombre descriptivo separados por ';'. "
            "Si es único, responde estrictamente: UNICA."
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
            seleccion = st.radio(f"Variantes para el Anexo {num}:", opciones)
            if st.button("Elegir esta variante"):
                st.session_state.version_elegida = seleccion
                st.session_state.paso = 3
                st.rerun()
        with col_corr:
            st.info("¿Ajuste complementario?")
            txt_fb = st.text_area("Observación:")
            if st.button("Registrar"):
                st.session_state.feedback_actual = txt_fb
                st.rerun()

# PASO 3: ENTREVISTA CONTEXTUAL (PÁRRAFO + INPUT)
elif st.session_state.paso == 3:
    st.subheader(f"Completando: {st.session_state.version_elegida}")
    num = st.session_state.anexo_n

    if 'bloques_contextuales' not in st.session_state:
        with st.spinner("Preparando entrevista contextual..."):
            prompt_c = (
                f"Extrae el texto íntegro de la variante '{st.session_state.version_elegida}'. "
                "Mantén los párrafos originales pero identifica cada sección a completar: "
                "etiquetas como [CONSIGNAR...], [DATOS...], y también los puntos suspensivos [.......]. "
                "Devuelve el texto estructurado de modo que yo pueda identificar las etiquetas."
            )
            res_c = model.generate_content([prompt_c, st.session_state.raw_text]).text
            
            # Identificamos todo lo que esté en corchetes que no sea solo puntos basura
            # Pero permitimos puntos suspensivos si el usuario los pidió como campo.
            encontrados = re.findall(r'\[[^\]]+\]', res_c)
            st.session_state.campos_contexto = [c for c in encontrados if not all(char in " ._…[]" for char in c[1:-1]) or "..." in c]
            st.session_state.texto_referencia = res_c

    st.info("Complete los datos directamente en el flujo del párrafo:")
    
    with st.form(key=f"form_contextual_{num}"):
        # Mostramos el párrafo de referencia con el estilo solicitado
        st.markdown("### Borrador de Redacción")
        
        # Mostramos el texto segmentado con inputs
        # Nota: Para evitar saturar la UI, presentamos los inputs de forma ordenada
        respuestas = {}
        for i, campo in enumerate(st.session_state.campos_contexto):
            val_prev = st.session_state.memoria_datos.get(campo, "")
            # Creamos el label del input con el texto original del corchete
            respuestas[campo] = st.text_input(f"Dato para: {campo}", value=val_prev, key=f"ctx_{num}_{i}")
        
        st.markdown("---")
        if st.form_submit_button("Generar Anexo Final"):
            st.session_state.memoria_datos.update(respuestas)
            with st.spinner("Redactando..."):
                # Reemplazo final
                texto_final = st.session_state.texto_referencia
                for campo, valor in respuestas.items():
                    texto_final = texto_final.replace(campo, valor if valor else campo)
                
                prompt_f = (
                    f"Toma este texto con datos llenos: {texto_final}. "
                    "Asegúrate de que el formato sea idéntico a las bases originales. "
                    "Elimina cualquier corchete restante y limpia la redacción."
                )
                st.session_state.docx_final = model.generate_content(prompt_f).text
                st.session_state.paso = 4
                st.rerun()

# PASO 4: RESULTADO
elif st.session_state.paso == 4:
    st.success(f"¡{st.session_state.version_elegida} generado!")
    st.text_area("Vista previa:", st.session_state.docx_final, height=400)
    
    st.download_button("⬇️ Descargar Word", 
                       data=exportar_word(st.session_state.docx_final), 
                       file_name=f"{st.session_state.version_elegida}.docx")
    
    if st.button("Ir al Siguiente Anexo ➡️"):
        st.session_state.anexo_n += 1
        st.session_state.feedback_actual = ""
        for k in ['campos_contexto', 'texto_referencia', 'version_elegida', 'docx_final', 'bloques_contextuales']:
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
