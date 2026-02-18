import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.scraper import (
    MIN_DATE,
    collect_all_sources,
    dedupe_items,
    filter_recent_items,
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
        hackerone_html = '<html><body><a href="/reports/1234">Report</a></body></html>'

        with patch(
            "app.scraper._get",
            side_effect=[portswigger_xml, RuntimeError("429 Too Many Requests"), hackerone_html],
        ):
            items = collect_all_sources()

        sources = {item["source"] for item in items}
        self.assertIn("portswigger", sources)
        self.assertIn("hackerone", sources)


if __name__ == "__main__":
    unittest.main()
