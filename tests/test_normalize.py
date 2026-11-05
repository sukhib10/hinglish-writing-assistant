"""
Unit tests for SMS and digit normalization (src.normalize).
Pure Python unit tests with no model loading.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root directory to sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.normalize import (
    SMS_SPELLINGS,
    normalize_sms,
    devanagari_to_ascii_digits,
)


class TestNormalizeSMS(unittest.TestCase):
    """Unit tests for normalize_sms()."""

    def test_nhi_pta(self):
        """'nhi pta' should normalize to 'nahi pata'."""
        self.assertEqual(normalize_sms("nhi pta"), "nahi pata")
        self.assertEqual(normalize_sms("mujhe nhi pta"), "mujhe nahi pata")

    def test_mai_thik_hu(self):
        """'mai thik hu' should normalize to 'main theek hoon'."""
        self.assertEqual(normalize_sms("mai thik hu"), "main theek hoon")

    def test_names_unchanged(self):
        """Names and capitalized words should remain untouched."""
        self.assertEqual(
            normalize_sms("Rahul Mysuru se aa raha hai"),
            "Rahul Mysuru se aa raha hai"
        )
        self.assertEqual(
            normalize_sms("Priya ne Bangalore mein job li hai"),
            "Priya ne Bangalore mein job li hai"
        )
        self.assertEqual(
            normalize_sms("Amit ki shaadi Delhi mein hai"),
            "Amit ki shaadi Delhi mein hai"
        )
        self.assertEqual(
            normalize_sms("Sneha aur Karthik kal Chennai ja rahe hain"),
            "Sneha aur Karthik kal Chennai ja rahe hain"
        )
        self.assertEqual(
            normalize_sms("Dr Sharma ka lecture kal Mysore University mein hai"),
            "Dr Sharma ka lecture kal Mysore University mein hai"
        )

    def test_plain_text_unchanged(self):
        """Standard plain text without informal SMS abbreviations should remain unchanged."""
        plain_cases = [
            "main ghar ja raha hoon",
            "aap kaise ho",
            "kal milte hain",
            "mujhe bhookh lagi hai",
            "yeh kitne ka hai",
            "mujhe neend aa rahi hai",
            "mera laptop kharab ho gaya hai",
            "bus stand pe milte hain",
        ]
        for text in plain_cases:
            with self.subTest(text=text):
                self.assertEqual(normalize_sms(text), text)

    def test_mai_standalone_only(self):
        """'mai' should only be replaced when it is a standalone word, not a substring."""
        # Standalone 'mai'
        self.assertEqual(normalize_sms("mai"), "main")
        self.assertEqual(normalize_sms("mai theek hoon"), "main theek hoon")
        # Substrings containing 'mai' must NOT be modified
        self.assertEqual(
            normalize_sms("please mujhe project ki file email kar do"),
            "please mujhe project ki file email kar do"
        )
        self.assertEqual(normalize_sms("remain"), "remain")
        self.assertEqual(normalize_sms("climate"), "climate")

    def test_all_sms_spellings_entries(self):
        """Verify each dictionary entry maps correctly as a standalone word."""
        expected_mappings = {
            "nhi": "nahi",
            "nahin": "nahi",
            "pta": "pata",
            "hu": "hoon",
            "hun": "hoon",
            "mai": "main",
            "thik": "theek",
            "kyaa": "kya",
            "mujhey": "mujhe",
            "muje": "mujhe",
            "h": "hai",
        }
        for informal, standard in expected_mappings.items():
            with self.subTest(informal=informal):
                self.assertEqual(normalize_sms(informal), standard)
                self.assertEqual(SMS_SPELLINGS[informal], standard)

    def test_punctuation_and_whitespace_preservation(self):
        """Punctuation, commas, quotes, and whitespace should be preserved."""
        self.assertEqual(normalize_sms("nhi, pta!"), "nahi, pata!")
        self.assertEqual(normalize_sms('"mai thik hu"'), '"main theek hoon"')
        self.assertEqual(normalize_sms("kyaa?"), "kya?")
        self.assertEqual(normalize_sms("   "), "   ")
        self.assertEqual(normalize_sms(""), "")


class TestDevanagariToAsciiDigits(unittest.TestCase):
    """Unit tests for devanagari_to_ascii_digits()."""

    def test_500(self):
        """'५००' should convert to '500'."""
        self.assertEqual(devanagari_to_ascii_digits("५००"), "500")

    def test_1250(self):
        """'१२५०' should convert to '1250'."""
        self.assertEqual(devanagari_to_ascii_digits("१२५०"), "1250")

    def test_all_digits(self):
        """All Devanagari digits ०-९ should convert to 0-9."""
        self.assertEqual(devanagari_to_ascii_digits("०१२३४५६७८९"), "0123456789")

    def test_embedded_in_hindi_text(self):
        """Digits embedded in Hindi sentences should convert while preserving Hindi text."""
        self.assertEqual(
            devanagari_to_ascii_digits("मुझे ५०० रुपये चाहिए"),
            "मुझे 500 रुपये चाहिए"
        )
        self.assertEqual(
            devanagari_to_ascii_digits("बिल १२५० रुपीस का आया है"),
            "बिल 1250 रुपीस का आया है"
        )
        self.assertEqual(
            devanagari_to_ascii_digits("क्लास १० बजे शुरू होगी"),
            "क्लास 10 बजे शुरू होगी"
        )
        self.assertEqual(
            devanagari_to_ascii_digits("बस २ मिनट"),
            "बस 2 मिनट"
        )

    def test_ascii_and_plain_text_unchanged(self):
        """ASCII digits and text without Devanagari numerals should remain unchanged."""
        self.assertEqual(devanagari_to_ascii_digits("500"), "500")
        self.assertEqual(devanagari_to_ascii_digits("1250"), "1250")
        self.assertEqual(devanagari_to_ascii_digits("मुझे 500 रुपये चाहिए"), "मुझे 500 रुपये चाहिए")
        self.assertEqual(devanagari_to_ascii_digits("कल मिलते हैं"), "कल मिलते हैं")
        self.assertEqual(devanagari_to_ascii_digits(""), "")


class TestPipelineNormalizationFlag(unittest.TestCase):
    """Unit tests for USE_NORMALIZATION flag and HINGLISH_NORMALIZE env var (no model loading)."""

    def setUp(self):
        self.orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_flag_default(self):
        """Default should have normalization enabled."""
        import src.pipeline as pipeline
        self.assertTrue(pipeline._is_normalization_enabled())

    def test_flag_disabled_via_env(self):
        """Setting HINGLISH_NORMALIZE='0' should disable normalization."""
        import src.pipeline as pipeline
        os.environ["HINGLISH_NORMALIZE"] = "0"
        self.assertFalse(pipeline._is_normalization_enabled())

    def test_flag_enabled_via_env(self):
        """Setting HINGLISH_NORMALIZE='1' should enable normalization."""
        import src.pipeline as pipeline
        os.environ["HINGLISH_NORMALIZE"] = "1"
        self.assertTrue(pipeline._is_normalization_enabled())

    def test_flag_module_variable(self):
        """Toggling USE_NORMALIZATION directly should be respected."""
        import src.pipeline as pipeline
        if "HINGLISH_NORMALIZE" in os.environ:
            del os.environ["HINGLISH_NORMALIZE"]
        orig_val = pipeline.USE_NORMALIZATION
        try:
            pipeline.USE_NORMALIZATION = False
            self.assertFalse(pipeline._is_normalization_enabled())
            pipeline.USE_NORMALIZATION = True
            self.assertTrue(pipeline._is_normalization_enabled())
        finally:
            pipeline.USE_NORMALIZATION = orig_val


if __name__ == "__main__":
    unittest.main()
