# Failure Analysis: Hinglish Writing Assistant

## 1. Overview

This document presents a failure and error analysis for the Hinglish Writing Assistant baseline pipeline.

The evaluation suite consists of **40 test cases** across **7 distinct categories**:

- `short` (6 test cases)
- `long` (6 test cases)
- `english_mix` (7 test cases)
- `names` (5 test cases)
- `numbers` (5 test cases)
- `slang` (6 test cases)
- `spelling` (5 test cases)

### Baseline Pipeline Setup

- **Phrasing Step**: **OFF** (`PHRASING_BACKEND=none`).
- **Transliteration**: AI4Bharat `IndicXlit` (Roman script Hinglish to Devanagari Hindi).
- **Translation**: AI4Bharat `IndicTrans2` distilled 200M model (`ai4bharat/indictrans2-indic-en-dist-200M`, Devanagari Hindi to English).

### Overall Metrics

- **Strict Character Error Rate (CER)**: 7.00%
- **Strict Word Accuracy (1 - WER)**: 81.85%
- **Normalised Character Error Rate (CER)**: 6.67%
- **Corpus chrF**: 65.18
- **Corpus BLEU**: 38.53

### Per-Category Performance Breakdown

The following table reports the metrics per category computed from `eval/results.csv`. Exact match counts denote rows where the generated Hindi matched the reference Hindi verbatim.

| Category      | Count | Strict CER (%) | Word Accuracy (%) | Exact Match (Strict) | Corpus chrF | Mean Sentence chrF |
| :------------ | :---: | :------------: | :---------------: | :------------------: | :---------: | :----------------: |
| `english_mix` |   7   |     2.55%      |      95.56%       |    5 / 7 (71.4%)     |    59.73    |       57.45        |
| `long`        |   6   |     5.75%      |      77.61%       |     0 / 6 (0.0%)     |    73.09    |       72.32        |
| `names`       |   5   |     5.42%      |      86.11%       |     0 / 5 (0.0%)     |    81.50    |       86.27        |
| `numbers`     |   5   |     14.75%     |      66.67%       |     0 / 5 (0.0%)     |    63.45    |       63.87        |
| `short`       |   6   |     1.16%      |      95.83%       |    5 / 6 (83.3%)     |    63.52    |       68.03        |
| `slang`       |   6   |     8.63%      |      81.82%       |    3 / 6 (50.0%)     |    40.46    |       37.32        |
| `spelling`    |   5   |     20.31%     |      56.25%       |    1 / 5 (20.0%)     |    62.11    |       52.44        |

_(Note: In `eval/results.csv`, per-row CER mean values are: `english_mix`: 2.54%, `long`: 5.88%, `names`: 5.59%, `numbers`: 15.36%, `short`: 1.19%, `slang`: 8.30%, `spelling`: 21.96%.)_

---

## 2. Method

### Reference Creation and Verification

The reference Hindi and English sentences in `data/test_cases.csv` were originally drafted with AI assistance and subsequently reviewed by human annotators.

- **Verified by**: TEAM

### Strict vs. Normalised Scoring

Two scoring modes were evaluated using the `jiwer` library:

1. **Strict Scoring**:
   - Compares the generated Devanagari output against the reference string character-for-character without any modifications.
   - Any difference in diacritics (nukta `़`), nasalization markers (candrabindu `ँ` vs. anusvara `ं`), punctuation marks (ASCII commas, periods, or Hindi danda `।`), or numeral representations (ASCII `0-9` vs. Devanagari `०-९`) is penalized as an error.
2. **Normalised Scoring**:
   - Removes nukta (`़`, Unicode `U+093C`) in both decomposed and precomposed Unicode representations.
   - Maps candrabindu (`ँ`, Unicode `U+0901`) to anusvara (`ं`, Unicode `U+0902`).
   - Strips all ASCII punctuation and Unicode punctuation (category `P*`, including the danda `।`).
   - Collapses consecutive whitespace and trims leading/trailing spaces.

### Valid Spelling Variants

A significant finding in the evaluation is that several mismatches flagged by strict CER are legitimate spelling or transliteration variants rather than actual mistakes:

- **Nasalization variants**: e.g., `नहीं` vs. `नही` (Row 8, Row 11, Row 36), `आऊँगा` vs. `आऊंगा` (Row 27). Both are widespread in standard written and informal Hindi.
- **Pronoun spellings**: e.g., `यह` vs. `येह` (Row 5).
- **Loanword conventions**: e.g., `सब्जेक्ट्स` vs. `सब्जेक्ट` (Row 28), `एग्जाम` vs. `एक्जाम` (Row 7).
- **Vocabulary choices**: e.g., `इंतजार` vs. `इंतज़ार` (Row 11).

Normalised scoring reduces the overall CER from 7.00% to 6.67%, but does not capture all valid orthographic alternatives.

---

## 3. Failure Categories

### a. Informal / SMS Spelling Variants

- **Description**: Users frequently communicate in informal chat shorthand by omitting vowels, shortening syllables, or using non-standard phonetic spellings (e.g., `nhi`, `pta`, `mai`, `thik`, `hu`). The transliteration model struggles to infer the intended word when standard vowels are missing.
- **Real Examples from `results.csv`**:
  - **Row 37**:
    - **Hinglish Input**: `mujhe nhi pta`
    - **Reference Hindi**: `मुझे नहीं पता`
    - **Output Hindi**: `मुझे नही पीटीए`
    - **Output English**: `I don't have a PTA.`
    - _(Metrics: Strict CER = 0.3846, Exact Match = 0)_
  - **Row 39**:
    - **Hinglish Input**: `mai thik hu`
    - **Reference Hindi**: `मैं ठीक हूँ`
    - **Output Hindi**: `मई थिक हू`
    - **Output English**: `May is fine.`
    - _(Metrics: Strict CER = 0.4545, Exact Match = 0)_
  - **Row 38**:
    - **Hinglish Input**: `main theek hun`
    - **Reference Hindi**: `मैं ठीक हूँ`
    - **Output Hindi**: `मैं ठीक हुन`
    - **Output English**: `I'll be alright`
    - _(Metrics: Strict CER = 0.1818, Exact Match = 0)_
- **Likely Cause**: `IndicXlit` is trained on phonetically spelled Romanized Hindi. When presented with vowel-less SMS acronyms like `pta`, it treats the token as an uppercase acronym (`PTA` -> `पीटीए`). For `mai`, it matches the English calendar month "May" (`मई`) rather than the first-person pronoun `मैं`.
- **Possible Fix**: Introduce a rule-based or dictionary-based pre-processing step to canonicalize common SMS abbreviations before transliteration (e.g., `nhi` -> `nahi`, `pta` -> `pata`, `mai` -> `main`, `thik` -> `theek`, `hu`/`hun` -> `hoon`).

---

### b. Error Propagation from Transliteration into Translation

- **Description**: The translation stage (`IndicTrans2`) operates downstream of the transliteration stage (`IndicXlit`). When transliteration outputs an unintended word or acronym, the translation model faithfully translates that erroneous Devanagari word, producing a nonsensical or misleading English sentence.
- **Real Examples from `results.csv`**:
  - **Row 37**:
    - **Hinglish Input**: `mujhe nhi pta`
    - **Reference Hindi**: `मुझे नहीं पता`
    - **Output Hindi**: `मुझे नही पीटीए`
    - **Output English**: `I don't have a PTA.` _(Reference English: `I don't know`)_
  - **Row 39**:
    - **Hinglish Input**: `mai thik hu`
    - **Reference Hindi**: `मैं ठीक हूँ`
    - **Output Hindi**: `मई थिक हू`
    - **Output English**: `May is fine.` _(Reference English: `I am fine`)_
  - **Row 14**:
    - **Hinglish Input**: `meeting ka time change ho gaya hai`
    - **Reference Hindi**: `मीटिंग का टाइम चेंज हो गया है`
    - **Output Hindi**: `मीटिंग का टाइम चंगे हो गया है`
    - **Output English**: `The time of the meeting has become good.` _(Reference English: `The meeting time has changed`)_
- **Likely Cause**: The pipeline is strictly cascading. `IndicTrans2` possesses no visibility into the original Roman Hinglish prompt and assumes `Output Hindi` represents the user's intended semantics.
- **Possible Fix**: Apply an intermediate phrasing/grammar validation layer (such as the phrasing improvement step) or perform joint re-ranking using the source Roman text.

---

### c. Digits Converted to Devanagari Numerals

- **Description**: Numeric digits (0-9) present in the Hinglish input are automatically converted into native Devanagari numerals (`०, १, २, ३, ४, ५, ६, ७, ८, ९`). In contemporary Hindi writing (digital interfaces, newspapers, formal documents), standard ASCII/Arabic numerals are standard.
- **Real Examples from `results.csv`**:
  - **Row 25**:
    - **Hinglish Input**: `mujhe 500 rupees chahiye`
    - **Reference Hindi**: `मुझे 500 रुपये चाहिए`
    - **Output Hindi**: `मुझे ५०० रुपीस चाहिए`
    - **Output English**: `I need 500 rupees.`
    - _(Metrics: Strict CER = 0.2500, Exact Match = 0)_
  - **Row 28**:
    - **Hinglish Input**: `is semester mein 5 subjects hain`
    - **Reference Hindi**: `इस सेमेस्टर में 5 सब्जेक्ट्स हैं`
    - **Output Hindi**: `इस सेमेस्टर में ५ सब्जेक्ट हैं`
    - **Output English**: `There are 5 subjects in this semester.`
    - _(Metrics: Strict CER = 0.0938, Exact Match = 0)_
  - **Row 29**:
    - **Hinglish Input**: `bill 1250 rupees ka aaya hai`
    - **Reference Hindi**: `बिल 1250 रुपये का आया है`
    - **Output Hindi**: `बिल १२५० रुपीस का आया है`
    - **Output English**: `The bill has come for 1250 rupees.`
    - _(Metrics: Strict CER = 0.2500, Exact Match = 0)_
  - **Row 34**:
    - **Hinglish Input**: `abhi aata hoon bhai, bas 2 minute`
    - **Reference Hindi**: `अभी आता हूँ भाई, बस 2 मिनट`
    - **Output Hindi**: `अभी आता हूँ भाई, बस २ मिन्यूट`
    - **Output English**: `I'll be right back, brother, just 2 minutes.`
    - _(Metrics: Strict CER = 0.1538, Exact Match = 0)_
- **Likely Cause**: `IndicXlit`'s character translation tables map ASCII numbers `0-9` to Devanagari Unicode code points `U+0966` through `U+096F`.
- **Possible Fix**: Add a simple post-processing character map to convert Devanagari digits back to ASCII numerals:
  ```python
  text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
  ```

---

### d. English Loanword Spelling Variants

- **Description**: English loanwords embedded in Hinglish sentences (such as "rupees", "idea", "minute") are transliterated either letter-by-letter or with unexpected vowel choices, diverging from accepted Hindi loanword conventions.
- **Real Examples from `results.csv`**:
  - **Row 25**:
    - **Hinglish Input**: `mujhe 500 rupees chahiye`
    - **Reference Hindi**: `मुझे 500 रुपये चाहिए`
    - **Output Hindi**: `मुझे ५०० रुपीस चाहिए`
    - **Output English**: `I need 500 rupees.`
    - _(Loanword "rupees" transliterated as "रुपीस" rather than standard Hindi "रुपये")_
  - **Row 32**:
    - **Hinglish Input**: `arre wah, mast idea hai`
    - **Reference Hindi**: `अरे वाह, मस्त आइडिया है`
    - **Output Hindi**: `अर्रे वाह, मस्त आईडीईए है`
    - **Output English**: `Oh wow, that's a great IDEA.`
    - _(Loanword "idea" transliterated letter-by-letter as "आईडीईए" [I-D-E-A] instead of phonetic "आइडिया")_
  - **Row 34**:
    - **Hinglish Input**: `abhi aata hoon bhai, bas 2 minute`
    - **Reference Hindi**: `अभी आता हूँ भाई, बस 2 मिनट`
    - **Output Hindi**: `अभी आता हूँ भाई, बस २ मिन्यूट`
    - **Output English**: `I'll be right back, brother, just 2 minutes.`
    - _(Loanword "minute" transliterated as "मिन्यूट" rather than standard "मिनट")_
- **Likely Cause**: `IndicXlit` relies on general phonetic sequence modeling without a lexicon of frequent English loanwords. When an English spelling exhibits non-transparent orthography (e.g., `idea` or `minute`), the model produces unnatural transliterations.
- **Possible Fix**: Maintain a small bilingual substitution dictionary for high-frequency English loanwords in Hinglish (`rupees` -> `रुपये`, `idea` -> `आइडिया`, `minute` -> `मिनट`).

---

### e. City and Place Names

- **Description**: Proper nouns, especially Indian city names and administrative entities, have standard historical and regional Devanagari spellings that differ from phonetic mappings of their English forms.
- **Real Examples from `results.csv`**:
  - **Row 22**:
    - **Hinglish Input**: `Amit ki shaadi Delhi mein hai`
    - **Reference Hindi**: `अमित की शादी दिल्ली में है`
    - **Output Hindi**: `अमित की शादी डेल्ही में है`
    - **Output English**: `Amit's wedding is in Delhi.`
    - _(Strict CER = 0.1154; transliterated as "डेल्ही" instead of standard "दिल्ली")_
  - **Row 20**:
    - **Hinglish Input**: `Rahul Mysuru se aa raha hai`
    - **Reference Hindi**: `राहुल मैसूरु से आ रहा है`
    - **Output Hindi**: `राहुल मैसूरू से आ रहा है`
    - **Output English**: `Rahul is coming from Mysuru.`
    - _(Strict CER = 0.0417; short vowel `मैसूरु` vs. long vowel `मैसूरू`)_
  - **Row 21**:
    - **Hinglish Input**: `Priya ne Bangalore mein job li hai`
    - **Reference Hindi**: `प्रिया ने बैंगलोर में जॉब ली है`
    - **Output Hindi**: `प्रिय ने बैंगलोर में जॉब ली है`
    - **Output English**: `Priya has taken a job in Bangalore.`
    - _("Bangalore" matched correctly as "बैंगलोर", but the person name "Priya" lost its final vowel and became "प्रिय")_
  - **Row 23**:
    - **Hinglish Input**: `Sneha aur Karthik kal Chennai ja rahe hain`
    - **Reference Hindi**: `स्नेहा और कार्तिक कल चेन्नई जा रहे हैं`
    - **Output Hindi**: `स्नेह और कार्तिक कल चेन्नई जा रहे हैं`
    - **Output English**: `Sneh and Kartik are leaving for Chennai tomorrow.`
    - _("Chennai" matched correctly as "चेन्नई", but "Sneha" dropped the final vowel to become "स्नेह")_
  - **Row 24**:
    - **Hinglish Input**: `Dr Sharma ka lecture kal Mysore University mein hai`
    - **Reference Hindi**: `डॉ. शर्मा का लेक्चर कल मैसूर यूनिवर्सिटी में है`
    - **Output Hindi**: `डीआर शर्मा का लेक्चर कल मैसूर यूनिवर्सिटी में है`
    - **Output English**: `DR Sharma's lecture is tomorrow at the University of Mysore.`
    - _("Mysore" matched "मैसूर", but honorific "Dr" was transliterated as "डीआर" rather than "डॉ." or "डॉक्टर")_
- **Likely Cause**: The transliteration engine does not incorporate a dedicated geographical gazetteer. It transliterates `Delhi` character-by-character as `डेल्ही` rather than mapping it to the standard Hindi lemma `दिल्ली`.
- **Possible Fix**: Integrate a curated gazetteer / dictionary for major Indian cities, states, and honorific abbreviations (`Delhi` -> `दिल्ली`, `Dr` -> `डॉ.`).

---

### f. Ambiguous Words Causing Meaning Errors

- **Description**: Words spelled in Latin script that can represent either an English word or an Indian regional word can cause severe semantic misinterpretations.
- **Real Example from `results.csv`**:
  - **Row 14**:
    - **Hinglish Input**: `meeting ka time change ho gaya hai`
    - **Reference Hindi**: `मीटिंग का टाइम चेंज हो गया है`
    - **Output Hindi**: `मीटिंग का टाइम चंगे हो गया है`
    - **Reference English**: `The meeting time has changed`
    - **Output English**: `The time of the meeting has become good.`
    - _(Strict CER = 0.1034, chrF = 43.47)_
- **Likely Cause**: The English word `change` was transliterated by `IndicXlit` into `चंगे` (a Punjabi/Hindi word meaning "good/fine", as in _changey_). Downstream, `IndicTrans2` interpreted `चंगे हो गया है` as "has become good".
- **Possible Fix**: Disambiguate common English action verbs/nouns in code-mixed text using an English-origin lexicon or language identification before transliteration.

---

### g. Translation Style Differences (Not Real Errors)

- **Description**: The translation model frequently outputs natural and semantically correct English translations that diverge stylistically from the single reference sentence, resulting in artificially depressed automated translation metrics (chrF / BLEU).
- **Real Examples from `results.csv`**:
  - **Row 34**:
    - **Hinglish Input**: `abhi aata hoon bhai, bas 2 minute`
    - **Reference Hindi**: `अभी आता हूँ भाई, बस 2 मिनट`
    - **Output Hindi**: `अभी आता हूँ भाई, बस २ मिन्यूट`
    - **Reference English**: `Coming right away brother, just 2 minutes`
    - **Output English**: `I'll be right back, brother, just 2 minutes.`
    - _(chrF = 60.88; "I'll be right back" is a fully natural colloquial equivalent of "Coming right away", but penalized by string overlap metrics)_
  - **Row 38**:
    - **Hinglish Input**: `main theek hun`
    - **Reference Hindi**: `मैं ठीक हूँ`
    - **Output Hindi**: `मैं ठीक हुन`
    - **Reference English**: `I am fine`
    - **Output English**: `I'll be alright`
    - _(chrF = 8.13; "I'll be alright" conveys the intended communicative meaning, but shares virtually no character n-grams with "I am fine")_
  - **Row 3**:
    - **Hinglish Input**: `kal milte hain`
    - **Reference Hindi**: `कल मिलते हैं`
    - **Output Hindi**: `कल मिलते हैं` _(Exact match = 1)_
    - **Reference English**: `We will meet tomorrow`
    - **Output English**: `See you tomorrow`
    - _(chrF = 39.52; despite a 100% exact match in Hindi, the natural colloquial English translation "See you tomorrow" scores only 39.52 chrF against "We will meet tomorrow")_
- **Likely Cause**: Standard n-gram metrics (BLEU, chrF) compare hypotheses against a single reference sentence without semantic embeddings.
- **Possible Fix**: Provide multiple reference translations per test item, or use semantic evaluation metrics such as COMET or BERTScore.

---

### Detailed Case Analysis: Row 12, Rows 36 vs 37, and Rows 38 vs 39

#### 1. Row 12: Grammatical Gender Agreement (`नया` vs. `नई`)

- **Hinglish Input**: `hamare college mein is saal naya library ban raha hai`
- **Reference Hindi**: `हमारे कॉलेज में इस साल नई लाइब्रेरी बन रही है`
- **Output Hindi**: `हमारे कॉलेज में इस साल नया लाइब्रेरी बन रहा है`
- **Reference English**: `A new library is being built in our college this year`
- **Output English**: `A new library is coming up in our college this year`
- **What Actually Happened**:
  In the input Hinglish, the user used masculine agreement markers: `naya library ban raha hai`. The transliteration engine (`IndicXlit`) faithfully converted each word phonetically into Devanagari (`नया लाइब्रेरी बन रहा है`), preserving the masculine gender markers from the prompt. In standard Hindi, the borrowed noun "लाइब्रेरी" (library) is typically feminine, which is why the human-verified reference uses feminine agreement (`नई लाइब्रेरी बन रही है`).
  Because `IndicXlit` is purely an orthographic transliteration tool without grammatical parsing, it did not correct the gender agreement. However, downstream in the translation stage, `IndicTrans2` handled the sentence gracefully, translating it into natural English (`A new library is coming up in our college this year`, achieving a chrF of 72.37).

#### 2. Rows 36 vs. 37: Standard vs. SMS Negation and Knowledge

- **Row 36**:
  - **Hinglish**: `mujhe nahi pata`
  - **Reference Hindi**: `मुझे नहीं पता`
  - **Output Hindi**: `मुझे नही पता`
  - **Output English**: `I don't know`
  - **chrF**: 100.0, **CER strict**: 0.0769
- **Row 37**:
  - **Hinglish**: `mujhe nhi pta`
  - **Reference Hindi**: `मुझे नहीं पता`
  - **Output Hindi**: `मुझे नही पीटीए`
  - **Output English**: `I don't have a PTA.`
  - **chrF**: 38.68, **CER strict**: 0.3846
- **What Actually Happened**:
  For the standard spelling in Row 36, the pipeline produced clean Hindi (`मुझे नही पता`, differing from reference only by the anusvara on `नहीं`) and an exact English translation (`I don't know`, chrF 100.0). In Row 37, when given the SMS shorthand `nhi pta`, `IndicXlit` failed on `pta`, transliterating it as the capitalized English abbreviation `पीटीए` (PTA). `IndicTrans2` then translated the corrupted Hindi string into `I don't have a PTA.`.

#### 3. Rows 38 vs. 39: Standard vs. Phonetically Simplified Well-Being

- **Row 38**:
  - **Hinglish**: `main theek hun`
  - **Reference Hindi**: `मैं ठीक हूँ`
  - **Output Hindi**: `मैं ठीक हुन`
  - **Output English**: `I'll be alright`
  - **chrF**: 8.13, **CER strict**: 0.1818
- **Row 39**:
  - **Hinglish**: `mai thik hu`
  - **Reference Hindi**: `मैं ठीक हूँ`
  - **Output Hindi**: `मई थिक हू`
  - **Output English**: `May is fine.`
  - **chrF**: 28.14, **CER strict**: 0.4545
- **What Actually Happened**:
  In Row 38, `main theek hun` was transliterated as `मैं ठीक हुन` (preserving the root word `ठीक`), which translated to the valid colloquial English sentence `I'll be alright`. In Row 39, the shortened informal spelling `mai thik hu` led `IndicXlit` to map `mai` to the calendar month "May" (`मई`) and `thik` to `थिक` (with dental `थ` instead of retroflex `ठ`). `IndicTrans2` subsequently translated `मई थिक हू` as `May is fine.`.

---

## 4. Spelling Robustness Finding

A direct comparison of the test case pairs demonstrates the pipeline's lack of spelling robustness:

|    Pair     |    Form    | Hinglish Input                        | Output Hindi                        | Output English                           | Same Hindi Produced? |
| :---------: | :--------: | :------------------------------------ | :---------------------------------- | :--------------------------------------- | :------------------: |
| **36 / 37** | Full / SMS | `mujhe nahi pata` vs. `mujhe nhi pta` | `मुझे नही पता` vs. `मुझे नही पीटीए` | `I don't know` vs. `I don't have a PTA.` |        **NO**        |
| **38 / 39** | Full / SMS | `main theek hun` vs. `mai thik hu`    | `मैं ठीक हुन` vs. `मई थिक हू`       | `I'll be alright` vs. `May is fine.`     |        **NO**        |

### Key Takeaway

**The baseline pipeline does NOT produce the same Hindi output for the same underlying meaning when informal or SMS spellings are used.**

- In pair 36/37, omitting vowels in `pta` causes the system to switch from a verb of knowing (`पता`) to an acronym (`पीटीए`).
- In pair 38/39, using `mai` instead of `main` causes the system to switch from a first-person pronoun (`मैं`) to a calendar month (`मई`).

Because the transliteration model lacks an informal abbreviation expansion module, small spelling variations introduce severe semantic drift and downstream translation errors.

---

## 5. Limitations

1. **Small Test Suite (40 Test Cases)**:
   The evaluation suite contains 40 sentences across 7 categories. While valuable for diagnostic categorization, a sample size of 5 to 7 sentences per category is too small to draw statistically conclusive conclusions or establish narrow confidence intervals.
2. **AI-Drafted References**:
   The reference sentences were generated with AI assistance before human checking. Subtleties in stylistic preference or colloquial phrasing in the references can skew strict character and n-gram overlap metrics.
3. **Single Reference Per Sentence**:
   Evaluating translation and transliteration against a single reference sentence introduces artificial penalties for valid synonyms, stylistic choices, and alternate spelling conventions (e.g., `We will meet tomorrow` vs. `See you tomorrow`).
4. **Phrasing Step (Gemini) Not Evaluated in Baseline**:
   The baseline evaluation was run strictly with phrasing disabled (`PHRASING_BACKEND=none`). The actual capability of the phrasing refinement module (`improve_phrasing`) to correct transliteration errors remains unmeasured in this report.
5. **Dependency on External API**:
   The phrasing enhancement backend relies on an external REST API (Gemini). During preliminary testing, external requests encountered network interruptions and `503 Service Unavailable` errors, highlighting the fragility of relying on real-time external APIs in an interactive writing assistant pipeline.
6. **Human Verification Audit Status**:
   In `data/test_cases.csv`, specific names in the `verified_by` column are currently unpopulated (marked as **to be checked**).

---

## 6. Proposed Improvements

To address the failure modes identified above without adding heavyweight dependencies, the following four improvements are proposed:

1. **Devanagari to ASCII Digit Post-Processing**:
   Implement a post-transliteration mapping that converts Devanagari numerals (`०-९`) back to standard Arabic/ASCII digits (`0-9`). This single change will immediately resolve digit mismatches across rows 25, 26, 27, 28, 29, and 34, substantially reducing strict CER in the `numbers` category.
2. **Common City Names and English Loanwords Dictionary**:
   Implement a lightweight lookup dictionary for proper nouns and frequent loanwords that `IndicXlit` consistently mishandles:
   - Cities & Places: `Delhi` -> `दिल्ली` (fixes Row 22).
   - Honorifics: `Dr` / `Dr.` -> `डॉ.` (fixes Row 24).
   - Loanwords & Currency: `change` -> `चेंज` (fixes Row 14), `idea` -> `आइडिया` (fixes Row 32), `minute` -> `मिनट` (fixes Row 34), `rupees` -> `रुपये` (fixes Rows 25, 29).
3. **SMS / Informal Spelling Normalisation Layer**:
   Insert a fast rule-based pre-transliteration step to expand colloquial chat abbreviations to standard Hinglish:
   - `nhi` -> `nahi`
   - `pta` -> `pata`
   - `mai` -> `main`
   - `thik` -> `theek`
   - `hu` / `hun` -> `hoon`
     This will directly eliminate catastrophic failures in rows 37 and 39.
4. **Re-Evaluation Benchmark**:
   Re-run the evaluation script across all 40 test cases after deploying these pre- and post-processing modules to quantitatively measure the reduction in strict CER, word error rate, and the improvement in corpus chrF and exact match rate.

*(Note: See [Section 7](#7-before-vs-after-normalisation-improvement-round) below for the empirical results of this re-evaluation benchmark following the implementation of fixes 1 and 3.)*

---

## 7. Before vs After: Normalisation Improvement Round

### 7.1 Overview of Implemented Normalisation Fixes

To target the most severe failure modes identified in Section 3 without introducing heavyweight model dependencies or training new architectures, two targeted pre- and post-processing improvements were implemented in `src/normalize.py`:

1. **Pre-Transliteration SMS Spelling Normalisation** (`normalize_sms`):
   Applied before passing input to AI4Bharat `IndicXlit`. It canonicalizes common informal Roman chat abbreviations and phonetic shorthands to standard Roman Hinglish using whole-word regex matching (`\b[a-zA-Z]+\b`). Examples include:
   - `nhi` / `nahin` $\to$ `nahi`
   - `pta` $\to$ `pata` (prevents acronym mistransliteration `PTA` / `पीटीए`)
   - `mai` $\to$ `main` (prevents mistransliterating pronoun "I" as calendar month "May" / `मई`)
   - `thik` $\to$ `theek` (prevents dental `थ` in `थिक` instead of retroflex `ठ` in `ठीक`)
   - `hu` / `hun` $\to$ `hoon`
   - `kyaa` $\to$ `kya`, `mujhey` / `muje` $\to$ `mujhe`, and `h` $\to$ `hai`

2. **Post-Transliteration Devanagari-to-ASCII Digit Conversion** (`devanagari_to_ascii_digits`):
   Applied immediately after `IndicXlit` transliteration. It converts native Devanagari numerals (`०, १, २, ३, ४, ५, ६, ७, ८, ९`) back to standard ASCII/Arabic digits (`0-9`) via Unicode character translation table (`str.maketrans`).

The baseline pipeline behavior (normalisation disabled) remains fully reproducible by setting the environment variable `HINGLISH_NORMALIZE=0` or passing the `--no-normalize` flag to `eval/run_eval.py`.

---

### 7.2 Overall Performance Comparison

The following table compares the baseline evaluation (`eval/results.csv`, normalisation OFF) with the normalised pipeline (`eval/results_normalized.csv`, normalisation ON) across all 40 test cases:

| Metric | Baseline (Norm OFF) | Normalised (Norm ON) | Absolute Change | Relative Change (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Strict CER (%)** | 7.00% | 4.88% | -2.12% | -30.29% |
| **Normalised CER (%)** | 6.67% | 4.54% | -2.13% | -31.93% |
| **Strict Word Accuracy (1 - WER) (%)** | 81.85% | 86.29% | +4.44% | +5.42% |
| **Normalised Word Accuracy (1 - WER) (%)** | 83.47% | 87.90% | +4.43% | +5.31% |
| **Strict Exact Match** | 14 / 40 (35.0%) | 17 / 40 (42.5%) | +3 (+7.5%) | +21.43% |
| **Corpus chrF** | 65.18 | 65.58 | +0.40 | +0.61% |
| **Corpus BLEU** | 38.53 | 39.50 | +0.97 | +2.52% |

---

### 7.3 Per-Category Strict CER Comparison

The table below breaks down the strict Character Error Rate (CER) across all 7 evaluation categories:

| Category | Test Count | Baseline Strict CER (%) | Normalised Strict CER (%) | Absolute Change | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `spelling` | 5 | 20.31% (13 / 64) | 3.12% (2 / 64) | -17.19% | Substantial improvement |
| `numbers` | 5 | 14.75% (18 / 122) | 5.74% (7 / 122) | -9.01% | Substantial improvement |
| `slang` | 6 | 8.63% (12 / 139) | 7.91% (11 / 139) | -0.72% | Minor improvement (Row 34 digit fix) |
| `long` | 6 | 5.75% (18 / 313) | 5.75% (18 / 313) | 0.00% | Unchanged |
| `names` | 5 | 5.42% (9 / 166) | 5.42% (9 / 166) | 0.00% | Unchanged |
| `english_mix` | 7 | 2.55% (5 / 196) | 2.55% (5 / 196) | 0.00% | Unchanged |
| `short` | 6 | 1.16% (1 / 86) | 1.16% (1 / 86) | 0.00% | Unchanged |

---

### 7.4 Row-Level Examples: Before vs After

The following row examples from `eval/results.csv` and `eval/results_normalized.csv` illustrate the concrete effects of digit mapping and SMS spelling expansion:

#### 1. Row 25 (`numbers`)
- **Hinglish Input**: `mujhe 500 rupees chahiye`
- **Reference Hindi**: `मुझे 500 रुपये चाहिए`
- **Output Hindi (Before)**: `मुझे ५०० रुपीस चाहिए`
- **Output Hindi (After)**: `मुझे 500 रुपीस चाहिए`
- **Reference English**: `I need 500 rupees`
- **Output English (Before)**: `I need 500 rupees.`
- **Output English (After)**: `I need 500 rupees.`
- **Analysis**: Strict CER dropped from 0.25 (25.00%) to 0.10 (10.00%). Devanagari numerals `५००` were successfully converted to ASCII `500`. However, the English loanword `rupees` remains transliterated as `रुपीस` instead of standard Hindi `रुपये`.

#### 2. Row 29 (`numbers`)
- **Hinglish Input**: `bill 1250 rupees ka aaya hai`
- **Reference Hindi**: `बिल 1250 रुपये का आया है`
- **Output Hindi (Before)**: `बिल १२५० रुपीस का आया है`
- **Output Hindi (After)**: `बिल 1250 रुपीस का आया है`
- **Reference English**: `The bill has come to 1250 rupees`
- **Output English (Before)**: `The bill has come for 1250 rupees.`
- **Output English (After)**: `The bill has come for 1250 rupees.`
- **Analysis**: Strict CER dropped from 0.25 (25.00%) to 0.0833 (8.33%). The digits `१२५०` were converted back to ASCII `1250`, while `rupees` remained `रुपीस`.

#### 3. Row 37 (`spelling`)
- **Hinglish Input**: `mujhe nhi pta`
- **Reference Hindi**: `मुझे नहीं पता`
- **Output Hindi (Before)**: `मुझे नही पीटीए`
- **Output Hindi (After)**: `मुझे नही पता`
- **Reference English**: `I don't know`
- **Output English (Before)**: `I don't have a PTA.`
- **Output English (After)**: `I don't know`
- **Analysis**: Strict CER decreased from 0.3846 (38.46%) to 0.0769 (7.69%). Pre-normalising `nhi` $\to$ `nahi` and `pta` $\to$ `pata` resolved the catastrophic mistransliteration of `pta` as the acronym `पीटीए`. Downstream, `IndicTrans2` flipped from producing the nonsensical English sentence "I don't have a PTA." (chrF 38.68) to the exact reference translation "I don't know" (chrF 100.0).

#### 4. Row 39 (`spelling`)
- **Hinglish Input**: `mai thik hu`
- **Reference Hindi**: `मैं ठीक हूँ`
- **Output Hindi (Before)**: `मई थिक हू`
- **Output Hindi (After)**: `मैं ठीक हूँ`
- **Reference English**: `I am fine`
- **Output English (Before)**: `May is fine.`
- **Output English (After)**: `I'm alright.`
- **Analysis**: Strict CER dropped from 0.4545 (45.45%) to 0.00% (an exact match). Canonicalizing `mai` $\to$ `main`, `thik` $\to$ `theek`, and `hu` $\to$ `hoon` fixed the pronoun-to-calendar-month error (`मई` $\to$ `मैं`) and the dental consonant error (`थिक` $\to$ `ठीक`). In translation, the output changed from "May is fine." to the valid colloquial translation "I'm alright.".

---

### 7.5 What Did Not Improve (Underlying Model Limitations)

While lexical normalisation resolved isolated numeral representations and frequent SMS abbreviations, several error classes remained entirely unaffected. These reflect intrinsic limitations of the underlying transliteration and translation models (`IndicXlit` and `IndicTrans2`) that cannot be addressed by shallow string rules:

1. **Proper Names & City Names (Rows 21, 22, 23)**:
   - **Row 21**: `Priya` transliterated as `प्रिय` instead of `प्रिया` (loss of terminal vowel `a`).
   - **Row 22**: `Delhi` transliterated phonetically as `डेल्ही` instead of standard Hindi lemma `दिल्ली`.
   - **Row 23**: `Sneha` transliterated as `स्नेह` instead of `स्नेहा` (loss of terminal vowel `a`).
   - *Reason*: `IndicXlit` lacks an Indian named entity gazetteer and applies generic phonetic decomposition to proper nouns.

2. **English Loanword Transliterations (Rows 25, 32, 34)**:
   - **Row 25 & 29**: `rupees` transliterated phonetically as `रुपीस` rather than Hindi `रुपये`.
   - **Row 32**: `idea` transliterated letter-by-letter as `आईडीईए` ("I-D-E-A") rather than standard `आइडिया`.
   - **Row 34**: `minute` transliterated as `मिन्यूट` rather than standard `मिनट`.
   - *Reason*: `IndicXlit` has no loanword vocabulary to reconcile non-phonetic English orthography with conventional Devanagari loanword forms.

3. **Cross-Lingual Semantic Ambiguity (Row 14)**:
   - **Row 14**: `meeting ka time change ho gaya hai` $\to$ `मीटिंग का टाइम चंगे हो गया है` $\to$ *"The time of the meeting has become good."*
   - *Reason*: The English verb/noun `change` is homographic with the Romanized Punjabi/Hindi adjective *changey* (`चंगे`, meaning good/fine). Without context-aware language identification or semantic disambiguation, the pipeline selects the regional meaning.

4. **Grammatical Gender Agreement (Row 12)**:
   - **Row 12**: `hamare college mein is saal naya library ban raha hai` $\to$ `हमारे कॉलेज में इस साल नया लाइब्रेरी बन रहा है` (reference: `नई लाइब्रेरी बन रही है`).
   - *Reason*: Transliteration operates strictly character-by-character without syntactic or grammatical parsing. It faithfully reproduces the user's incorrect masculine agreement (`naya` $\to$ `नया`, `ban raha hai` $\to$ `बन रहा है`), unable to enforce the feminine gender of borrowed noun `लाइब्रेरी`.

5. **Phonetic Distortion in Family Terms (Row 10)**:
   - **Row 10**: `meri behen ne kaha...` $\to$ `मेरी बेहें ने कहा...` $\to$ *"My sister-in-law said..."*.
   - *Reason*: `IndicXlit` transliterates `behen` with an unintended nasalized vowel (`बेहें` instead of standard `बहन`). `IndicTrans2` subsequently interprets `बेहें` as "sister-in-law" rather than "sister", severely altering the sentence meaning.

6. **Standard vs. Informal Nasalization in Negation (Row 36)**:
   - **Row 36**: `mujhe nahi pata` $\to$ `मुझे नही पता` (reference: `मुझे नहीं पता`, strict CER = 0.0769).
   - *Reason*: `IndicXlit` consistently omits the anusvara on `नही`. Because `normalize_sms` only rewrites `nhi` $\to$ `nahi`, the input `nahi` remains unmodified and continues to generate `नही`.

---

### 7.6 Limitations of the Normalisation Fix

1. **Small, Rule-Based Dictionary (Not a Model Improvement)**:
   The fix consists of a curated 11-word dictionary in `src/normalize.py` and a regex character map. It does not enhance the generalization or vocabulary of the underlying neural models (`IndicXlit`, `IndicTrans2`). Unseen abbreviations or alternative phonetic spellings (e.g. `nhii`, `knw`, `msg`) remain unhandled.
2. **Side Effects of the Standalone `"h" -> "hai"` Rule**:
   The word-boundary replacement for the single letter `h` (`\bh\b` $\to$ `hai`) carries risk in general text. While intended to expand the colloquial single-letter Hindi copula ("kya scene h" $\to$ "kya scene hai"), it can unintentionally corrupt English middle initials (e.g., "John H. Smith"), single-letter variable names, or abbreviations.
3. **Risk of Overfitting to the Test Set**:
   The dictionary entries were selected based on the specific error patterns observed in the 40 test cases of `data/test_cases.csv`. A clean held-out test suite with independent Hinglish inputs is required to verify that these rules generalize and do not cause regressions on broader conversational text.
4. **Single-Run Benchmark**:
   All reported metrics originate from a single deterministic evaluation pass over the 40 test cases.
