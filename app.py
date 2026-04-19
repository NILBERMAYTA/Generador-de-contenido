from __future__ import annotations

from io import BytesIO

import streamlit as st

from src.config import (
    get_gemini_api_key,
    get_stability_api_key,
    get_text_model,
    has_gemini_api_key,
    has_stability_api_key,
)
from src.image_generator import generate_image
from src.prompts import CONTENT_TYPES, QUICK_PROMPTS, STYLES
from src.text_generator import generate_text
from src.utils import make_download_name


st.set_page_config(
    page_title="Estudio Creativo Gemini",
    page_icon="🎨",
    layout="wide",
)


def init_session_state() -> None:
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("generated_text", "")
    st.session_state.setdefault("generated_image", None)
    st.session_state.setdefault("image_mime_type", "image/png")
    st.session_state.setdefault("visual_prompt", "")
    st.session_state.setdefault("last_request", {})


def reset_generation() -> None:
    st.session_state["generated_text"] = ""
    st.session_state["generated_image"] = None
    st.session_state["image_mime_type"] = "image/png"
    st.session_state["visual_prompt"] = ""
    st.session_state["last_request"] = {}


def add_to_history(prompt: str, content_type: str, style: str, text: str) -> None:
    st.session_state["history"].insert(
        0,
        {
            "prompt": prompt,
            "content_type": content_type,
            "style": style,
            "text": text,
        },
    )
    st.session_state["history"] = st.session_state["history"][:5]


def render_sidebar() -> tuple[str, str, int, str]:
    with st.sidebar:
        st.header("Configuración")
        content_type = st.selectbox("Tipo de contenido", CONTENT_TYPES, index=0)
        style = st.selectbox("Estilo o nicho", STYLES, index=0)
        length = st.slider("Longitud aproximada del texto", 80, 500, 180, step=20)
        aspect_ratio = st.selectbox(
            "Relación de aspecto de la imagen",
            ["1:1", "16:9", "9:16", "3:2", "2:3", "4:5", "5:4", "21:9", "9:21"],
            index=0,
        )

        st.divider()
        st.subheader("Ideas rápidas")
        for idx, example in enumerate(QUICK_PROMPTS):
            if st.button(example, key=f"quick_prompt_{idx}", use_container_width=True):
                st.session_state["prompt_input"] = example

        st.divider()
        if st.button("Generar otro", use_container_width=True):
            reset_generation()
            st.rerun()

        if st.session_state["history"]:
            st.divider()
            st.subheader("Historial reciente")
            for item in st.session_state["history"]:
                st.caption(f"{item['content_type']} · {item['style']}")
                st.write(item["prompt"])

    return content_type, style, length, aspect_ratio


def render_results() -> None:
    text_col, image_col = st.columns([1.1, 0.9], gap="large")

    with text_col:
        st.subheader("Texto generado")
        if st.session_state["generated_text"]:
            st.text_area(
                "Resultado",
                value=st.session_state["generated_text"],
                height=420,
                key="generated_text_area",
                disabled=True,
                label_visibility="collapsed",
            )
            st.download_button(
                "Descargar texto",
                data=st.session_state["generated_text"].encode("utf-8"),
                file_name=make_download_name("contenido_creativo", "txt"),
                mime="text/plain",
                use_container_width=False,
            )
        else:
            st.info("Aquí aparecerá el contenido generado en español.")

    with image_col:
        st.subheader("Imagen generada")
        if st.session_state["generated_image"]:
            st.image(st.session_state["generated_image"], use_container_width=True)
            st.download_button(
                "Descargar imagen",
                data=BytesIO(st.session_state["generated_image"]).getvalue(),
                file_name=make_download_name("imagen_creativa", "png"),
                mime=st.session_state["image_mime_type"],
                use_container_width=True,
            )
            with st.expander("Prompt visual usado"):
                st.write(st.session_state["visual_prompt"])
        else:
            st.info("Aquí se mostrará la imagen.")


def main() -> None:
    init_session_state()

    st.title("Generación de Contenido Creativo Asistida por IA")

    content_type, style, length, aspect_ratio = render_sidebar()

    if not has_gemini_api_key():
        st.warning(
            "No se encontró `GEMINI_API_KEY`. Crea un archivo `.env` basado en "
            "`./.env.example` antes de generar contenido."
        )
    if not has_stability_api_key():
        st.warning(
            "No se encontró `STABILITY_API_KEY`. Agrega tu clave de Stability AI en `.env` para generar imágenes."
        )


    user_prompt = st.text_area(
        "Escribe tu idea o prompt base",
        key="prompt_input",
        height=180,
        placeholder=(
            "Ejemplo: Un dragón bibliotecario descubre un mapa escondido entre libros "
            "antiguos y emprende un viaje inesperado."
        ),
    )

    if st.button("Generar", type="primary", use_container_width=True):
        if not user_prompt.strip():
            st.error("Debes escribir una idea base antes de generar contenido.")
        elif not has_gemini_api_key():
            st.error("Falta la API key. Configura `GEMINI_API_KEY` en tu archivo `.env`.")
        elif not has_stability_api_key():
            st.error("Falta la API key. Configura `STABILITY_API_KEY` en tu archivo `.env`.")
        else:
            try:
                gemini_api_key = get_gemini_api_key()
                stability_api_key = get_stability_api_key()

                with st.spinner("Generando texto creativo..."):
                    generated_text = generate_text(
                        user_prompt=user_prompt,
                        content_type=content_type,
                        style=style,
                        length=length,
                        api_key=gemini_api_key,
                    )

                with st.spinner("Generando imagen con Stability AI..."):
                    image_result = generate_image(
                        generated_text=generated_text,
                        style=style,
                        api_key=stability_api_key,
                        gemini_api_key=gemini_api_key,
                        aspect_ratio=aspect_ratio,
                    )

                st.session_state["generated_text"] = generated_text
                st.session_state["generated_image"] = image_result["image_bytes"]
                st.session_state["image_mime_type"] = image_result["mime_type"]
                st.session_state["visual_prompt"] = image_result["image_prompt"]
                st.session_state["last_request"] = {
                    "prompt": user_prompt,
                    "content_type": content_type,
                    "style": style,
                    "length": length,
                    "aspect_ratio": aspect_ratio,
                }
                add_to_history(user_prompt, content_type, style, generated_text)
                st.success("Texto e imagen generados correctamente.")
            except Exception as exc:
                st.error(f"No fue posible completar la generación: {exc}")

    render_results()


if __name__ == "__main__":
    main()
