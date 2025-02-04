#!/usr/bin/env bash

# python
export PYTHONPATH=.
uv run python3 src/downloader.py
uv run python3 src/converter.py
uv run python3 src/summarizer.py

# git
git add data/json data/markdown data/summary
git commit -a -m "auto-push"
git push

date
