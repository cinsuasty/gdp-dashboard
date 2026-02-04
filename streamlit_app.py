import streamlit as st
import requests
import json
import uuid
import pandas as pd
import time
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Ask DB Agent Chat", page_icon="💬", layout="wide")

# Estilos personalizados
st.markdown(
    """
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .metadata-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
    }
    .query-box {
        background-color: #e8eaf0;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.3rem 0;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .report-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
        border-left: 4px solid #4CAF50;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Inicializar session_state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing_reports" not in st.session_state:
    st.session_state.processing_reports = {}
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False


# Función para obtener el estado de un reporte
def check_report_status(report_id, api_key, base_url="http://localhost:8010"):
    try:
        headers = {"accept": "application/json", "X-API-Key": api_key}
        response = requests.get(
            f"{base_url}/v1/ask-db/reports/{report_id}", headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al verificar reporte {report_id}: {str(e)}")
        return None


# Función para obtener el link de reporte (retorna None o el markdown del link)
def get_report_link(
    report_data,
    message_idx,
    report_idx,
    api_key,
    base_url="http://localhost:8010",
    is_new_message=False,
):
    report_id = report_data.get("report_id")
    status = report_data.get("status")

    if status == "processing":
        # Polling para obtener el estado actualizado
        max_attempts = 3
        attempt = 0
        updated_data = None

        while attempt < max_attempts:
            updated_data = check_report_status(report_id, api_key, base_url)

            if updated_data and updated_data.get("status") == "completed":
                # Actualizar el reporte en el historial solo si el mensaje ya está guardado
                if not is_new_message and message_idx < len(st.session_state.messages):
                    if "reports" in st.session_state.messages[message_idx]:
                        st.session_state.messages[message_idx]["reports"][
                            report_idx
                        ] = updated_data
                return render_completed_report(
                    updated_data, report_id, api_key, base_url
                )
            elif updated_data and updated_data.get("status") == "failed":
                return f"❌ El reporte falló: {updated_data.get('error', 'Error desconocido')}"

            time.sleep(3)
            attempt += 1

        return "⏱️ Reporte en proceso..."

    elif status == "completed":
        return render_completed_report(report_data, report_id, api_key, base_url)

    elif status == "failed":
        return f"❌ El reporte falló: {report_data.get('error', 'Error desconocido')}"

    else:
        return f"Estado del reporte: {status}"


# Función para renderizar un reporte completado (retorna el markdown del link)
def render_completed_report(
    report_data, report_id, api_key, base_url="http://localhost:8010"
):
    download_url = report_data.get("download_url")

    if download_url:
        return f"[📥 Descargar reporte Excel]({download_url})"
    else:
        return "❌ No se encontró la URL de descarga del reporte."


# Título principal
st.title("💬 Ask DB Agent - Chat Conversacional")

# Sidebar para configuración
with st.sidebar:
    st.header("⚙️ Configuración")

    # Configuración del endpoint
    st.subheader("Endpoint")

    # Mapeo de entornos a URLs
    env_urls = {
        "prod": "https://agent-api.prd.getcometa.com",
        "local": "http://localhost:8010",
    }

    # Selectbox para elegir el entorno
    selected_env = st.selectbox(
        "Entorno",
        options=list(env_urls.keys()),
        index=0,
        help="Selecciona el entorno del API",
    )

    base_url = env_urls[selected_env]
    st.caption(f"URL: `{base_url}`")

    api_url = f"{base_url}/v1/ask-db/query"

    # API Key oculta - se envía en cada request pero no se muestra al usuario
    api_key = "admin_key_no_limit"

    st.divider()

    # Configuración de parámetros del body
    st.subheader("Parámetros de la Conversación")

    # Thread ID (solo lectura)
    thread_id = st.text_input(
        "Thread ID",
        value=st.session_state.thread_id,
        help="ID único para la conversación actual",
        disabled=True,
    )

    school_id = st.text_input(
        "School ID",
        value="1f0c0932-074c-4296-ac2d-091cc6628da9",
        help="ID único de la escuela",
    )

    school_name = st.text_input(
        "School Name", value="Acatitlan", help="Nombre de la escuela"
    )

    st.divider()

    # Opciones de visualización
    st.subheader("Opciones de Visualización")
    show_metadata = st.checkbox("Mostrar metadatos", value=True)
    show_queries = st.checkbox("Mostrar queries ejecutadas", value=True)
    show_tools = st.checkbox("Mostrar herramientas usadas", value=True)

    st.divider()

    # Botones de acción
    col1, col2 = st.columns(2)

    with col1:
        # Botón para limpiar solo la visualización del chat
        if st.button(
            "🧹 Limpiar Vista",
            use_container_width=True,
            help="Limpia la visualización del chat sin afectar la conversación",
        ):
            st.session_state.messages = []
            st.rerun()

    with col2:
        # Botón para iniciar una nueva conversación
        if st.button(
            "✨ Nueva Conversación",
            use_container_width=True,
            help="Inicia una nueva conversación con un Thread ID nuevo",
        ):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.processing_reports = {}
            st.rerun()

# Mostrar el historial de mensajes
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Mostrar metadatos si están disponibles
        if message["role"] == "assistant" and "metadata" in message:
            metadata = message["metadata"]

            # Contenedor para metadatos
            if show_metadata or show_queries or show_tools:
                with st.expander("📊 Ver detalles de la respuesta", expanded=False):
                    if show_queries and metadata.get("queries_executed"):
                        st.markdown("**Queries Ejecutadas:**")
                        for i, query in enumerate(metadata["queries_executed"], 1):
                            st.markdown(
                                f'<div class="query-box">{query}</div>',
                                unsafe_allow_html=True,
                            )

                    if show_tools and metadata.get("tools_executed"):
                        st.markdown("**Herramientas Usadas:**")
                        st.code(", ".join(metadata["tools_executed"]))

                    if show_metadata:
                        st.markdown("**Metadatos Completos:**")
                        metadata_to_show = {
                            "success": metadata.get("success"),
                            "queries_executed": metadata.get("queries_executed"),
                            "tools_executed": metadata.get("tools_executed"),
                        }

                        # Agregar información de reportes sin la data
                        if metadata.get("reports_executed"):
                            reports_metadata = []
                            for report in metadata["reports_executed"]:
                                report_info = {
                                    "report_id": report.get("report_id"),
                                    "status": report.get("status"),
                                    "row_count": report.get("row_count"),
                                    "school_id": report.get("school_id"),
                                    "thread_id": report.get("thread_id"),
                                }
                                reports_metadata.append(report_info)
                            metadata_to_show["reports_executed"] = reports_metadata

                        st.json(metadata_to_show)

        # Los reportes ya están integrados en el mensaje

# Input del chat
if prompt := st.chat_input(
    "Escribe tu mensaje aquí...", disabled=st.session_state.is_processing
):
    # Marcar como procesando
    st.session_state.is_processing = True

    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mostrar mensaje del asistente con spinner
    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            try:
                # Preparar la petición
                headers = {
                    "accept": "application/json",
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                }

                body = {
                    "thread_id": thread_id,
                    "message": prompt,
                    "school_id": school_id,
                    "school_name": school_name,
                }

                # Hacer la petición al API
                response = requests.post(api_url, headers=headers, json=body)
                response.raise_for_status()

                # Procesar la respuesta
                data = response.json()

                if data.get("success"):
                    message_text = data.get("message", "Sin respuesta")

                    # Procesar reportes primero
                    reports = data.get("reports_executed", [])

                    # Eliminar duplicados de reportes (basado en report_id)
                    unique_reports = []
                    seen_ids = set()
                    for report in reports:
                        report_id = report.get("report_id")
                        if report_id and report_id not in seen_ids:
                            unique_reports.append(report)
                            seen_ids.add(report_id)

                    # Obtener links de reportes
                    report_links = []
                    for report_idx, report in enumerate(unique_reports):
                        link = get_report_link(
                            report,
                            len(st.session_state.messages),
                            report_idx,
                            api_key,
                            base_url,
                            is_new_message=True,
                        )
                        if link:
                            report_links.append(link)

                    # Integrar reportes al final del mensaje
                    if report_links:
                        message_text += "\n\n**Reporte:** " + " | ".join(report_links)

                    # Mostrar el mensaje completo con reportes integrados
                    st.markdown(message_text)

                    # Preparar metadatos
                    metadata = {
                        "success": data.get("success"),
                        "queries_executed": data.get("queries_executed", []),
                        "tools_executed": data.get("tools_executed", []),
                        "reports_executed": reports,
                    }

                    # Mostrar metadatos
                    if show_metadata or show_queries or show_tools:
                        with st.expander(
                            "📊 Ver detalles de la respuesta", expanded=False
                        ):
                            if show_queries and metadata.get("queries_executed"):
                                st.markdown("**Queries Ejecutadas:**")
                                for i, query in enumerate(
                                    metadata["queries_executed"], 1
                                ):
                                    st.markdown(
                                        f'<div class="query-box">{query}</div>',
                                        unsafe_allow_html=True,
                                    )

                            if show_tools and metadata.get("tools_executed"):
                                st.markdown("**Herramientas Usadas:**")
                                st.code(", ".join(metadata["tools_executed"]))

                            if show_metadata:
                                st.markdown("**Metadatos Completos:**")
                                metadata_to_show = {
                                    "success": metadata.get("success"),
                                    "queries_executed": metadata.get(
                                        "queries_executed"
                                    ),
                                    "tools_executed": metadata.get("tools_executed"),
                                }

                                # Agregar información de reportes sin la data
                                if metadata.get("reports"):
                                    reports_metadata = []
                                    for report in metadata["reports"]:
                                        report_info = {
                                            "report_id": report.get("report_id"),
                                            "status": report.get("status"),
                                            "row_count": report.get("row_count"),
                                            "school_id": report.get("school_id"),
                                            "thread_id": report.get("thread_id"),
                                        }
                                        reports_metadata.append(report_info)
                                    metadata_to_show["reports"] = reports_metadata

                                st.json(metadata_to_show)

                    # Agregar al historial (el mensaje ya incluye los reportes integrados)
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": message_text,
                            "metadata": metadata,
                        }
                    )
                else:
                    error_msg = f"❌ Error: {data.get('message', 'Error desconocido')}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

            except requests.exceptions.RequestException as e:
                error_msg = f"❌ Error de conexión: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
            except Exception as e:
                error_msg = f"❌ Error inesperado: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )
            finally:
                # Desmarcar como procesando y hacer rerun para habilitar el input
                st.session_state.is_processing = False
                st.rerun()

# Información en el footer
st.divider()
st.caption(f"Thread ID actual: `{st.session_state.get('thread_id', 'N/A')}`")
