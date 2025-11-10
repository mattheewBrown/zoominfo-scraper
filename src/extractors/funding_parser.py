from __future__ import annotations

import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

def _hash_to_float(seed: str, scale: float = 100_000_000.0) -> float:
    hv = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10], 16)