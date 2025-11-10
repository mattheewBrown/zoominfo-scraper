from __future__ import annotations

import csv
import json
import os
from typing import List, Dict, Any

def ensure_folder(folder: str) -> None:
    os.makedirs(folder, exist_ok=True)

def export_json(records: List[Dict[str, Any]], folder: str, basename: str) -> str:
    ensure_folder(folder)
    path = os.path.join(folder, f"{basename}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return path

def export_csv(records: List[Dict[str, Any]], folder: str, basename: str) -> str:
    ensure_folder(folder)
    path = os.path.join(folder, f"{basename}.csv")
    if not records:
        # create empty file with header note
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["note"])
            writer.writerow(["No records"])
        return path

    # Flatten nested keys (address.*, fundings length, etc.)
    def flatten(obj: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    out[f"{k}.{sk}"] = sv
            elif isinstance(v, list):
                # For CSV, we serialize lists as JSON
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
        return out

    flat = [flatten(r) for r in records]
    headers = sorted({h for row in flat for h in row.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in flat:
            writer.writerow(row)
    return path