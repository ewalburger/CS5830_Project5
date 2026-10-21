# CS5830_Project5

Dataset: We will be scraping data from the Utah State Today xml page https://www.usu.edu/today/rss/UtahStateToday.xml

We will be determining the category of article based on it's description using the Naiive Bayes algorithm.

## Collecting a local dataset

The RSS feed is limited to its newest 50 articles. Run the scraper to collect
older articles from the category archives and save them in `articles.json`:

```bash
python scrape.py --pages 10
```

It is safe to run again: stories already in `articles.json` are skipped. Raise
`--pages` to collect a longer history.
