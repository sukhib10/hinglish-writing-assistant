"""
Gradio web application for the Hinglish Smart Writing Assistant.
Provides an interactive UI for transliterating Roman Hinglish into Devanagari Hindi,
improving phrasing, and translating to English.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so src.pipeline can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr
from src.pipeline import (
    run_pipeline,
    _get_xlit_engine,
    _get_translation_components,
)

# ---------------------------------------------------------
# Startup Model Preloading
# ---------------------------------------------------------
print("=" * 60)
print("Initializing Hinglish Writing Assistant...")
print("Loading IndicXlit and IndicTrans2 models into memory at startup...")
try:
    # Explicitly initialize cached singletons so models load once at startup
    _get_xlit_engine()
    _get_translation_components()
    print("All models successfully preloaded and ready for inference!")
except Exception as preload_err:
    print(f"Warning: Model preloading encountered an issue: {preload_err}")
print("=" * 60)


def process_hinglish(text: str, improve: bool, translate: bool):
    """
    Process input Hinglish text through the pipeline with error handling.

    Args:
        text (str): Roman Hinglish input sentence.
        improve (bool): Whether to perform phrasing improvement.
        translate (bool): Whether to translate to English.

    Returns:
        tuple[str, str, str]: (Hindi Devanagari, Improved phrasing, English translation)
    """
    if not text or not text.strip():
        return "", "", ""

    try:
        result = run_pipeline(
            text=text.strip(),
            improve=improve,
            translate=translate,
        )
        hindi = result.get("transliterated", "") or ""
        improved = result.get("improved", "") or ""
        english = result.get("translated", "") or ""
        return hindi, improved, english
    except Exception as exc:
        error_message = f"An error occurred while processing: {str(exc)}"
        # Return friendly message in outputs instead of crashing
        return f"⚠️ {error_message}", "", ""


# ---------------------------------------------------------
# Gradio UI Layout
# ---------------------------------------------------------
TITLE = "Hinglish Writing Assistant"
DESCRIPTION = "Convert Roman-script Hinglish into Devanagari Hindi, refine phrasing, and translate to English."

# 5 clickable example sentences: casual Hinglish with English words, numbers, and a name
EXAMPLES = [
    ["Rahul kal 2 baje meeting ke liye office aayega."],
    ["Priya ne 3 tickets book kar diye hain movie ke."],
    ["Amit bhai 5 baje call karo, urgent project discussion hai."],
    ["Neha ko 1000 rupees Google Pay kar do please."],
    ["Rohit ne 4 new laptops order kiye team ke liye."],
]

with gr.Blocks(title=TITLE) as demo:
    gr.Markdown(f"# {TITLE}")
    gr.Markdown(f"*{DESCRIPTION}*")

    with gr.Row():
        with gr.Column(scale=1):
            input_text = gr.Textbox(
                label="Roman Hinglish Input",
                placeholder="Type your Roman Hinglish sentence here...",
                lines=3,
            )

            with gr.Row():
                improve_checkbox = gr.Checkbox(
                    label="Improve phrasing",
                    value=False,
                )
                translate_checkbox = gr.Checkbox(
                    label="Translate to English",
                    value=True,
                )

            convert_btn = gr.Button("Convert", variant="primary")

            gr.Examples(
                examples=EXAMPLES,
                inputs=[input_text],
                label="Clickable Examples",
            )

        with gr.Column(scale=1):
            out_hindi = gr.Textbox(
                label="Hindi (Devanagari)",
                lines=3,
                interactive=False,
            )
            out_improved = gr.Textbox(
                label="Improved phrasing",
                lines=3,
                interactive=False,
            )
            out_english = gr.Textbox(
                label="English",
                lines=3,
                interactive=False,
            )

    # Wire up button click and enter key submission
    convert_btn.click(
        fn=process_hinglish,
        inputs=[input_text, improve_checkbox, translate_checkbox],
        outputs=[out_hindi, out_improved, out_english],
    )
    input_text.submit(
        fn=process_hinglish,
        inputs=[input_text, improve_checkbox, translate_checkbox],
        outputs=[out_hindi, out_improved, out_english],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
