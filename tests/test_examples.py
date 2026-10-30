"""The app must load a matched upstream pair or an explicit offline pair."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from utils.data_loader import download_sample_data


class ExampleDownloadTests(unittest.TestCase):
    def test_same_revision_and_content_addressed_cache(self):
        root = Path(__file__).resolve().parents[1]
        responses = [json.dumps({'sha': 'abc123'}).encode(),
                     (root / 'data/data_provider_example_360.xlsx').read_bytes(),
                     (root / 'data/example_portfolio_360.csv').read_bytes()]
        calls = []

        def fetch(request, **kwargs):
            calls.append(request if isinstance(request, str) else request.full_url)
            return io.BytesIO(responses[len(calls) - 1])

        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen', side_effect=fetch):
            provider, portfolio = download_sample_data.__wrapped__(directory)
            self.assertEqual(Path(provider).parent, Path(portfolio).parent)
            self.assertEqual(Path(provider).read_bytes(), responses[1])
            self.assertEqual(Path(portfolio).read_bytes(), responses[2])
        self.assertTrue(all('/abc123/examples/data/' in url for url in calls[1:]))

    def test_network_failure_uses_complete_bundled_pair(self):
        with patch('urllib.request.urlopen', side_effect=OSError('offline')), patch('utils.data_loader.st.warning') as warning:
            paths = download_sample_data.__wrapped__()
            self.assertTrue(all(Path(path).is_file() for path in paths))
            warning.assert_called_once()

    def test_mismatched_pair_is_rejected(self):
        root = Path(__file__).resolve().parents[1]
        responses = [json.dumps({'sha': 'abc123'}).encode(),
                     (root / 'data/data_provider_example_360.xlsx').read_bytes(),
                     b'company_id,company_name,investment_value\nunknown,Wrong,100\n']
        with tempfile.TemporaryDirectory() as directory, patch('urllib.request.urlopen', side_effect=[io.BytesIO(x) for x in responses]), patch('utils.data_loader.st.warning') as warning:
            paths = download_sample_data.__wrapped__(directory)
            self.assertTrue(all(Path(path).parent == root / 'data' for path in paths))
            self.assertFalse(list(Path(directory).rglob('*.xlsx')))
            warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()
