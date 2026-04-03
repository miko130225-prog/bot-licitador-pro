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
st.set_page_config(page_title="Licitador Pro - GTN", layout="wide")
st.title("⚖️ Asistente de Licitaciones: Llenado Contextual")

# Inicialización de estados
if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_n' not in st.session_state: st.session_state.anexo_n = 1
if 'memoria_datos' not in st.session_state: st.session_state.memoria_datos = {}
if 'feedback_actual' not in st.session_state: st.session_state.feedback_actual = ""

# --- PASO 1: CARGA ---
if st.session_state.paso == 1:
    archivo = st.file_uploader("Sube las Bases Integradas (.docx)", type="docx")
    if archivo and st.button("Iniciar Proceso de Anexos"):
        with st.spinner("Procesando documento..."):
            st.session_state.raw_text = obtener_texto_completo(archivo)
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: IDENTIFICACIÓN OBLIGATORIA DE VARIANTES ---
elif st.session_state.paso == 2:
    num = st.session_state.anexo_n
    st.header(f"Identificación: ANEXO N° {num}")
    
    with st.spinner(f"Buscando variantes para el Anexo {num}..."):
        prompt_v = (
            f"Busca en las bases todas las versiones del 'ANEXO N° {num}'. "
            f"Instrucción del usuario: {st.session_state.feedback_actual}. "
            "Si hay más de una (ej. Individual, Consorcio, Jurídica), lístalas separadas por ';'. "
            "Si es única, responde estrictamente: UNICA."
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
            st.markdown("##### Seleccione el modelo correcto:")
            seleccion = st.radio("Modelos detectados:", opciones, key=f"radio_n{num}")
            if st.button("Confirmar Modelo Seleccionado"):
                st.session_state.version_elegida = seleccion
                st.session_state.paso = 3
                st.rerun()
        
        with col_corr:
            st.info("Ajuste de búsqueda")
            txt_fb = st.text_area("Explique la observación:", key=f"fb_n{num}", placeholder="Ej: Ignora el modelo de consorcio")
            if st.button("Registrar y Reintentar"):
                st.session_state.feedback_actual = txt_fb
                st.rerun()

# --- PASO 3: FORMULARIO CONTEXTUAL (RELLENAR PÁRRAFO) ---
elif st.session_state.paso == 3:
    num = st.session_state.anexo_n
    st.header(f"Llenado Contextual: {st.session_state.version_elegida}")

    if 'campos_contexto' not in st.session_state:
        with st.spinner("Preparando el párrafo de redacción..."):
            prompt_c = (
                f"Extrae el texto exacto del '{st.session_state.version_elegida}'. "
                "Identifica las etiquetas [CONSIGNAR...], [DATOS...], etc. "
                "No resumas, necesito el párrafo legal completo."
            )
            res_c = model.generate_content([prompt_c, st.session_state.raw_text]).text
            
            # Extraemos etiquetas descriptivas, ignoramos puntos [......]
            encontrados = re.findall(r'\[[^\]]+\]', res_c)
            st.session_state.campos_contexto = [c for c in encontrados if any(char.isalpha() for char in c)]
            st.session_state.texto_referencia = res_c

    st.markdown("---")
    st.warning("Complete la información directamente sobre la estructura del párrafo:")

    with st.form(key=f"form_contextual_{num}"):
        respuestas = {}
        
        # Mostramos los campos integrados en la estructura
        st.markdown("#### Estructura del Documento")
        
        # Iteramos sobre los campos para crear los inputs
        for i, campo in enumerate(st.session_state.campos_contexto):
            val_prev = st.session_state.memoria_datos.get(campo, "")
            # Usamos label_visibility="visible" pero con el texto del campo para que el usuario sepa qué poner
            respuestas[campo] = st.text_input(
                f"Complete el espacio para: {campo}", 
                value=val_prev, 
                key=f"inp_{num}_{i}",
                placeholder=f"Escriba aquí la información para {campo}..."
            )
            st.markdown("---") # Separador para simular el avance del párrafo

        if st.form_submit_button("✅ Finalizar y Generar Documento"):
            st.session_state.memoria_datos.update(respuestas)
            with st.spinner("Generando archivo final..."):
                # Reemplazo de etiquetas por valores
                texto_final = st.session_state.texto_referencia
                for tag, valor in respuestas.items():
                    if valor:
                        texto_final = texto_final.replace(tag, valor)
                
                prompt_f = (
                    f"Toma este texto con los datos insertados: {texto_final}. "
                    "Reconstrúyelo respetando el formato de las bases originales. "
                    "Elimina corchetes sobrantes y asegúrate de que sea un documento formal listo."
                )
                st.session_state.docx_final = model.generate_content(prompt_f).text
                st.session_state.paso = 4
                st.rerun()

# --- PASO 4: DESCARGA Y CONTINUACIÓN ---
elif st.session_state.paso == 4:
    st.success(f"Anexo {st.session_state.anexo_n} redactado correctamente.")
    st.text_area("Vista previa del anexo:", st.session_state.docx_final, height=400)
    
    doc_bin = exportar_word(st.session_state.docx_final)
    st.download_button(
        label="⬇️ Descargar Anexo en formato Word", 
        data=doc_bin, 
        file_name=f"Anexo_{st.session_state.anexo_n}_Final.docx"
    )
    
    st.markdown("---")
    proximo = st.session_state.anexo_n + 1
    if st.button(f"Pasar al Anexo N° {proximo} ➡️"):
        st.session_state.anexo_n = proximo
        st.session_state.feedback_actual = ""
        # Limpieza profunda de temporales
        for k in ['campos_contexto', 'texto_referencia', 'version_elegida', 'docx_final']:
            if k in st.session_state: del st.session_state[k]
        st.session_state.paso = 2
        st.rerun()
