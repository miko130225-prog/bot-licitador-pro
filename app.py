import streamlit as st
import asyncio
from putergenai import PuterClient  # El puente gratuito
from PyPDF2 import PdfReader

# Configuración de la interfaz
st.set_page_config(page_title="Licitador Pro Gratis", page_icon="⚖️")
st.title("🤖 Analista de Licitaciones (Modo Puter)")

# Función para leer el PDF
def leer_pdf(file):
    reader = PdfReader(file)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    return texto

# Lógica de la IA con Puter (Sin Tarjeta/API Key)
async def consultar_ia(prompt_sistema, texto_bases):
    async with PuterClient() as client:
        # Puter nos da acceso a Gemini 2.5 Flash gratis
        respuesta = await client.ai_chat(
            prompt=f"{prompt_sistema}\n\nBASES ADJUNTAS:\n{texto_bases}",
            options={"model": "gemini-2.5-flash"}
        )
        return respuesta

# --- INTERFAZ DEL USUARIO ---
archivos = st.file_uploader("Carga las bases en PDF", type="pdf", accept_multiple_files=True)

if archivos:
    texto_completo = ""
    for f in archivos:
        texto_completo += leer_pdf(f)
    
    st.success("Bases leídas. ¿Cómo quieres proceder?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Identificar Perfil (Natural/Jurídica)"):
            instruccion = "Analiza las bases y dime qué preguntas de decisión (Persona Natural o Jurídica) debo responder para armar el expediente."
            with st.spinner("Analizando lógica legal..."):
                res = asyncio.run(consultar_ia(instruccion, texto_completo))
                st.markdown(res)
                
    with col2:
        perfil = st.selectbox("Selecciona tu perfil una vez decidido:", ["Persona Natural", "Persona Jurídica"])
        if st.button("Generar Lista de Documentos"):
            instruccion = f"Soy {perfil}. Según las bases, dime exactamente qué documentos debo preparar hoy mismo."
            with st.spinner("Extrayendo requisitos..."):
                res = asyncio.run(consultar_ia(instruccion, texto_completo))
                st.write(res)
