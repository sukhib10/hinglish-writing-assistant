"""
Unit tests for improve_phrasing in src.pipeline.
Tests backend options and mocked Gemini REST API calls without making real network requests.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root directory to sys.path so 'src' is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import improve_phrasing


class TestImprovePhrasing(unittest.TestCase):

    def setUp(self):
        # Preserve original environment state
        self.orig_env = os.environ.copy()

    def tearDown(self):
        # Restore environment state
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_empty_input(self):
        """Empty or whitespace input should be returned as-is."""
        self.assertEqual(improve_phrasing(""), "")
        self.assertEqual(improve_phrasing("   "), "   ")

    def test_backend_none(self):
        """PHRASING_BACKEND='none' should return input text unchanged."""
        os.environ["PHRASING_BACKEND"] = "none"
        text = "राहुल कल 2 बजे ऑफिस आएगा"
        self.assertEqual(improve_phrasing(text), text)

    def test_missing_api_key(self):
        """Missing GEMINI_API_KEY should return input text unchanged and warn."""
        os.environ["PHRASING_BACKEND"] = "gemini"
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        text = "राहुल कल 2 बजे ऑफिस आएगा"
        self.assertEqual(improve_phrasing(text), text)

    @patch("src.pipeline.requests.post")
    def test_mocked_failed_request_http_error(self, mock_post):
        """HTTP error response from Gemini API should fallback to input text unchanged."""
        os.environ["PHRASING_BACKEND"] = "gemini"
        os.environ["GEMINI_API_KEY"] = "dummy-test-key"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        text = "राहुल कल 2 बजे ऑफिस आएगा"
        result = improve_phrasing(text)
        self.assertEqual(result, text)
        mock_post.assert_called_once()

    @patch("src.pipeline.requests.post")
    def test_mocked_failed_request_timeout(self, mock_post):
        """Timeout exception during request should fallback to input text unchanged."""
        import requests
        os.environ["PHRASING_BACKEND"] = "gemini"
        os.environ["GEMINI_API_KEY"] = "dummy-test-key"

        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        text = "राहुल कल 2 बजे ऑफिस आएगा"
        result = improve_phrasing(text)
        self.assertEqual(result, text)
        mock_post.assert_called_once()

    @patch("src.pipeline.requests.post")
    def test_mocked_success_strips_quotes_and_whitespace(self, mock_post):
        """Successful Gemini response should have surrounding whitespace and quotes stripped."""
        os.environ["PHRASING_BACKEND"] = "gemini"
        os.environ["GEMINI_API_KEY"] = "dummy-test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '  "राहुल कल दोपहर 2 बजे कार्यालय आएंगे।"  \n'}
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        text = "राहुल कल 2 बजे ऑफिस आएगा"
        expected = "राहुल कल दोपहर 2 बजे कार्यालय आएंगे।"
        result = improve_phrasing(text)
        self.assertEqual(result, expected)

        # Verify key was passed in header and not in URL
        called_args, called_kwargs = mock_post.call_args
        self.assertNotIn("dummy-test-key", called_args[0])
        self.assertEqual(called_kwargs["headers"]["x-goog-api-key"], "dummy-test-key")
        self.assertEqual(called_kwargs["timeout"], 10)


if __name__ == "__main__":
    unittest.main()
