import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# --- CONFIGURACIÓN ---
MODELO_TÉCNICO = 'gemini-2.5-flash-lite'

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODELO_TÉCNICO)
except Exception as e:
    st.error("Error: Configura la API Key en los Secrets.")

st.set_page_config(page_title="Licitador Pro - Selección de Perfil", page_icon="⚖️", layout="wide")

# --- LÓGICA DE PERSISTENCIA (SESSION STATE) ---
if 'perfil_usuario' not in st.session_state:
    st.session_state.perfil_usuario = None

def extraer_contenido_pdf(archivos):
    texto_total = ""
    for archivo in archivos:
        try:
            lector = PdfReader(archivo)
            for pagina in lector.pages:
                texto_total += pagina.extract_text() + "\n"
        except Exception as e:
            st.error(f"Error al leer {archivo.name}: {e}")
    return texto_total

st.title("⚖️ Analista y Generador de Licitaciones")
st.markdown("---")

col_archivo, col_resultados = st.columns([1, 2])

with col_archivo:
    st.header("📂 1. Cargar Bases")
    archivos_subidos = st.file_uploader("Subir Bases (PDF)", type="pdf", accept_multiple_files=True)
    
    if archivos_subidos:
        with st.spinner("Procesando bases..."):
            contexto_legal = extraer_contenido_pdf(archivos_subidos)
        st.success("Bases cargadas correctamente.")

with col_resultados:
    st.header("📝 2. Definir Perfil de Postulación")
    
    if archivos_subidos:
        # BOTÓN DE ANÁLISIS INICIAL
        if st.button("🔍 Analizar Requisitos de las Bases"):
            prompt_perfil = (
                "Analiza estas bases y dime brevemente: 1. ¿Quién puede postular? 2. ¿Qué documentos piden? "
                "Sé directo para que el usuario pueda elegir su perfil a continuación."
            )
            with st.spinner("Analizando..."):
                try:
                    respuesta = model.generate_content([prompt_perfil, contexto_legal])
                    st.info(respuesta.text)
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        
        # AQUÍ ESTÁ EL CAMBIO: Selector de Perfil para el Usuario
        st.subheader("🎯 Define tu Perfil para generar documentos")
        perfil_elegido = st.radio(
            "Selecciona cómo te presentarás a esta licitación:",
            ["No definido", "Persona Natural", "Persona Jurídica (Empresa Nacional)", "Persona Jurídica (Extranjera)", "Consorcio"],
            index=0
        )

        if perfil_elegido != "No definido":
            st.session_state.perfil_usuario = perfil_elegido
            st.success(f"Perfil configurado como: **{perfil_elegido}**")
            
            # BOTÓN DINÁMICO: Generar Check-list específico
            if st.button(f"📋 Generar Lista de Documentos para {perfil_elegido}"):
                prompt_especifico = (
                    f"El usuario ha decidido postular como **{perfil_elegido}**. "
                    f"Basado en las bases leídas, genera la lista EXACTA de documentos que debe preparar "
                    f"esta persona/entidad. No menciones requisitos de otros perfiles."
                )
                with st.spinner("Filtrando requisitos para tu perfil..."):
                    res = model.generate_content([prompt_especifico, contexto_legal])
                    st.warning(f"### Documentos Obligatorios para {perfil_elegido}")
                    st.markdown(res.text)

            # BOTÓN PARA GENERAR ANEXO (Simulación de texto)
            if st.button(f"✍️ Redactar Borrador de Anexo 1 ({perfil_elegido})"):
                prompt_anexo = (
                    f"Redacta un borrador del Anexo 1 (Datos del Postor) adaptado para **{perfil_elegido}** "
                    f"siguiendo el formato de las bases. Deja espacios en blanco [ ] donde el usuario deba completar su RUC, Nombre, etc."
                )
                with st.spinner("Redactando borrador legal..."):
                    res = model.generate_content([prompt_anexo, contexto_legal])
                    st.code(res.text, language="text")
    else:
        st.info("Sube las bases para habilitar la selección de perfil.")

st.markdown("---")
st.caption("Filtro dinámico de perfil legal | Modelo: Gemini 2.5 Flash-Lite")
