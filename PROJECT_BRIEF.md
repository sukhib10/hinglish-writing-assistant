Project: Hinglish Smart Writing Assistant (course CS3235 mini-project)
Goal: Convert Roman-script Hinglish into Hindi (Devanagari script), improve the phrasing, and optionally translate into English.
Models and data:
- AI4Bharat IndicXlit for transliteration (Roman Hinglish to Devanagari)
- BharatGen Param1 for improving phrasing (prompting)
- AI4Bharat IndicTrans2 for Hindi to English translation
- Aksharantar dataset for transliteration evaluation
Frontend: Gradio. Language: Python 3.10+.
Evaluation: Character Error Rate and word accuracy for transliteration, translation quality for English output, using 30-50 hand-written test cases plus a failure analysis.
Rules:
- Use pretrained models only; no training from scratch.
- Keep code modular: /src, /app, /eval, /data, /tests.
- Pin versions in requirements.txt.
- Write a README with setup instructions.
- Run on CPU by default; GPU optional.
- Ask me before installing anything large or downloading large models.
- Explain what each file does in simple language.
- Never invent model names or package names; verify them on the official links.
