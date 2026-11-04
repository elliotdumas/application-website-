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
# version GitHub Pages : page complète avec son propre squelette HTML
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/index.html").write_text('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<meta name="robots" content="noindex, nofollow">\n<style>[hidden]{display:none!important}body{margin:0}img{max-width:100%}</style>\n' + page.replace("<style>", "</head>\n<body>\n<style>", 1) + "\n</body>\n</html>\n")
(ROOT / "docs/.nojekyll").write_text("")
print(f"dist/radar.html : {len(page)//1024} Ko, {len(data['offres'])} offres")
