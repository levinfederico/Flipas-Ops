name: Flipas Scraper

on:
  schedule:
    - cron: "0 12,14,16,18,20,22,0,2 * * 1-6"
    - cron: "0 14,18,22 * * 0"
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
      - run: pip install -r requirements.txt
      - name: Run scraper
        env:
          SMTP_PASSWORD:      ${{ secrets.SMTP_PASSWORD }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID:   ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python scraper.py
      - name: Commit data
        run: |
          git config user.name  "flipas-bot"
          git config user.email "flipasre@gmail.com"
          git add data.json seen_ids.json
          git diff --staged --quiet || git commit -m "🏠 $(date -u '+%Y-%m-%d %H:%M UTC')"
          git push
