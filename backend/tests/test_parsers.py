import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.scraper import (
    MIN_DATE,
    collect_all_sources,
    dedupe_items,
    filter_recent_items,
    parse_hackerone_hacktivity_api,
    parse_hackerone_overview_html,
    parse_rss_items,
)


class ParserTests(unittest.TestCase):
    def test_parse_rss_items_extracts_entries(self):
        xml = """
        <rss><channel>
          <item>
            <title>Test Writeup</title>
            <link>https://example.com/w1</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
            <description>Hello</description>
          </item>
        </channel></rss>
        """

        items = parse_rss_items(xml, source="medium")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "medium")
        self.assertEqual(items[0]["url"], "https://example.com/w1")
        self.assertEqual(items[0]["title"], "Test Writeup")

    def test_parse_rss_items_extracts_dc_creator_author(self):
        xml = """
        <rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
          <item>
            <title>Namespaced Author</title>
            <link>https://example.com/w2</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
            <dc:creator>Mayra</dc:creator>
          </item>
        </channel></rss>
        """

        items = parse_rss_items(xml, source="medium")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["author"], "Mayra")

    def test_parse_hackerone_overview_html_extracts_report_links(self):
        html = """
        <html><body>
          <a href="/reports/1234">Great bug chain</a>
          <a href="/reports/8888">Another report</a>
        </body></html>
        """

        items = parse_hackerone_overview_html(html)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source"], "hackerone")
        self.assertEqual(items[0]["url"], "https://hackerone.com/reports/1234")

    def test_parse_hackerone_overview_html_extracts_report_links_from_json_blob(self):
        html = """
        <html><body>
          <script>
            window.__DATA__={"items":[
              {"url":"https:\\/\\/hackerone.com\\/reports\\/4321"},
              {"url":"https:\\u002F\\u002Fhackerone.com\\u002Freports\\u002F8765"}
            ]};
          </script>
        </body></html>
        """

        items = parse_hackerone_overview_html(html)
        urls = {item["url"] for item in items}

        self.assertIn("https://hackerone.com/reports/4321", urls)
        self.assertIn("https://hackerone.com/reports/8765", urls)

    def test_parse_hackerone_hacktivity_api_extracts_reports_from_included_data(self):
        payload = {
            "data": [
                {
                    "type": "hacktivity-item",
                    "relationships": {"report": {"data": {"type": "report", "id": "4321"}}},
                }
            ],
            "included": [
                {
                    "type": "report",
                    "id": "4321",
                    "attributes": {
                        "title": "API report title",
                        "url": "https://hackerone.com/reports/4321",
                        "disclosed_at": "2026-02-18T11:00:00Z",
                    },
                }
            ],
        }

        items = parse_hackerone_hacktivity_api(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "hackerone")
        self.assertEqual(items[0]["url"], "https://hackerone.com/reports/4321")
        self.assertEqual(items[0]["title"], "API report title")

    def test_filter_recent_items_uses_min_2025_date(self):
        items = [
            {
                "source": "portswigger",
                "title": "old",
                "url": "https://example.com/old",
                "published_at": datetime(2024, 12, 31, tzinfo=timezone.utc),
            },
            {
                "source": "portswigger",
                "title": "new",
                "url": "https://example.com/new",
                "published_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            },
        ]

        filtered = filter_recent_items(items)

        self.assertEqual(MIN_DATE.isoformat(), "2025-01-01T00:00:00+00:00")
        self.assertEqual([x["url"] for x in filtered], ["https://example.com/new"])

    def test_dedupe_items_keeps_first_url_only(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        items = [
            {"url": "https://example.com/a", "published_at": now, "title": "a", "source": "medium"},
            {"url": "https://example.com/a", "published_at": now, "title": "a2", "source": "medium"},
            {"url": "https://example.com/b", "published_at": now, "title": "b", "source": "medium"},
        ]

        deduped = dedupe_items(items)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]["url"], "https://example.com/a")
        self.assertEqual(deduped[1]["url"], "https://example.com/b")

    def test_collect_all_sources_continues_when_one_source_fails(self):
        portswigger_xml = """
        <rss><channel>
          <item>
            <title>PortSwigger</title>
            <link>https://example.com/p1</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """

        with patch(
            "app.scraper._get",
            side_effect=[portswigger_xml, RuntimeError("429 Too Many Requests")],
        ):
            items = collect_all_sources()

        sources = {item["source"] for item in items}
        self.assertIn("portswigger", sources)
        self.assertNotIn("hackerone", sources)

    def test_collect_all_sources_uses_hackerone_api_when_credentials_present(self):
        portswigger_xml = """
        <rss><channel>
          <item>
            <title>PortSwigger</title>
            <link>https://example.com/p1</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
        medium_xml = """
        <rss><channel>
          <item>
            <title>Medium</title>
            <link>https://example.com/m1</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
        h1_items = [
            {
                "source": "hackerone",
                "title": "API report",
                "url": "https://hackerone.com/reports/9999",
                "published_at": datetime(2026, 2, 18, tzinfo=timezone.utc).isoformat(),
            }
        ]

        with (
            patch("app.scraper._get", side_effect=[portswigger_xml, medium_xml]) as get_mock,
            patch("app.scraper.fetch_hackerone_hacktivity_api", return_value=h1_items) as h1_api_mock,
        ):
            items = collect_all_sources(hackerone_username="user", hackerone_api_token="token")

        sources = {item["source"] for item in items}
        self.assertIn("portswigger", sources)
        self.assertIn("medium", sources)
        self.assertIn("hackerone", sources)
        h1_api_mock.assert_called_once_with("user", "token")
        self.assertEqual(get_mock.call_count, 2)

    def test_collect_all_sources_falls_back_to_hackerone_overview_when_api_returns_empty(self):
        portswigger_xml = """
        <rss><channel>
          <item>
            <title>PortSwigger</title>
            <link>https://example.com/p1</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
        medium_xml = """
        <rss><channel>
          <item>
            <title>Medium</title>
            <link>https://example.com/m1</link>
            <pubDate>Mon, 15 Jan 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
        h1_overview_html = """
        <html><body>
          <a href="/reports/1234">Overview disclosed report</a>
        </body></html>
        """

        with (
            patch(
                "app.scraper._get",
                side_effect=[portswigger_xml, medium_xml, h1_overview_html, "<html></html>"],
            ) as get_mock,
            patch("app.scraper.fetch_hackerone_hacktivity_api", return_value=[]) as h1_api_mock,
        ):
            items = collect_all_sources(hackerone_username="user", hackerone_api_token="token")

        urls = {item["url"] for item in items}
        self.assertIn("https://hackerone.com/reports/1234", urls)
        h1_api_mock.assert_called_once_with("user", "token")
        self.assertEqual(get_mock.call_count, 4)


if __name__ == "__main__":
    unittest.main()
