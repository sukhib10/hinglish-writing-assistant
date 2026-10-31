# Environment Setup & Workaround Notes

## Overview
This project runs AI4Bharat IndicXlit (transliteration) and IndicTrans2 (translation) on CPU. The project source code resides in the Windows workspace, while the execution environment runs inside **WSL (Ubuntu 22.04 LTS)** to bypass Windows-specific C++ compilation bottlenecks and path delimiter bugs in legacy NLP packages.

* **WSL Distribution**: `Ubuntu 22.04 LTS`
* **Python Virtual Environment**: `~/venvs/hinglish` (located in WSL home directory, not on `/mnt/c`)
* **Python Version**: `Python 3.10.12`

---

## 1. PyTorch CPU-Only Installation
PyTorch is installed from the official CPU wheel index to prevent downloading multi-gigabyte CUDA binaries.

```bash
~/venvs/hinglish/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
```
* **Installed Version**: `torch==2.14.1+cpu`

---

## 2. Toolchain & Build Package Pinning
Fairseq and legacy dependencies have strict requirements that clash with modern pip (>24.0) and setuptools (>70.0):

* `pip`: Must be `<24.1` (installed `24.0`) because pip 24.1+ strictly rejects legacy metadata syntax in `omegaconf<2.1` (`PyYAML (>=5.1.*)`).
* `setuptools`: Must be `<70` (installed `69.5.1`) for compiling fairseq Cython extensions.
* `numpy`: Must be `<2.0` (installed `1.26.4`) to maintain C-API binary compatibility with fairseq and PyTorch.
* `cython` and `wheel` are required to compile extensions from source.

```bash
~/venvs/hinglish/bin/pip install 'pip<24.1' 'setuptools<70' wheel cython 'numpy<2'
```

---

## 3. Fairseq Installation from Official Git Source
The PyPI package release for `fairseq` (`0.12.1` and `0.12.2`) is broken because `fairseq/version.txt` was omitted from the sdist tarball, causing `FileNotFoundError` during PEP 517 build isolation on all platforms.

**Resolution:**
Clone the official PyTorch Fairseq repository and build directly with `--no-build-isolation`:

```bash
cd ~
git clone https://github.com/pytorch/fairseq
cd fairseq
~/venvs/hinglish/bin/pip install --no-build-isolation .
```

---

## 4. `ai4bharat-transliteration` & `urduhack` Lightweight Patch
`ai4bharat-transliteration` depends on `urduhack`. By default, installing `urduhack` pulls `tensorflow-datasets`, `tf2crf`, and full **TensorFlow (~500 MB)**. However, `ai4bharat-transliteration` only uses `urduhack.normalization.normalize` for Urdu text, which is a lightweight string/regex utility.

**Resolution:**
1. Install `ai4bharat-transliteration` without recursive dependencies:
   ```bash
   ~/venvs/hinglish/bin/pip install --no-deps ai4bharat-transliteration
   ```
2. Install necessary runtime dependencies:
   ```bash
   ~/venvs/hinglish/bin/pip install ujson pydload indic-nlp-library
   ~/venvs/hinglish/bin/pip install --no-deps urduhack
   ```
3. Make TensorFlow imports lazy in `urduhack/__init__.py`:
   ```bash
   sed -i "s/from .pipeline import Pipeline/# from .pipeline import Pipeline/g" ~/venvs/hinglish/lib/python3.10/site-packages/urduhack/__init__.py
   sed -i "s/from .utils.resources import download/# from .utils.resources import download/g" ~/venvs/hinglish/lib/python3.10/site-packages/urduhack/__init__.py
   sed -i "s/from .conll import CoNLL/# from .conll import CoNLL/g" ~/venvs/hinglish/lib/python3.10/site-packages/urduhack/__init__.py
   ```

---

## 5. `transformers` Version Pinning for `IndicTransToolkit`
`IndicTransToolkit` (maintained by Varun Gumma / AI4Bharat) expects `PreTrainedTokenizerBase` in `transformers.tokenization_utils`. In `transformers 5.x`, the module organization was changed, causing `ImportError`.

**Resolution:**
Pin `transformers==4.40.2` and `sentencepiece==0.2.2`:

```bash
~/venvs/hinglish/bin/pip install transformers==4.40.2 sentencepiece
~/venvs/hinglish/bin/pip install git+https://github.com/VarunGumma/IndicTransToolkit.git
```

---

## 6. Model Checkpoints & Gated Access
* **IndicXlit**: Model assets are downloaded automatically by `XlitEngine` into:
  `~/venvs/hinglish/lib/python3.10/site-packages/ai4bharat/transliteration/transformer/models/en2indic/v1.0/`
* **IndicTrans2**: Model repository `ai4bharat/indictrans2-indic-en-dist-200M` on Hugging Face is a **gated model**. Users must click "Agree and access repository" on the Hugging Face model page and authenticate with a Hugging Face Read Token via:
  ```bash
  ~/venvs/hinglish/bin/huggingface-cli login
  # or export HF_TOKEN="hf_..."
  ```

---

## 7. Gradio Frontend Pinning (`gradio==4.44.1`)
`gradio==4.44.1` is pinned for the web application UI. Newer Gradio releases (5.x and 6.x) mandate `huggingface-hub>=0.25.1` or `huggingface-hub>=1.16.0`, which would force upgrading `huggingface-hub` to 2.x and risk breaking compatibility with `transformers==4.40.2`. `huggingface_hub==0.23.5` must stay pinned for `transformers 4.40.2` and IndicTrans2 stability. Pinning `gradio==4.44.1` cleanly satisfies `huggingface-hub>=0.19.3` while preserving all existing core ML packages (`torch`, `numpy`, `transformers`, `huggingface_hub`, `tokenizers`, `fairseq`, `pandas`) intact.
