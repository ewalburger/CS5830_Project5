"""Download Utah State Today stories into a local JSON file.

The RSS feed contains only the newest 50 stories.  This script instead walks
the paginated category archives, using the archive category as each story's
label.
"""

import argparse
import html
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import requests


BASE_URL = "https://www.usu.edu"
DEFAULT_OUTPUT = Path(__file__).with_name("articles.json")

# These are the category pages that correspond to the RSS labels.
SECTIONS = {
    "Arts & Humanities": "arts-humanities",
    "Athletics": "athletics",
    "Business & Society": "business-society",
    "Campus Life": "campus-life",
    "Health & Wellness": "health-wellness",
    "Land & Environment": "land-environment",
    "Science & Technology": "science-technology",
    "Teaching & Learning": "teaching-learning",
    "University Affairs": "university-affairs",
}


class StoryParser(HTMLParser):
    """Extract the title, publication date, and article body from one page."""

    def __init__(self):
        super().__init__()
        self.title_parts = []
        self.body_parts = []
        self.published = None
        self.in_title = False
        self.body_div_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property") == "article:published_time":
            self.published = attrs.get("content")
        if tag == "h1" and attrs.get("id") == "sf-story-title":
            self.in_title = True
        if tag == "div" and attrs.get("id") == "sf-story-content":
            self.body_div_depth = 1
        elif tag == "div" and self.body_div_depth:
            self.body_div_depth += 1

    def handle_endtag(self, tag):
        if tag == "h1" and self.in_title:
            self.in_title = False
        if tag == "div" and self.body_div_depth:
            self.body_div_depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.body_div_depth:
            self.body_parts.append(data)

    @staticmethod
    def clean(parts):
        return " ".join(" ".join(parts).split())

    @property
    def title(self):
        return self.clean(self.title_parts)

    @property
    def body(self):
        return self.clean(self.body_parts)


def archive_story_urls(page_html):
    """Return the unique canonical story links found on one archive page."""
    paths = re.findall(r'href=["\'](/today/story/[^"\'#?]+)', page_html)
    return {BASE_URL + html.unescape(path) for path in paths}


def load_articles(output_file):
    if not output_file.exists():
        return {}
    with output_file.open(encoding="utf-8") as file:
        articles = json.load(file)
    return {article["url"]: article for article in articles}


def save_articles(articles_by_url, output_file):
    articles = sorted(articles_by_url.values(), key=lambda article: article["url"])
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(articles, file, indent=2, ensure_ascii=False)


def scrape_story(session, url, category):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    parser = StoryParser()
    parser.feed(response.text)
    parser.close()

    if not parser.title or not parser.body:
        raise ValueError("could not find the title or story body")

    return {
        "title": parser.title,
        "category": category,
        # Keep this name so the current notebook can use the saved file directly.
        "summary": parser.body,
        "url": url,
        "published": parser.published,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pages",
        type=int,
        default=10,
        help="archive pages to visit per category (default: 10)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="JSON file to create"
    )
    parser.add_argument(
        "--delay", type=float, default=0.1, help="seconds between requests"
    )
    args = parser.parse_args()

    articles = load_articles(args.output)
    session = requests.Session()
    session.headers["User-Agent"] = "CS5830 class project scraper"

    for category, section in SECTIONS.items():
        for page in range(1, args.pages + 1):
            archive_url = f"{BASE_URL}/today/section/{section}/?page={page}"
            response = session.get(archive_url, timeout=30)
            response.raise_for_status()
            urls = archive_story_urls(response.text)
            if not urls:
                break

            added = 0
            for url in urls:
                if url in articles:
                    continue
                try:
                    articles[url] = scrape_story(session, url, category)
                    added += 1
                except (requests.RequestException, ValueError) as error:
                    print(f"Skipping {url}: {error}")
                time.sleep(args.delay)

            save_articles(articles, args.output)
            print(f"{category}, page {page}: added {added}; total {len(articles)}")
            time.sleep(args.delay)

    print(f"Saved {len(articles)} articles to {args.output}")


if __name__ == "__main__":
    main()
