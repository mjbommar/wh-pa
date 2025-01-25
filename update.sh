#!/usr/bin/env bash

export PYTHONPATH=.
uv run python3 src/downloader.py
uv run python3 src/converter.py
uv run python3 src/summarizer.py
date
