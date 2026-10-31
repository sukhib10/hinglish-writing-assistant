"""
Pipeline module for Hinglish Writing Assistant.
Provides functions for transliteration, phrasing improvement, and translation.
"""

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit import IndicProcessor

# Module-level cache variables for lazy loading
_xlit_engine = None
_translation_model = None
_translation_tokenizer = None
_indic_processor = None

INDIC_TRANS_MODEL_NAME = "ai4bharat/indictrans2-indic-en-dist-200M"


def _get_xlit_engine():
    """
    Lazy loader for AI4Bharat IndicXlit engine.
    Loads the Hindi transliteration model only once and caches it in memory.
    """
    global _xlit_engine
    if _xlit_engine is None:
        from ai4bharat.transliteration import XlitEngine
        _xlit_engine = XlitEngine("hi")
    return _xlit_engine


def _get_translation_components():
    """
    Lazy loader for IndicTrans2 (Hindi to English) model and processor.
    Loads model weights and tokenizer once on CPU and caches them.
    """
    global _translation_model, _translation_tokenizer, _indic_processor
    if _translation_model is None or _translation_tokenizer is None or _indic_processor is None:
        _translation_tokenizer = AutoTokenizer.from_pretrained(
            INDIC_TRANS_MODEL_NAME,
            trust_remote_code=True
        )
        _translation_model = AutoModelForSeq2SeqLM.from_pretrained(
            INDIC_TRANS_MODEL_NAME,
            trust_remote_code=True,
            torch_dtype=torch.float32
        )
        _translation_model.eval()
        _indic_processor = IndicProcessor(inference=True)
        
    return _translation_model, _translation_tokenizer, _indic_processor


def transliterate(text: str) -> str:
    """
    Converts Roman-script Hinglish text into Devanagari Hindi.
    Uses AI4Bharat IndicXlit translit_sentence.
    """
    if not text or not text.strip():
        return ""
    
    engine = _get_xlit_engine()
    result = engine.translit_sentence(text.strip())
    
    # IndicXlit returns a dict mapping lang code to the converted sentence
    if isinstance(result, dict):
        return result.get("hi", "").strip()
    return str(result).strip()


def improve_phrasing(text: str) -> str:
    """
    Improves Hindi phrasing and grammar.
    Currently a placeholder that returns text unchanged.
    BharatGen Param1 or an LLM prompt will replace this step later.
    """
    # Placeholder: Param1 / prompt-based rephrasing will be added here
    return text


def translate_to_english(text: str) -> str:
    """
    Translates Devanagari Hindi text to English.
    Uses AI4Bharat IndicTrans2 distilled model (200M).
    """
    if not text or not text.strip():
        return ""
    
    model, tokenizer, ip = _get_translation_components()
    src_lang = "hin_Deva"
    tgt_lang = "eng_Latn"
    
    # 1. Preprocess sentence with IndicProcessor
    batch = ip.preprocess_batch([text.strip()], src_lang=src_lang, tgt_lang=tgt_lang)
    inputs = tokenizer(batch, padding="longest", truncation=True, return_tensors="pt")
    
    # 2. Generate translation tokens
    with torch.no_grad():
        generated_tokens = model.generate(
            **inputs,
            num_beams=5,
            max_length=256
        )
    
    # 3. Decode tokens and postprocess
    decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
    translations = ip.postprocess_batch(decoded, lang=tgt_lang)
    
    return translations[0].strip() if translations else ""


def run_pipeline(text: str, improve: bool = False, translate: bool = False) -> dict:
    """
    Chains the writing assistant stages:
    1. Transliteration (Hinglish -> Hindi)
    2. Optional Phrasing Improvement
    3. Optional Translation (Hindi -> English)
    """
    # Stage 1: Transliterate Roman Hinglish to Hindi
    hindi_text = transliterate(text)
    
    # Stage 2: Phrasing improvement (optional)
    if improve:
        improved_text = improve_phrasing(hindi_text)
    else:
        improved_text = hindi_text
        
    # Stage 3: Translation to English (optional)
    if translate:
        english_text = translate_to_english(improved_text)
    else:
        english_text = None
        
    return {
        "input": text,
        "transliterated": hindi_text,
        "improved": improved_text,
        "translated": english_text
    }
