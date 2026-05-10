from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.parse
from typing import Optional

import requests

log = logging.getLogger("jarvis.smart_search")

TIMEOUT     = 8
CACHE_TTL   = 120.0
cache: dict[str, tuple[str, float]] = {}

DDG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

def cache_get(chave: str) -> Optional[str]:
    entry = cache.get(chave)
    if entry and (time.time() - entry[1]) < CACHE_TTL:
        return entry[0]
    return None

def cache_set(chave: str, valor: str) -> None:
    cache[chave] = (valor, time.time())

def limpar_html(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()

def buscar_ddg_api(termo: str) -> str:
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": termo, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers=DDG_HEADERS,
            timeout=TIMEOUT,
        )
        data = r.json()
        texto = (data.get("AbstractText") or data.get("Answer") or "").strip()
        if texto:
            return texto[:600]
        topicos = data.get("RelatedTopics", [])
        snippets = [t["Text"][:200] for t in topicos[:3] if isinstance(t, dict) and t.get("Text")]
        return "\n".join(snippets)[:500] if snippets else ""
    except Exception as exc:
        log.debug("DDG API: %s", exc)
        return ""

def buscar_wikipedia(termo: str) -> str:
    try:
        r = requests.get(
            "https://pt.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(termo),
            headers=DDG_HEADERS,
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            extrato = data.get("extract", "").strip()
            return extrato[:600] if extrato else ""
    except Exception as exc:
        log.debug("Wikipedia: %s", exc)
        return ""

def buscar_ddg_html(termo: str) -> str:
    try:
        from html.parser import HTMLParser

        class ExtratorHTML(HTMLParser):

            def __init__(self):
                super().__init__()
                self.snippets: list[str] = []
                self.cap = False
                self.buf: list[str] = []

            def handle_starttag(self, tag, attrs):
                cls = dict(attrs).get("class", "")
                if "result__snippet" in cls or "result__body" in cls:
                    self.cap = True
                    self.buf = []

            def handle_endtag(self, tag):
                if self.cap and tag in ("span", "div", "a"):
                    t = "".join(self.buf).strip()
                    if len(t) > 20:
                        self.snippets.append(t)
                    self.cap = False

            def handle_data(self, data):
                if self.cap:
                    self.buf.append(data)

        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(termo)}"
        r = requests.get(url, headers=DDG_HEADERS, timeout=TIMEOUT)
        p = ExtratorHTML()
        p.feed(r.text)
        return "\n".join(p.snippets[:3])[:500] if p.snippets else ""
    except Exception as exc:
        log.debug("DDG HTML: %s", exc)
        return ""

def buscar_ddg_lite(termo: str) -> str:
    try:
        from html.parser import HTMLParser

        class ExtratorLite(HTMLParser):

            def __init__(self):
                super().__init__()
                self.snippets: list[str] = []
                self.cap = False
                self.buf: list[str] = []

            def handle_starttag(self, tag, attrs):
                cls = dict(attrs).get("class", "")
                if "result-snippet" in cls or tag == "td":
                    self.cap = True
                    self.buf = []

            def handle_endtag(self, tag):
                if self.cap and tag in ("td", "span", "div"):
                    t = "".join(self.buf).strip()
                    if len(t) > 20:
                        self.snippets.append(t)
                    self.cap = False

            def handle_data(self, data):
                if self.cap:
                    self.buf.append(data)

        url = "https://lite.duckduckgo.com/lite/"
        r = requests.post(url, data={"q": termo}, headers=DDG_HEADERS, timeout=TIMEOUT)
        p = ExtratorLite()
        p.feed(r.text)
        return "\n".join(p.snippets[:3])[:500] if p.snippets else ""
    except Exception as exc:
        log.debug("DDG Lite: %s", exc)
        return ""

async def buscar_playwright(termo: str) -> str:
    try:
        from tasks.browser import jarvis_web
        return jarvis_web.run(jarvis_web.pesquisar_com_playwright(termo)) or ""
    except Exception as exc:
        log.debug("Playwright: %s", exc)
        return ""

def buscar_sync(termo: str) -> str:
    chave = f"search:{termo.lower()[:80]}"
    cached = cache_get(chave)
    if cached:
        return cached

    resultado = buscar_ddg_api(termo)
    if not resultado:
        resultado = buscar_wikipedia(termo)
    if not resultado:
        resultado = buscar_ddg_html(termo)
    if not resultado:
        resultado = buscar_ddg_lite(termo)

    if resultado:
        cache_set(chave, resultado)
    return resultado or f"Sem resultados para '{termo}'."

async def buscar(termo: str, usar_browser: bool = False) -> str:
    chave = f"search:{termo.lower()[:80]}"
    cached = cache_get(chave)
    if cached:
        return cached

    loop = asyncio.get_event_loop()

    resultado = await loop.run_in_executor(None, buscar_ddg_api, termo)
    if not resultado:
        resultado = await loop.run_in_executor(None, buscar_wikipedia, termo)
    if not resultado:
        resultado = await loop.run_in_executor(None, buscar_ddg_html, termo)
    if not resultado:
        resultado = await loop.run_in_executor(None, buscar_ddg_lite, termo)
    if not resultado and usar_browser:
        resultado = await buscar_playwright(termo)

    resultado = resultado or f"Sem resultados para '{termo}'."
    cache_set(chave, resultado)
    return resultado

def limpar_cache_busca() -> None:
    cache.clear()