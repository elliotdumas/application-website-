#!/usr/bin/env python3
"""Assemble la page publiée : web/radar.html + data/jobs.json -> dist/radar.html"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data/jobs.json").read_text())
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = (ROOT / "web/radar.html").read_text().replace("__DATA__", payload, 1)
(ROOT / "dist").mkdir(exist_ok=True)
(ROOT / "dist/radar.html").write_text(page)
print(f"dist/radar.html : {len(page)//1024} Ko, {len(data['offres'])} offres")
