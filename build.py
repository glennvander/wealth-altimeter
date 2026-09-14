#!/usr/bin/env python3
"""Assemble wealth-altimeter.html from altimeter.template.html + model.json (run model.py first)."""
import json, pathlib
here = pathlib.Path(__file__).parent
d = json.load(open(here/"model.json"))
def r(o):
    if isinstance(o, float): return round(o, 2)
    if isinstance(o, list): return [r(x) for x in o]
    if isinstance(o, dict): return {k: r(v) for k, v in o.items()}
    return o
page = (here/"altimeter.template.html").read_text().replace("/*__DATA__*/", json.dumps(r(d), separators=(",", ":")))
(here/"wealth-altimeter.html").write_text(page)
head = "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>"
(here/"preview.html").write_text(head + page + "</body></html>")
print("built", len(page), "bytes")
