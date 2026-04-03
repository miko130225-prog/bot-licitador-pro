import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from io import BytesIO
import time

# --- CONFIGURACIÓN DE IA ---
# Se utiliza gemini-2.5-flash-lite para optimizar la velocidad y latencia
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets de Streamlit (GEMINI_API_KEY).")

# --- FUNCIONES DE SOPORTE TÉCNICO ---
def extraer_contenido_completo(archivos):
    """Extrae texto de párrafos y celdas de tablas para no perder la estructura de los anexos."""
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
    """Genera un archivo .docx con formato profesional Arial 10."""
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)
    
    for linea in contenido_texto.split('\n'):
        if linea.strip():
            doc.add_paragraph(linea)
        else:
            doc.add_paragraph("") # Mantener espaciado
            
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- CONFIGURACIÓN DE INTERFAZ Y ESTADOS ---
st.set_page_config(page_title="Licitador Pro - Generador de Anexos", layout="wide", page_icon="⚖️")

if 'paso' not in st.session_state: st.session_state.paso = 1
if 'anexo_actual' not in st.session_state: st.session_state.anexo_actual = 1
if 'historial_datos' not in st.session_state: st.session_state.historial_datos = {}
if 'texto_bases' not in st.session_state: st.session_state.texto_bases = ""

st.title("⚖️ Asistente de Licitaciones: Generador de Anexos Oficiales")
st.markdown("---")

# --- PASO 1: CARGA DE DOCUMENTACIÓN ---
if st.session_state.paso == 1:
    st.header("1️⃣ Carga de Bases Integradas")
    st.info("Suba el archivo Word de las bases para identificar los formatos de anexos.")
    archivo = st.file_uploader("Cargar archivo .docx", type=["docx"])
    
    if archivo and st.button("Analizar Documento"):
        with st.spinner("Procesando tablas y formatos..."):
            st.session_state.texto_bases = extraer_contenido_completo([archivo])
            st.session_state.paso = 2
            st.rerun()

# --- PASO 2: SELECCIÓN DE VERSIÓN DE ANEXO ---
elif st.session_state.paso == 2:
    n = st.session_state.anexo_actual
    st.header(f"2️⃣ Validación de Formato: ANEXO N° {n}")
    
    if f'opciones_n{n}' not in st.session_state:
        with st.spinner(f"Buscando versiones del Anexo {n} en las bases..."):
            prompt_check = (
                f"Busca en el texto todas las versiones del 'ANEXO N° {n}'. "
                "Si existen versiones diferentes (ej. para Individual vs para Consorcio), "
                "devuelve solo sus nombres descriptivos separados por punto y coma (;). "
                "Ejemplo: ANEXO N° 1 (Postor Individual) ; ANEXO N° 1 (Consorcio). "
                "Si solo hay una versión, responde 'Versión Única'."
            )
            res_raw = model.generate_content([prompt_check, st.session_state.texto_bases]).text
            
            # Limpieza de opciones para el selector
            if "Única" in res_raw:
                st.session_state[f'opciones_n{n}'] = [f"ANEXO N° {n} (Único)"]
            else:
                # Filtrar solo líneas que mencionen el anexo y limpiar basura narrativa
                opciones = [opt.strip().replace("*", "") for opt in res_raw.split(';') if "ANEXO" in opt.upper()]
                st.session_state[f'opciones_n{n}'] = opciones

    opcion_elegida = st.selectbox(
        "Se detectaron las siguientes versiones. Seleccione la que desea completar:",
        st.session_state[f'opciones_n{n}']
    )

    if st.button("Confirmar Formato y Ver Campos"):
        st.session_state.anexo_nombre_especifico = opcion_elegida
        st.session_state.paso = 3
        st.rerun()

# --- PASO 3: ENTREVISTA DINÁMICA (TABLAS + CORCHETES) ---
elif st.session_state.paso == 3:
    st.header(f"3️⃣ Datos para: {st.session_state.anexo_nombre_especifico}")
    
    if 'campos_actuales' not in st.session_state:
        with st.spinner("Escaneando tablas y espacios en blanco..."):
            prompt_campos = (
                f"Analiza el '{st.session_state.anexo_nombre_especifico}' en las bases. "
                "Genera una lista de TODOS los datos que el usuario debe completar: "
                "1. Campos en tablas (RUC, Domicilio, MYPE, Teléfono, etc.). "
                "2. Textos entre corchetes [ ]. "
                "3. Espacios sobre líneas de puntos .... "
                "Responde solo la lista de campos separada por comas, sin explicaciones."
            )
            res = model.generate_content([prompt_campos, st.session_state.texto_bases])
            st.session_state.campos_actuales = [c.strip().replace("*", "") for c in res.text.split(',')]

    with st.form("form_datos_anexo"):
        st.markdown("##### Ingrese la información requerida:")
        nuevas_respuestas = {}
        cols = st.columns(2)
        
        for i, campo in enumerate(st.session_state.campos_actuales):
            if not campo: continue
            with cols[i % 2]:
                # Recuperar valor si ya se llenó en un anexo previo (Eficiencia)
                valor_previo = st.session_state.historial_datos.get(campo, "")
                
                if "MYPE" in campo.upper():
                    nuevas_respuestas[campo] = st.selectbox(campo, ["NO", "SÍ"], 
                                                           index=0 if valor_previo != "SÍ" else 1)
                else:
                    nuevas_respuestas[campo] = st.text_input(campo, value=valor_previo)
        
        if st.form_submit_button("Generar Documento y Continuar"):
            st.session_state.respuestas_del_momento = nuevas_respuestas
            st.session_state.historial_datos.update(nuevas_respuestas)
            st.session_state.paso = 4
            st.rerun()

# --- PASO 4: RESULTADO, DESCARGA Y TRANSICIÓN ---
elif st.session_state.paso == 4:
    st.header(f"4️⃣ Documento Generado: {st.session_state.anexo_nombre_especifico}")
    
    if 'resultado_texto' not in st.session_state:
        with st.spinner("Redactando anexo oficial..."):
            # Combinamos historial para asegurar que no falte nada
            datos_finales_str = "\n".join([f"{k}: {v}" for k, v in st.session_state.respuestas_del_momento.items()])
            
            prompt_redactar = (
                f"Redacta el {st.session_state.anexo_nombre_especifico} completo. "
                f"DATOS PROPORCIONADOS: {datos_finales_str}. "
                f"ESTRUCTURA DE BASES: {st.session_state.texto_bases}. "
                "INSTRUCCIONES DE FORMATO: "
                "1. Si el anexo original tiene una TABLA DE DATOS (RUC, etc.), RECRÉALA igual. "
                "2. NO dejes corchetes [ ] ni líneas vacías, inserta los datos directamente. "
                "3. Si es MYPE SÍ, marca con una 'X' el paréntesis (X) correspondiente. "
                "4. Mantén el rigor legal y la terminología de las bases."
            )
            st.session_state.resultado_texto = model.generate_content(prompt_redactar).text

    st.text_area("Vista Previa (Formato Texto):", st.session_state.resultado_texto, height=400)
    
    col_dl, col_next = st.columns(2)
    with col_dl:
        doc_bin = crear_word_descargable(st.session_state.resultado_texto)
        st.download_button(
            label=f"⬇️ Descargar {st.session_state.anexo_nombre_especifico} (.docx)",
            data=doc_bin,
            file_name=f"{st.session_state.anexo_nombre_especifico.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    with col_next:
        if st.button("Pasar al Siguiente Anexo ➡️"):
            st.session_state.anexo_actual += 1
            # Limpieza selectiva para el siguiente ciclo
            if 'campos_actuales' in st.session_state: del st.session_state.campos_actuales
            if 'resultado_texto' in st.session_state: del st.session_state.resultado_texto
            if 'opciones_n' + str(st.session_state.anexo_actual-1) in st.session_state: 
                # Opcional: podrías limpiar opciones previas si el archivo es enorme
                pass
            st.session_state.paso = 2
            st.rerun()

    if st.button("⬅️ Editar datos de este anexo"):
        if 'resultado_texto' in st.session_state: del st.session_state.resultado_texto
        st.session_state.paso = 3
        st.rerun()

st.markdown("---")
st.caption("Bot de Licitaciones Pro | Formato fiel a Bases Integradas 2026")
