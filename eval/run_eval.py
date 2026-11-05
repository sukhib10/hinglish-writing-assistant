"""
Evaluation script for Hinglish Writing Assistant.

Features:
1. Runs Hinglish inputs through transliterate() and translate_to_english().
   Phrasing improvement is OFF by default (PHRASING_BACKEND=none inside the script);
   an optional --phrasing flag runs improve_phrasing() between them.
2. Computes Hindi scores with jiwer:
   - Character Error Rate (CER)
   - Word Accuracy (1 - WER)
   Computed in two modes:
     a) Strict (exact strings)
     b) Normalised (removes nukta ़, replaces ँ with ं, strips punctuation & extra spaces)
3. Computes English translation scores with sacrebleu:
   - chrF (sentence-level & corpus-level)
   - BLEU (sentence-level & corpus-level)
4. Saves per-row results to eval/results.csv in UTF-8 with BOM:
   Columns: id, category, hinglish, reference_hindi, output_hindi,
            CER strict, CER normalised, exact match, reference_english,
            output_english, chrF
5. Prints overall metrics, per-category breakdown, and top 10 worst rows by CER.
"""

import argparse
import csv
import os
import re
import string
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Add project root directory to sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set default phrasing backend to none inside script
if "PHRASING_BACKEND" not in os.environ:
    os.environ["PHRASING_BACKEND"] = "none"

try:
    import jiwer
except ImportError:
    jiwer = None

try:
    import sacrebleu
except ImportError:
    sacrebleu = None


def normalize_hindi(text: str) -> str:
    """
    Normalises Hindi text for robust evaluation:
    1. Removes nukta (़, U+093C), handling both decomposed and precomposed forms.
    2. Replaces candrabindu (ँ, U+0901) with anusvara (ं, U+0902).
    3. Strips punctuation (Unicode category 'P*' and ASCII punctuation, including danda ।).
    4. Strips extra whitespace.
    """
    if not text:
        return ""

    # 1. Decompose to separate base characters and combining nukta (U+093C)
    text = unicodedata.normalize("NFD", text)
    # Remove nukta
    text = text.replace("\u093c", "")
    # Recompose to standard NFC
    text = unicodedata.normalize("NFC", text)

    # 2. Replace candrabindu with anusvara
    text = text.replace("\u0901", "\u0902")

    # 3. Strip punctuation
    text = "".join(
        c for c in text
        if not (unicodedata.category(c).startswith("P") or c in string.punctuation)
    )

    # 4. Collapse multiple spaces and strip leading/trailing whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def evaluate_dataset(
    data_path: Path,
    output_path: Path,
    use_phrasing: bool = False
) -> None:
    """
    Runs the pipeline over the evaluation dataset and computes metrics.
    """
    if jiwer is None:
        raise ImportError(
            "Package 'jiwer' is not installed. Please install jiwer to run evaluation."
        )
    if sacrebleu is None:
        raise ImportError(
            "Package 'sacrebleu' is not installed. Please install sacrebleu to run evaluation."
        )

    # Set PHRASING_BACKEND based on flag
    if not use_phrasing:
        os.environ["PHRASING_BACKEND"] = "none"

    # Import pipeline functions
    from src.pipeline import transliterate, improve_phrasing, translate_to_english

    # Read test cases (UTF-8 with BOM)
    if not data_path.exists():
        raise FileNotFoundError(f"Test cases file not found at: {data_path}")

    rows = []
    with open(data_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    total_rows = len(rows)
    print("=" * 80)
    print("              HINGLISH WRITING ASSISTANT - PIPELINE EVALUATION")
    print("=" * 80)
    print(f"Dataset Path        : {data_path}")
    print(f"Total Test Cases    : {total_rows}")
    phrasing_status = (
        f"ON (using {os.environ.get('PHRASING_BACKEND', 'gemini')})"
        if use_phrasing
        else "OFF (PHRASING_BACKEND=none)"
    )
    print(f"Phrasing Improvement: {phrasing_status}")
    print(f"Output CSV Path     : {output_path}")
    print("=" * 80)
    print("Running pipeline inference across all test cases...\n")

    # Storage for per-row records and evaluation aggregates
    results_records = []
    category_data = defaultdict(lambda: {
        "ref_hindi": [],
        "out_hindi": [],
        "ref_hindi_norm": [],
        "out_hindi_norm": [],
        "ref_english": [],
        "out_english": [],
        "exact_matches_strict": 0,
        "exact_matches_norm": 0,
        "cer_strict_list": [],
        "cer_norm_list": [],
        "word_acc_strict_list": [],
        "word_acc_norm_list": [],
        "chrf_list": [],
        "bleu_list": [],
        "count": 0,
    })

    all_ref_hindi = []
    all_out_hindi = []
    all_ref_hindi_norm = []
    all_out_hindi_norm = []
    all_ref_english = []
    all_out_english = []

    for idx, row in enumerate(rows, start=1):
        test_id = row.get("id", str(idx))
        category = row.get("category", "default").strip()
        hinglish_input = row.get("hinglish", "").strip()
        ref_hindi = row.get("reference_hindi", "").strip()
        ref_english = row.get("reference_english", "").strip()

        # Step 1: Transliterate
        raw_hindi = transliterate(hinglish_input)

        # Step 2: Phrasing (optional)
        if use_phrasing:
            out_hindi = improve_phrasing(raw_hindi)
        else:
            out_hindi = raw_hindi

        # Step 3: Translate to English
        out_english = translate_to_english(out_hindi)

        # Normalised forms for Hindi
        ref_hindi_norm = normalize_hindi(ref_hindi)
        out_hindi_norm = normalize_hindi(out_hindi)

        # Compute Hindi metrics (Strict)
        cer_strict = float(jiwer.cer(ref_hindi, out_hindi))
        wer_strict = float(jiwer.wer(ref_hindi, out_hindi))
        word_acc_strict = 1.0 - wer_strict
        exact_match_strict = 1 if out_hindi.strip() == ref_hindi.strip() else 0

        # Compute Hindi metrics (Normalised)
        if not ref_hindi_norm and not out_hindi_norm:
            cer_norm = 0.0
            wer_norm = 0.0
        elif not ref_hindi_norm or not out_hindi_norm:
            cer_norm = 1.0
            wer_norm = 1.0
        else:
            cer_norm = float(jiwer.cer(ref_hindi_norm, out_hindi_norm))
            wer_norm = float(jiwer.wer(ref_hindi_norm, out_hindi_norm))
        word_acc_norm = 1.0 - wer_norm
        exact_match_norm = 1 if out_hindi_norm == ref_hindi_norm else 0

        # Compute English translation metrics (Sentence-level)
        sent_chrf = float(sacrebleu.sentence_chrf(out_english, [ref_english]).score)
        sent_bleu = float(sacrebleu.sentence_bleu(out_english, [ref_english]).score)

        # Record per-row result for eval/results.csv
        record = {
            "id": test_id,
            "category": category,
            "hinglish": hinglish_input,
            "reference_hindi": ref_hindi,
            "output_hindi": out_hindi,
            "CER strict": round(cer_strict, 4),
            "CER normalised": round(cer_norm, 4),
            "exact match": exact_match_strict,
            "reference_english": ref_english,
            "output_english": out_english,
            "chrF": round(sent_chrf, 2),
            # Auxiliary fields for failure analysis and category breakdown
            "word_acc_strict": word_acc_strict,
            "word_acc_norm": word_acc_norm,
            "exact_match_norm": exact_match_norm,
            "BLEU": round(sent_bleu, 2),
        }
        results_records.append(record)

        # Aggregate for overall corpus metrics
        all_ref_hindi.append(ref_hindi)
        all_out_hindi.append(out_hindi)
        all_ref_hindi_norm.append(ref_hindi_norm)
        all_out_hindi_norm.append(out_hindi_norm)
        all_ref_english.append(ref_english)
        all_out_english.append(out_english)

        # Aggregate for category metrics
        cat_dict = category_data[category]
        cat_dict["count"] += 1
        cat_dict["ref_hindi"].append(ref_hindi)
        cat_dict["out_hindi"].append(out_hindi)
        cat_dict["ref_hindi_norm"].append(ref_hindi_norm)
        cat_dict["out_hindi_norm"].append(out_hindi_norm)
        cat_dict["ref_english"].append(ref_english)
        cat_dict["out_english"].append(out_english)
        cat_dict["exact_matches_strict"] += exact_match_strict
        cat_dict["exact_matches_norm"] += exact_match_norm
        cat_dict["cer_strict_list"].append(cer_strict)
        cat_dict["cer_norm_list"].append(cer_norm)
        cat_dict["word_acc_strict_list"].append(word_acc_strict)
        cat_dict["word_acc_norm_list"].append(word_acc_norm)
        cat_dict["chrf_list"].append(sent_chrf)
        cat_dict["bleu_list"].append(sent_bleu)

        if idx % 10 == 0 or idx == total_rows:
            print(f"Processed {idx:2d}/{total_rows:2d} test cases...")

    # Write per-row results to eval/results.csv in UTF-8 with BOM
    output_path.parent.mkdir(parents=True, exist_ok=True)
    csv_fieldnames = [
        "id",
        "category",
        "hinglish",
        "reference_hindi",
        "output_hindi",
        "CER strict",
        "CER normalised",
        "exact match",
        "reference_english",
        "output_english",
        "chrF",
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in results_records:
            writer.writerow(rec)

    print(f"\nSuccessfully wrote per-row results to: {output_path}")

    # Compute Overall Corpus Metrics
    overall_cer_strict = float(jiwer.cer(all_ref_hindi, all_out_hindi))
    overall_wer_strict = float(jiwer.wer(all_ref_hindi, all_out_hindi))
    overall_word_acc_strict = 1.0 - overall_wer_strict

    overall_cer_norm = float(jiwer.cer(all_ref_hindi_norm, all_out_hindi_norm))
    overall_wer_norm = float(jiwer.wer(all_ref_hindi_norm, all_out_hindi_norm))
    overall_word_acc_norm = 1.0 - overall_wer_norm

    overall_exact_strict_count = sum(r["exact match"] for r in results_records)
    overall_exact_norm_count = sum(r["exact_match_norm"] for r in results_records)

    overall_corpus_chrf = float(
        sacrebleu.corpus_chrf(all_out_english, [all_ref_english]).score
    )
    overall_corpus_bleu = float(
        sacrebleu.corpus_bleu(all_out_english, [all_ref_english]).score
    )
    overall_avg_chrf = sum(r["chrF"] for r in results_records) / total_rows
    overall_avg_bleu = sum(r["BLEU"] for r in results_records) / total_rows

    # Print Overall Scores
    print("\n" + "=" * 80)
    print("                               OVERALL SCORES")
    print("=" * 80)
    print("--- Hindi Transliteration Metrics (jiwer) ---")
    print(f"  Strict CER                  : {overall_cer_strict:8.4f}  ({overall_cer_strict * 100:6.2f}%)")
    print(f"  Strict Word Accuracy (1-WER): {overall_word_acc_strict:8.4f}  ({overall_word_acc_strict * 100:6.2f}%)")
    print(f"  Strict Exact Match          : {overall_exact_strict_count:4d}/{total_rows:<4d} ({overall_exact_strict_count / total_rows * 100:6.2f}%)")
    print()
    print(f"  Normalised CER              : {overall_cer_norm:8.4f}  ({overall_cer_norm * 100:6.2f}%)")
    print(f"  Normalised Word Acc (1-WER) : {overall_word_acc_norm:8.4f}  ({overall_word_acc_norm * 100:6.2f}%)")
    print(f"  Normalised Exact Match      : {overall_exact_norm_count:4d}/{total_rows:<4d} ({overall_exact_norm_count / total_rows * 100:6.2f}%)")
    print()
    print("--- English Translation Metrics (sacrebleu) ---")
    print(f"  Corpus chrF                 : {overall_corpus_chrf:8.2f}")
    print(f"  Sentence chrF (average)     : {overall_avg_chrf:8.2f}")
    print(f"  Corpus BLEU                 : {overall_corpus_bleu:8.2f}")
    print(f"  Sentence BLEU (average)     : {overall_avg_bleu:8.2f}")
    print("=" * 80)

    # Print Scores Per Category
    print("\n" + "=" * 80)
    print("                            SCORES PER CATEGORY")
    print("=" * 80)
    header_fmt = "{:<13} {:>5} | {:>10} {:>10} | {:>10} {:>10} | {:>10} | {:>8} {:>8}"
    row_fmt = "{:<13} {:>5d} | {:>10.4f} {:>10.4f} | {:>10.4f} {:>10.4f} | {:>9.1f}% | {:>8.2f} {:>8.2f}"

    print(header_fmt.format(
        "Category", "Count", "CER(str)", "CER(norm)", "WAcc(str)", "WAcc(norm)", "ExactMatch", "chrF", "BLEU"
    ))
    print("-" * 80)

    for cat_name, cat in sorted(category_data.items()):
        c_count = cat["count"]
        # Category corpus CER / WER
        c_cer_strict = float(jiwer.cer(cat["ref_hindi"], cat["out_hindi"]))
        c_wer_strict = float(jiwer.wer(cat["ref_hindi"], cat["out_hindi"]))
        c_wacc_strict = 1.0 - c_wer_strict

        c_cer_norm = float(jiwer.cer(cat["ref_hindi_norm"], cat["out_hindi_norm"]))
        c_wer_norm = float(jiwer.wer(cat["ref_hindi_norm"], cat["out_hindi_norm"]))
        c_wacc_norm = 1.0 - c_wer_norm

        c_exact_pct = (cat["exact_matches_strict"] / c_count) * 100.0

        c_chrf = float(sacrebleu.corpus_chrf(cat["out_english"], [cat["ref_english"]]).score)
        c_bleu = float(sacrebleu.corpus_bleu(cat["out_english"], [cat["ref_english"]]).score)

        print(row_fmt.format(
            cat_name,
            c_count,
            c_cer_strict,
            c_cer_norm,
            c_wacc_strict,
            c_wacc_norm,
            c_exact_pct,
            c_chrf,
            c_bleu,
        ))
    print("=" * 80)

    # Print Top 10 Worst Rows by CER
    print("\n" + "=" * 80)
    print("                         TOP 10 WORST ROWS BY CER")
    print("=" * 80)

    # Sort descending by strict CER; tie-break on normalised CER descending
    sorted_by_cer = sorted(
        results_records,
        key=lambda r: (r["CER strict"], r["CER normalised"]),
        reverse=True
    )
    worst_10 = sorted_by_cer[:10]

    for rank, r in enumerate(worst_10, start=1):
        print(f"Rank {rank:2d} | Row ID: {r['id']} | Category: {r['category']}")
        print(f"  Hinglish Input   : {r['hinglish']}")
        print(f"  Reference Hindi  : {r['reference_hindi']}")
        print(f"  Output Hindi     : {r['output_hindi']}")
        print(f"  CER Strict       : {r['CER strict']:.4f}  | CER Normalised: {r['CER normalised']:.4f}  | Exact Match: {r['exact match']}")
        print(f"  Reference English: {r['reference_english']}")
        print(f"  Output English   : {r['output_english']}")
        print(f"  chrF             : {r['chrF']:.2f}  | BLEU: {r['BLEU']:.2f}")
        print("-" * 80)
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Hinglish Writing Assistant on test cases."
    )
    parser.add_argument(
        "--phrasing",
        action="store_true",
        help="Enable phrasing improvement stage (improve_phrasing) between transliteration and translation."
    )
    parser.add_argument(
        "--data",
        type=str,
        default=str(PROJECT_ROOT / "data" / "test_cases.csv"),
        help="Path to test cases CSV file (default: data/test_cases.csv)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "eval" / "results.csv"),
        help="Path to output results CSV file (default: eval/results.csv)."
    )

    args = parser.parse_args()

    evaluate_dataset(
        data_path=Path(args.data),
        output_path=Path(args.output),
        use_phrasing=args.phrasing,
    )


if __name__ == "__main__":
    main()
