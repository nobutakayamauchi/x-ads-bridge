from __future__ import annotations

import unittest

from creative_reference import (
    CreativeReferenceError,
    normalize_bundle_command,
    normalize_tweet_references,
    tweet_id_from_url,
)


class CreativeReferenceTests(unittest.TestCase):
    def test_extracts_x_status_id(self):
        self.assertEqual(
            tweet_id_from_url("https://x.com/ultimate28/status/2092414512934908309?s=20"),
            "2092414512934908309",
        )

    def test_accepts_twitter_status_url(self):
        self.assertEqual(
            tweet_id_from_url("https://twitter.com/ultimate28/status/1234567890"),
            "1234567890",
        )

    def test_rejects_non_x_host(self):
        with self.assertRaises(CreativeReferenceError):
            tweet_id_from_url("https://example.com/ultimate28/status/1234567890")

    def test_normalizes_single_url_to_signed_tweet_ids(self):
        proposed = {
            "action": "create_website_traffic_bundle_paused",
            "tweet_url": "https://x.com/ultimate28/status/2092414512934908309",
        }
        normalized = normalize_tweet_references(proposed)
        self.assertEqual(normalized["tweet_ids"], ["2092414512934908309"])
        self.assertNotIn("tweet_url", normalized)

    def test_merges_and_deduplicates_ids_and_urls(self):
        proposed = {
            "tweet_ids": ["111"],
            "tweet_urls": [
                "https://x.com/a/status/222",
                "https://x.com/a/status/111",
            ],
        }
        normalized = normalize_tweet_references(proposed)
        self.assertEqual(normalized["tweet_ids"], ["111", "222"])
        self.assertNotIn("tweet_urls", normalized)

    def test_bundle_command_canonicalizes_before_protocol(self):
        command = {
            "action": "prepare_bundle_proposal",
            "proposed_command": {
                "action": "create_website_traffic_bundle_paused",
                "tweet_url": "https://x.com/a/status/333",
            },
        }
        normalized = normalize_bundle_command(command)
        self.assertEqual(normalized["proposed_command"]["tweet_ids"], ["333"])
        self.assertNotIn("tweet_url", normalized["proposed_command"])


if __name__ == "__main__":
    unittest.main()
