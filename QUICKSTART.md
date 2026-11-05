# Quickstart

A one-page guide to get the Hinglish Smart Writing Assistant running. For the full write-up (design decisions, evaluation, limitations), see [README.md](README.md).

## What it does

Roman Hinglish in, clean Hindi (and optionally English) out:

```
"mujhe nhi pta, bill 500 rupees h"
   -> SMS normalisation -> IndicXlit (Devanagari) -> digit fix
   -> optional phrasing (Gemini) -> IndicTrans2 -> English
```

## Requirements

- Python 3.10+
- CPU is enough (GPU optional)
- Windows users: run everything inside **WSL Ubuntu 22.04**
- A free [Hugging Face](https://huggingface.co/) account (the translation model is gated)

## Install

The dependency chain is fragile (fairseq, pinned pip/setuptools, a patched `urduhack`), so follow the numbered steps in **[README.md, Section 4](README.md#4-setup-windows--wsl-ubuntu-2204)** in order. Background on each workaround is in [docs/SETUP_NOTES.md](docs/SETUP_NOTES.md).

Then accept the terms for [`ai4bharat/indictrans2-indic-en-dist-200M`](https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M) and log in:

```bash
huggingface-cli login
```

## Run the app

```bash
python app/app.py
```

Open http://localhost:7860. Models load once at startup, so the first launch is slow.

## Optional settings

| Variable             | Default            | Meaning                                         |
| -------------------- | ------------------ | ----------------------------------------------- |
| `GEMINI_API_KEY`     | _(empty)_          | Enables phrasing improvement. Never commit it.  |
| `PHRASING_BACKEND`   | `gemini`           | Set to `none` to skip phrasing.                 |
| `HINGLISH_NORMALIZE` | `1`                | Set to `0` to reproduce the raw baseline.       |

## Run the tests and evaluation

```bash
pytest tests/                      # unit tests
python eval/run_eval.py            # normalisation ON  -> eval/results_normalized.csv
python eval/run_eval.py --no-normalize   # baseline    -> eval/results.csv
```

## Where things live

| Folder  | Purpose                                         |
| ------- | ----------------------------------------------- |
| `src/`  | Pipeline and text normalisation                 |
| `app/`  | Gradio web UI                                   |
| `eval/` | Evaluation script and results                   |
| `data/` | 40 hand-written test cases                      |
| `docs/` | Setup notes and failure analysis                |
| `tests/`| Unit and integration tests                      |

## Troubleshooting

- **Gradio crashes with `unhashable type: 'dict'`**: you have unpinned FastAPI/Starlette. Use the versions in `requirements.txt`.
- **`pip check` warnings** (flask, gevent, pyarrow, ...): known and harmless for this pipeline.
- **Phrasing step errors or 503s**: the Gemini API is external; set `PHRASING_BACKEND=none` to bypass it.
- **Never launch Gradio with `share=True`**: it exposes your machine through a public tunnel.
