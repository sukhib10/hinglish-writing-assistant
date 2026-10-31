"""
Test script for the modular Hinglish Writing Assistant pipeline.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import run_pipeline


def main():
    test_input = "mujhe kal university jaana hai"
    print("=" * 60)
    print(f"Testing Hinglish Writing Assistant Pipeline")
    print(f"Input Text: '{test_input}'")
    print("=" * 60)
    
    # Run pipeline with both improve and translate flags enabled
    result = run_pipeline(test_input, improve=True, translate=True)
    
    print("\n--- Pipeline Stage Outputs ---")
    print(f"Stage 0 (Original Input):        {result['input']}")
    print(f"Stage 1 (IndicXlit Hindi):       {result['transliterated']}")
    print(f"Stage 2 (Phrasing Improvement):  {result['improved']}")
    print(f"Stage 3 (IndicTrans2 English):   {result['translated']}")
    print("=" * 60)
    print("Pipeline test completed successfully!")


if __name__ == "__main__":
    main()
