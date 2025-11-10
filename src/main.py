from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure relative imports work when running as "python src/main.py"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from extractors.company_parser import build_company_record  # noqa: E402
from extractors.utils_proxy import build_client, fetch_text  # noqa: E402
from outputs.exporters import export_json, export_csv  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def load_settings(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_inputs(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # normalize to list
        data = [data]
    return data

async def process_one(
    client,
    item: Dict[str, Any],
    settings: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    simulate: bool = bool(settings.get("simulate", True))
    retries: int = int(settings.get("max_retries_per_url", 3))
    backoff: float = float(settings.get("retry_backoff_seconds", 1.5))

    url = item.get("company_url") or item.get("url") or ""
    name = item.get("company_name") or item.get("name") or ""

    target = url or name
    if not target:
        logging.warning("Skipping input without company_url or company_name: %s", item)
        return None

    html: Optional[str] = None
    if url and not simulate:
        try:
            html = await fetch_text(client, url, retries, backoff)
        except Exception as e:  # noqa: BLE001
            if not settings.get("ignore_url_failures", True):
                raise
            logging.error("Failed fetching %s: %s", url, e)

    record = build_company_record(target, html, simulate)
    return record

async def run_async(args: argparse.Namespace) -> int:
    # Settings resolution
    settings_path = args.settings or os.path.join(CURRENT_DIR, "config", "settings.example.json")
    settings = load_settings(settings_path)

    # Inputs
    input_path = args.input or os.path.join(os.path.dirname(CURRENT_DIR), "data", "input_samples.json")
    inputs = load_inputs(input_path)
    logging.info("Loaded %d input items", len(inputs))

    # HTTP client (may use proxy rotation via environment of utils)
    client = build_client(
        timeout_seconds=int(settings.get("timeout_seconds", 20)),
        proxies=settings.get("proxies"),
        user_agents=settings.get("user_agents"),
    )

    sem = asyncio.Semaphore(int(settings.get("concurrency", 10)))
    results: List[Dict[str, Any]] = []

    async def worker(itm: Dict[str, Any]) -> None:
        async with sem:
            rec = await process_one(client, itm, settings)
            if rec:
                results.append(rec)

    await asyncio.gather(*(worker(itm) for itm in inputs))
    await client.aclose()

    # Outputs
    out_folder = args.out or settings.get("output", {}).get("folder") or os.path.join(os.path.dirname(CURRENT_DIR), "data")
    basename = settings.get("output", {}).get("basename", "zoominfo_companies")

    json_path = export_json(results, out_folder, basename)
    csv_path = export_csv(results, out_folder, basename)

    logging.info("Wrote JSON: %s", json_path)
    logging.info("Wrote CSV : %s", csv_path)
    return 0

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ZoomInfo Company Data Scraper (simulation-capable).")
    p.add_argument("--input", help="Path to input JSON (list of {company_url|company_name})")
    p.add_argument("--settings", help="Path to settings JSON")
    p.add_argument("--out", help="Output folder path")
    return p

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        code = asyncio.run(run_async(args))
        raise SystemExit(code)
    except KeyboardInterrupt:
        logging.warning("Interrupted by user")
        raise SystemExit(130)

if __name__ == "__main__":
    main()