import os
import sys
import time
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit import IndicProcessor

def get_ram_mb():
    # Read Resident Set Size (VmRSS) from /proc/self/status on Linux
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return 0.0

def main():
    print(f"[RAM Initial] {get_ram_mb():.1f} MB")
    model_name = "ai4bharat/indictrans2-indic-en-dist-200M"
    
    t0 = time.time()
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    print("Loading model on CPU...")
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float32
    )
    model.eval()
    print(f"Model loaded in {time.time() - t0:.2f}s")
    print(f"[RAM After Model Load] {get_ram_mb():.1f} MB")
    
    ip = IndicProcessor(inference=True)
    
    sentences = [
        "मुझे कल यूनिवर्सिटी जाना है",
        "नमस्ते, आप कैसे हैं?",
        "यह प्रोजेक्ट बहुत उपयोगी साबित होगा।"
    ]
    src_lang = "hin_Deva"
    tgt_lang = "eng_Latn"
    
    print(f"\nTranslating {len(sentences)} sentences from Hindi to English...")
    t_start = time.time()
    
    # Preprocess
    batch = ip.preprocess_batch(sentences, src_lang=src_lang, tgt_lang=tgt_lang)
    inputs = tokenizer(batch, padding="longest", truncation=True, return_tensors="pt")
    
    # Generate
    with torch.no_grad():
        generated_tokens = model.generate(
            **inputs,
            num_beams=5,
            max_length=256
        )
    
    # Decode
    decoded = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
    translations = ip.postprocess_batch(decoded, lang=tgt_lang)
    
    t_elapsed = time.time() - t_start
    print(f"Translation completed in {t_elapsed:.2f}s")
    print(f"[RAM Peak During Inference] {get_ram_mb():.1f} MB\n")
    
    for src, tgt in zip(sentences, translations):
        print(f"Hindi:   {src}")
        print(f"English: {tgt}\n")

if __name__ == "__main__":
    main()
