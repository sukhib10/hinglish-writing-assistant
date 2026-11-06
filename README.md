# Hinglish Smart Writing Assistant

Convert Roman-script Hinglish into Hindi (Devanagari script), optionally improve the phrasing, and optionally translate into English.

---

## 1. Problem and Relevance

Roman-script Hinglish (Hindi written using the Latin alphabet) is the predominant medium of informal digital communication across hundreds of millions of smartphone and computer users in India. Despite its widespread everyday use, processing Romanized Hinglish presents major computational NLP challenges:

- **High Spelling and Phonetic Ambiguity**: Hinglish has no standardized orthography. Users frequently drop vowels, abbreviate words, or use colloquial shorthand (e.g., `nhi`, `nahin`, `mai`, `thik`, `hu`).
- **Code-Mixing**: Hinglish fluidly blends Hindi grammar and vocabulary with English words and loan terms (e.g., `meeting`, `laptop`, `idea`, `change`, `rupees`).
- **Loss of Grammatical and Phonetic Information**: The Latin script does not encode grammatical gender, long vs. short vowel distinctions, nukta marks (`़`), or nasalization (candrabindu `ँ` vs. anusvara `ं`), leading to ambiguity during downstream understanding.

This writing assistant provides an end-to-end pipeline to convert informal Roman Hinglish into clean Devanagari Hindi, optionally refine the phrasing and grammar, and optionally generate an accurate English translation.

---

## 2. Pipeline

The processing pipeline takes Roman Hinglish and transforms it in a multi-stage cascading architecture:

```
Hinglish -> SMS normalisation -> IndicXlit -> digit fix -> optional phrasing (Gemini API, swappable backend) -> IndicTrans2 distilled 200M -> English
```

### Detailed Pipeline Flow

```
+--------------------------------------------------------------------------+
|                        Input Roman Hinglish                              |
|                   e.g., "mujhe nhi pta, bill 500 rupees h"               |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| Stage 1: Pre-Transliteration SMS Normalisation (src/normalize.py)         |
| - Whole-word regex expansion of informal chat shorthand                   |
| - e.g., 'nhi' -> 'nahi', 'pta' -> 'pata', 'h' -> 'hai'                   |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| Stage 2: Transliteration via AI4Bharat IndicXlit                         |
| - Converts phonetically Romanized input into Devanagari Hindi script     |
| - Model: AI4Bharat XlitEngine ("hi")                                     |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| Stage 3: Post-Transliteration Digit Fix (src/normalize.py)               |
| - Converts native Devanagari numerals (०-९) back to ASCII digits (0-9)  |
| - Matches modern Hindi digital writing conventions                       |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| Stage 4: Optional Phrasing Improvement (src/pipeline.py)                 |
| - Swappable backend (PHRASING_BACKEND="gemini" or "none")                |
| - Refines Hindi grammar, natural flow, and phrasing via REST API         |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| Stage 5: Optional Translation to English (src/pipeline.py)               |
| - Model: AI4Bharat IndicTrans2 distilled 200M (hin_Deva -> eng_Latn)     |
| - Preprocessed and tokenized via IndicTransToolkit                       |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                              Outputs                                     |
| - Hindi (Devanagari)                                                     |
| - Improved Phrasing (optional)                                           |
| - English Translation (optional)                                         |
+--------------------------------------------------------------------------+
```

---

## 3. Models, Data, and Design Decisions

- **Transliteration (`AI4Bharat IndicXlit`)**:
  - Pretrained transformer model for converting Roman script to Devanagari Hindi.
  - Automatically loads and caches model assets via `ai4bharat.transliteration.XlitEngine("hi")`.
- **Translation (`AI4Bharat IndicTrans2 distilled 200M`)**:
  - Gated Hugging Face model (`ai4bharat/indictrans2-indic-en-dist-200M`) designed for high-quality Indic-to-English translation.
  - **Why distilled 200M?** It fits easily within a standard CPU laptop environment (and low-resource GPUs), providing fast inference without requiring massive VRAM or multi-gigabyte downloads.
- **Phrasing Improvement (`Gemini REST API` / Swappable Backend)**:
  - The project brief originally suggested BharatGen Param1 for phrasing refinement. However, BharatGen Param1 does not fit our target development hardware (16 GB system RAM and 2 GB NVIDIA MX GPU).
  - The phrasing step was implemented as an external REST API call to Google Gemini (`gemini-2.5-flash` by default) using standard `requests` with a 10-second timeout.
  - The backend is swappable via the `PHRASING_BACKEND` environment variable (`gemini` or `none`), allowing local models like BharatGen Param1 to be dropped in if higher-capacity hardware becomes available.
- **Aksharantar Dataset**:
  - Listed in `PROJECT_BRIEF.md` for transliteration evaluation.
  - **Status**: Not used; to be added (the repository currently evaluates on `data/test_cases.csv` and does not yet integrate the Aksharantar dataset).

---

## 4. Setup (Windows + WSL Ubuntu 22.04)

This project runs on CPU. Because legacy NLP packages have Windows compilation bottlenecks and path delimiter issues, the execution environment runs inside **WSL (Ubuntu 22.04 LTS)** with a virtual environment at `~/venvs/hinglish`.

Follow these reproducible steps in order, taken directly from [docs/SETUP_NOTES.md](file:///docs/SETUP_NOTES.md):

### 1. Create the Virtual Environment in WSL

```bash
python3 -m venv ~/venvs/hinglish
```

### 2. Install CPU-Only PyTorch

Install PyTorch from the official CPU wheel index to avoid downloading multi-gigabyte CUDA binaries:

```bash
~/venvs/hinglish/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 3. Pin Build Toolchain and Core Packages

Fairseq and legacy dependencies require pip `<24.1`, setuptools `<70`, and numpy `<2`:

```bash
~/venvs/hinglish/bin/pip install 'pip<24.1' 'setuptools<70' wheel cython 'numpy<2'
```

### 4. Build Fairseq from Official Git Source

The PyPI sdist tarball for `fairseq` (0.12.1/0.12.2) is missing `version.txt`. Clone from git and build with `--no-build-isolation`:

```bash
cd ~
git clone https://github.com/pytorch/fairseq
cd fairseq
~/venvs/hinglish/bin/pip install --no-build-isolation .
```

### 5. Install `ai4bharat-transliteration` and Apply the Lightweight `urduhack` Patch

`ai4bharat-transliteration` depends on `urduhack`, which by default pulls in TensorFlow (~500 MB). Only `urduhack.normalization.normalize` is needed:

```bash
~/venvs/hinglish/bin/pip install --no-deps ai4bharat-transliteration
~/venvs/hinglish/bin/pip install ujson pydload indic-nlp-library
~/venvs/hinglish/bin/pip install --no-deps urduhack
sed -i "s/from .pipeline import Pipeline/# from .pipeline import Pipeline/g" ~/venvs/hinglish/lib/python3.10/site-packages/urduhack/__init__.py
sed -i "s/from .utils.resources import download/# from .utils.resources import download/g" ~/venvs/hinglish/lib/python3.10/site-packages/urduhack/__init__.py
sed -i "s/from .conll import CoNLL/# from .conll import CoNLL/g" ~/venvs/hinglish/lib/python3.10/site-packages/urduhack/__init__.py
```

### 6. Install `transformers` and `IndicTransToolkit`

Pin `transformers==4.40.2` and `sentencepiece==0.2.2` to prevent breaking changes in tokenization modules:

```bash
~/venvs/hinglish/bin/pip install transformers==4.40.2 sentencepiece
~/venvs/hinglish/bin/pip install git+https://github.com/VarunGumma/IndicTransToolkit.git
```

### 7. Install Remaining Project Dependencies

Install Gradio and evaluation packages matching pins in `requirements.txt`:

```bash
~/venvs/hinglish/bin/pip install gradio==4.44.1 fastapi==0.112.2 starlette==0.38.6 pydantic==2.10.6 jiwer==4.0.0 RapidFuzz==3.14.5 sacremoses==0.2.0 sacrebleu==2.6.0 omegaconf==2.0.6 hydra-core==1.0.7 bitarray==3.12.3 pandas==2.3.3 scipy==1.15.3 scikit-learn==1.7.2
```

### 8. Hugging Face Authentication for Gated IndicTrans2

The translation model `ai4bharat/indictrans2-indic-en-dist-200M` is gated:

1. Log in to your [Hugging Face](https://huggingface.co/) account and accept terms on the model page: [ai4bharat/indictrans2-indic-en-dist-200M](https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M).
2. Authenticate in WSL:

```bash
~/venvs/hinglish/bin/huggingface-cli login
# or: hf auth login
# or export HF_TOKEN="hf_..."
```

---

## 5. Running the Application

Launch the Gradio web interface from the project root:

```bash
python app/app.py
```

_(If running from WSL, invoke via `~/venvs/hinglish/bin/python app/app.py`)_

Then open your browser and navigate to:

```
http://localhost:7860
```

### Environment Configuration Options

You can control pipeline features and credentials via environment variables:

| Variable             |      Default       | Purpose / Allowed Values                                                                        |
| :------------------- | :----------------: | :---------------------------------------------------------------------------------------------- |
| `GEMINI_API_KEY`     |     _(empty)_      | Optional API key for Gemini phrasing improvement. Never print, commit, or hardcode API keys.    |
| `GEMINI_MODEL`       | `gemini-2.5-flash` | Model identifier for the phrasing REST API.                                                     |
| `PHRASING_BACKEND`   |      `gemini`      | `gemini` (enables API call) or `none` (bypasses phrasing and returns raw transliteration).      |
| `HINGLISH_NORMALIZE` |        `1`         | `1` (enables SMS normalisation and digit fix) or `0` (disables them to reproduce raw baseline). |

> [!WARNING]
> **Do not use `share=True`**: Never launch the Gradio application with `share=True` in `demo.launch()`, as this publishes the app and local network services to a public internet tunnel.

---

## 6. Evaluation

The project is evaluated on a diagnostic suite of **40 test cases** located in [data/test_cases.csv](file:///data/test_cases.csv).

- **Categories (7 total)**: `short` (6), `long` (6), `english_mix` (7), `names` (5), `numbers` (5), `slang` (6), `spelling` (5).
- **Reference Annotations**: Reference Hindi and English sentences were drafted with AI assistance and verified.

### Running the Evaluation Script

Run the evaluation script from the project root:

- **Default Evaluation (Normalisation ON)**:

  ```bash
  python eval/run_eval.py
  ```

  Saves results with strict and normalised metrics to `eval/results_normalized.csv`.

- **Baseline Evaluation (Normalisation OFF)**:

  ```bash
  python eval/run_eval.py --no-normalize
  ```

  Reproduces the raw baseline and writes to `eval/results.csv`.

- **With Phrasing Improvement Stage**:
  ```bash
  python eval/run_eval.py --phrasing
  ```
  Enables `improve_phrasing()` between transliteration and translation (requires `GEMINI_API_KEY`).

### Evaluation Metrics

1. **Hindi Transliteration Metrics (`jiwer`)**:
   - **Strict Character Error Rate (CER)**: Exact character match against reference. Penalizes any difference in diacritics, nukta (`़`), candrabindu (`ँ`), or numerals.
   - **Normalised Character Error Rate (CER)**: Removes nukta (`़`, `U+093C`), normalizes candrabindu (`ँ`) to anusvara (`ं`), removes ASCII and Unicode punctuation (including danda `।`), and strips excess whitespace.
   - **Strict Word Accuracy**: Defined as $1 - \text{WER}$ on exact strings.
   - **Normalised Word Accuracy**: Defined as $1 - \text{WER}$ on normalised strings.
   - **Exact Match**: Percentage of outputs matching the reference verbatim.
2. **English Translation Metrics (`sacrebleu`)**:
   - **Sentence-level and Corpus-level chrF**: Character n-gram F-score.
   - **Sentence-level and Corpus-level BLEU**: Precision-based n-gram overlap metric.

### Results: Baseline vs. Normalised

The table below compares the baseline pipeline (normalisation OFF) against the improved pipeline (normalisation ON) across all 40 test cases (copied directly from [docs/failure_analysis.md](file:///docs/failure_analysis.md)):

| Metric                                     | Baseline (Norm OFF) | Normalised (Norm ON) | Absolute Change | Relative Change (%) |
| :----------------------------------------- | :-----------------: | :------------------: | :-------------: | :-----------------: |
| **Strict CER (%)**                         |        7.00%        |        4.88%         |     -2.12%      |       -30.29%       |
| **Normalised CER (%)**                     |        6.67%        |        4.54%         |     -2.13%      |       -31.93%       |
| **Strict Word Accuracy (1 - WER) (%)**     |       81.85%        |        86.29%        |     +4.44%      |       +5.42%        |
| **Normalised Word Accuracy (1 - WER) (%)** |       83.47%        |        87.90%        |     +4.43%      |       +5.31%        |
| **Strict Exact Match**                     |   14 / 40 (35.0%)   |   17 / 40 (42.5%)    |   +3 (+7.5%)    |       +21.43%       |
| **Corpus chrF**                            |        65.18        |        65.58         |      +0.40      |       +0.61%        |
| **Corpus BLEU**                            |        38.53        |        39.50         |      +0.97      |       +2.52%        |

### Per-Category Strict CER Comparison

| Category      | Test Count | Baseline Strict CER (%) | Normalised Strict CER (%) | Absolute Change | Status                               |
| :------------ | :--------: | :---------------------: | :-----------------------: | :-------------: | :----------------------------------- |
| `spelling`    |     5      |    20.31% (13 / 64)     |      3.12% (2 / 64)       |     -17.19%     | Substantial improvement              |
| `numbers`     |     5      |    14.75% (18 / 122)    |      5.74% (7 / 122)      |     -9.01%      | Substantial improvement              |
| `slang`       |     6      |    8.63% (12 / 139)     |     7.91% (11 / 139)      |     -0.72%      | Minor improvement (Row 34 digit fix) |
| `long`        |     6      |    5.75% (18 / 313)     |     5.75% (18 / 313)      |      0.00%      | Unchanged                            |
| `names`       |     5      |     5.42% (9 / 166)     |      5.42% (9 / 166)      |      0.00%      | Unchanged                            |
| `english_mix` |     7      |     2.55% (5 / 196)     |      2.55% (5 / 196)      |      0.00%      | Unchanged                            |
| `short`       |     6      |     1.16% (1 / 86)      |      1.16% (1 / 86)       |      0.00%      | Unchanged                            |

---

## 7. Key Findings and Failure Analysis Summary

Detailed diagnosis and error categorisation are available in [docs/failure_analysis.md](file:///docs/failure_analysis.md). Key findings include:

1. **Informal / SMS Spelling Breakdown**: Without pre-normalisation, `IndicXlit` fails on vowel-less tokens. For example, `pta` was mistransliterated as the acronym `पीटीए` (PTA), and `mai` was mistransliterated as the calendar month "May" (`मई`).
2. **Cascaded Error Propagation**: `IndicTrans2` blindly translates the generated Devanagari. When `mujhe nhi pta` became `मुझे नही पीटीए`, the English translation output was `"I don't have a PTA."` instead of `"I don't know"`.
3. **Devanagari Digits Penalty**: `IndicXlit` turns Arabic numerals into native Devanagari numerals (`०-९`), which mismatched digital Hindi references using standard ASCII `0-9`.
4. **Loanword Spelling Conventions**: English loanwords such as `rupees`, `idea`, and `minute` were transliterated literally as `रुपीस`, `आईडीईए` ("I-D-E-A"), and `मिन्यूट` rather than standard `रुपये`, `आइडिया`, and `मिनट`.
5. **Cross-Lingual Homograph Ambiguity**: In `meeting ka time change ho gaya hai`, the English word `change` was transliterated as `चंगे` (Punjabi/Hindi for "good/fine"), translating downstream to `"The time of the meeting has become good."`.
6. **Impact of Targeted Normalisation**: Adding pre-transliteration SMS expansion (`normalize_sms`) and post-transliteration digit mapping (`devanagari_to_ascii_digits`) in `src/normalize.py` lowered strict CER from 7.00% to 4.88% (a 30.3% relative reduction), reduced the `spelling` CER from 20.31% to 3.12%, and eliminated catastrophic translation failures on rows 37 and 39.

For the full qualitative and quantitative analysis, see [docs/failure_analysis.md](file:///docs/failure_analysis.md).

---

## 8. Limitations

1. **Small Test Set**: The test suite contains only 40 sentences across 7 categories. While useful for qualitative diagnosis, a larger corpus is needed for tight statistical confidence intervals.
2. **AI-Drafted References**: Reference sentences were initially generated with AI assistance before human checking. Minor stylistic differences between model translations and single reference sentences unfairly penalize string-overlap metrics like chrF and BLEU.
3. **External API Fragility for Phrasing**: The phrasing improvement module relies on an external REST API (Gemini). During preliminary testing, requests occasionally encountered network latency and `503 Service Unavailable` errors. Furthermore, phrasing improvement was disabled during the baseline evaluation and has not yet been systematically measured.
4. **Dictionary Tuned on the Test Set**: The 11-word substitution dictionary in `src/normalize.py` was developed to address failures observed directly in `data/test_cases.csv`. A separate held-out test dataset is required to confirm that these rules generalize without introducing regressions on unobserved Hinglish text.
5. **Harmless `pip check` Warnings**: Running `pip check` reports broken requirement warnings for packages like `flask`, `gevent`, `pyarrow`, `tensorboardx`, and `urduhack`. These are known transitive dependency mismatches from legacy packages that do not affect the execution of this pipeline.
6. **Gradio 4.44.1 Dependency Pinning**: `gradio==4.44.1` must be used with strictly pinned `fastapi==0.112.2`, `starlette==0.38.6`, and `pydantic==2.10.6`. Installing unpinned newer versions of Starlette or FastAPI causes runtime crashes (`TypeError: unhashable type: 'dict'`), while upgrading Gradio to 5.x/6.x forces a `huggingface-hub` upgrade that breaks compatibility with `transformers==4.40.2`.

---

## 9. Repository Structure

```
hinglish-writing-assistant/
├── app/
│   └── app.py                     # Gradio web UI application
├── data/
│   └── test_cases.csv             # 40 curated test cases across 7 categories
├── docs/
│   ├── failure_analysis.md        # Comprehensive failure analysis & empirical report
│   └── SETUP_NOTES.md             # Detailed WSL setup guide & dependency workarounds
├── eval/
│   ├── results.csv                # Baseline evaluation results (normalisation OFF)
│   ├── results_normalized.csv     # Normalised pipeline evaluation results (normalisation ON)
│   └── run_eval.py                # Evaluation benchmark script (jiwer + sacrebleu)
├── src/
│   ├── __init__.py
│   ├── normalize.py               # SMS shorthand expansion & Devanagari digit conversion
│   └── pipeline.py                # Core pipeline (transliterate, improve phrasing, translate)
├── tests/
│   ├── test_normalize.py          # Unit tests for text normalization
│   ├── test_phrasing.py           # Unit tests for phrasing backend
│   ├── test_pipeline.py           # Unit tests for end-to-end pipeline
│   └── test_translation_wsl.py    # Integration test for IndicTrans2 in WSL
├── .gitignore                     # Git ignore rules
├── PROJECT_BRIEF.md               # Mini-project specification & original requirements
├── README.md                      # Project documentation (this file)
└── requirements.txt               # Pinned package requirements
```

---

## 10. Licences and Credits

- **AI4Bharat IndicXlit**:
  - Developed by AI4Bharat (IIT Madras).
  - Used for Roman-to-Devanagari transliteration.
  - Reference: [AI4Bharat IndicXlit GitHub](https://github.com/AI4Bharat/IndicXlit). Released under open research license.
- **AI4Bharat IndicTrans2**:
  - Developed by AI4Bharat (IIT Madras).
  - Model: `ai4bharat/indictrans2-indic-en-dist-200M`.
  - Released under Creative Commons Attribution 4.0 International (CC-BY-4.0).
  - Reference: [AI4Bharat IndicTrans2](https://github.com/AI4Bharat/IndicTrans2).
- **IndicTransToolkit**:
  - Maintained by Varun Gumma and AI4Bharat for pre/post-processing Indic language tokens.
- **Fairseq**:
  - Maintained by PyTorch / Meta AI. Built from GitHub source to support sequence-to-sequence inference.
- **Aksharantar Dataset**:
  - AI4Bharat open benchmark dataset for Indic transliteration (referenced in project brief).
- **Google Gemini API**:
  - Generative Language REST API used as an external swappable backend for phrasing improvement.
 
## 11 . Results 
<img width="1545" height="552" alt="36810534-6b4b-4463-a4ae-ab5ba4803ece" src="https://github.com/user-attachments/assets/4d49830d-aa2d-44bc-8159-6341f30e4fdd" />
<img width="1591" height="637" alt="9269d8f3-6722-448c-a7c0-f86d8a59566c" src="https://github.com/user-attachments/assets/75e24ea8-d06f-4f30-beca-9acac6f31ba8" />
<img width="1584" height="651" alt="d18b5d29-6541-4071-81c0-7dd546e956b7" src="https://github.com/user-attachments/assets/707eb960-eba1-479c-a0ed-6c17c35bbb0c" />
