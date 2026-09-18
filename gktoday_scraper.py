#!/usr/bin/env python3
"""
GKToday Scraper - Primary Entrypoint
Aliases to gktoday_scraper_v10.py
"""
import sys
from gktoday_scraper_v10 import build_cli, Pipeline

if __name__ == "__main__":
    parser = build_cli()
    args = parser.parse_args()
    pipeline = Pipeline(args)
    pipeline.run()
