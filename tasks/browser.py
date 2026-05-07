from __future__ import annotations

import asyncio
import logging
import re
import threading
import urllib.parse

import requests

log = logging.getLogger("jarvis.browser")

DDG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
DDG_TIMEOUT = 10








def buscar_ddg_instantaneo(termo: str) -> str:
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": termo, "format": "json", "no_html": "1", "skip_disambig": "1"}
        r = requests.get(url, params=params, headers=DDG_HEADERS, timeout=DDG_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        abstract = (data.get("AbstractText") or "").strip()
        if abstract:
            return abstract[:500]


        answer = (data.get("Answer") or "").strip()
        if answer:
            return answer[:500]


        related = data.get("RelatedTopics", [])
        snippets = []
        for item in related[:3]:
            if isinstance(item, dict) and item.get("Text"):
                snippets.append(item["Text"][:200])


        if snippets:
            return "\n".join(snippets)


        return ""
    except Exception as e:
        log.error("[DDG] Erro: %s", e)
        return ""








def buscar_ddg_html_alternativo(termo: str) -> str:
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(termo)}"
        r = requests.get(url, headers=DDG_HEADERS, timeout=DDG_TIMEOUT)
        r.raise_for_status()
        from html.parser import HTMLParser

        class SnippetParser(HTMLParser):








            def __init__(self):
                super().__init__()
                self.snippets = []
                self.capture = False
                self.buf = []








            def handle_starttag(self, tag, attrs):
                classes = dict(attrs).get("class", "")
                if "result__snippet" in classes or "result__body" in classes:
                    self.capture = True
                    self.buf = []








            def handle_endtag(self, tag):
                if self.capture and tag in ("a", "span", "div"):
                    text = "".join(self.buf).strip()
                    if text and len(text) > 20:
                        self.snippets.append(text)


                    self.capture = False








            def handle_data(self, data):
                if self.capture:
                    self.buf.append(data)


        parser = SnippetParser()
        parser.feed(r.text)
        return "\n".join(parser.snippets[:3])[:500] if parser.snippets else ""
    except Exception as e:
        log.error("[DDG HTML] Erro: %s", e)
        return ""








def busca_web_sync(termo: str) -> str:
    resultado = buscar_ddg_instantaneo(termo)
    if not resultado:
        resultado = buscar_ddg_html_alternativo(termo)


    if not resultado:
        return f"Sem resultados encontrados para '{termo}'."


    return resultado








class JarvisWeb:








    def __init__(self):
        self.pw_lock = threading.Lock()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.browser_thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.ctx = None
        self.page = None
        self.pw = None
        self.browser = None
        self.pw_available: bool | None = None








    def verificar_playwright_disponivel(self) -> bool:
        if self.pw_available is not None:
            return self.pw_available


        try:
            import playwright
            self.pw_available = True
        except ImportError:
            self.pw_available = False


        return self.pw_available








    def start_system(self):
        if not self.verificar_playwright_disponivel():
            return


        if self.browser_thread and self.browser_thread.is_alive():
            return


        self.browser_thread = threading.Thread(target=self.rodar_loop_async, daemon=True)
        self.browser_thread.start()
        self.ready.wait(timeout=15)








    def rodar_loop_async(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.subir_playwright())
            self.loop.call_soon(self.ready.set)
            self.loop.run_forever()
        except Exception as e:
            log.error("[BROWSER] erro loop: %s", e)
            self.ready.set()








    def run(self, coro):
        if not self.verificar_playwright_disponivel():
            return "Playwright não instalado."


        self.start_system()
        if not self.loop or not self.loop.is_running():
            return "Erro: navegador não inicializado."


        try:
            return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=30)
        except Exception as e:
            return f"Erro execução: {e}"








    async def subir_playwright(self):
        from playwright.async_api import async_playwright

        if self.pw:
            try:
                await self.pw.stop()
            except Exception:
                pass


        self.pw = await async_playwright().start()
        try:
            self.browser = await self.pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            self.ctx = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            )
            self.page = await self.ctx.new_page()
        except Exception as e:
            log.error("[BROWSER] falha boot: %s", e)
            if self.pw:
                await self.pw.stop()
                self.pw = None








    async def manter_sessao(self):
        try:
            if not self.browser or not self.browser.is_connected():
                await self.subir_playwright()
                return


            if not self.ctx:
                self.ctx = await self.browser.new_context(viewport={"width": 1280, "height": 720})


            try:
                pages = self.ctx.pages
                if not self.page or self.page.is_closed() or self.page not in pages:
                    self.page = await self.ctx.new_page()
            except Exception:
                self.page = await self.ctx.new_page()


        except Exception:
            await self.subir_playwright()








    async def smart_search(self, termo: str, private: bool = False) -> str:
        resultado = await asyncio.get_event_loop().run_in_executor(None, busca_web_sync, termo)
        if resultado and not resultado.startswith("Sem resultados"):
            return resultado


        if not self.verificar_playwright_disponivel():
            return resultado


        return await self.pesquisar_com_playwright(termo)








    async def pesquisar_com_playwright(self, termo: str) -> str:
        await self.manter_sessao()
        page = await self.ctx.new_page()
        try:
            await page.goto(
                f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(termo)}",
                timeout=15000,
            )
            snippets = await page.locator(".result__snippet").all_inner_texts()
            return "\n".join(snippets[:3])[:500] if snippets else f"Sem resultados para '{termo}'."
        except Exception as e:
            return f"Erro busca: {e}"


        finally:
            await page.close()








    async def tocar_youtube(self, termo: str) -> str:
        if not self.verificar_playwright_disponivel():
            return "Playwright não instalado. Instale com: pip install playwright && playwright install chromium"


        await self.manter_sessao()
        try:
            await self.page.goto(
                f"https://www.youtube.com/results?search_query={urllib.parse.quote(termo)}",
                timeout=20000,
            )
            await asyncio.sleep(2)
            video = self.page.locator("a#video-title").first
            await video.wait_for(state="visible", timeout=10000)
            await video.click()
            return f"Tocando: {termo}"
        except Exception as e:
            return f"Erro YouTube: {e}"








    async def fechar_aba(self) -> str:
        if self.page and not self.page.is_closed():
            await self.page.close()
            return "Aba fechada."


        return "Nenhuma aba ativa."








    async def fechar_sistema(self) -> str:
        if self.browser:
            await self.browser.close()


        if self.pw:
            await self.pw.stop()


        if self.loop:
            self.loop.stop()


        return "Sistema encerrado."








    async def navigate_to_blank(self) -> str:
        await self.manter_sessao()
        try:
            await self.page.goto("about:blank")
            return "Navegando para página em branco."
        except Exception as e:
            return f"Erro ao navegar: {e}"

jarvis_web = JarvisWeb()








async def web_controller(command: str):
    cmd = command.lower().strip()
    if cmd.startswith("jarvis"):
        cmd = cmd.replace("jarvis", "", 1).strip()


    if cmd.startswith(("pesquisa", "busca")):
        termo = re.sub(r"^(pesquisa|busca)\s*(no\s*)?(google|youtube)?", "", cmd).strip()
        if termo:
            return await asyncio.get_event_loop().run_in_executor(None, busca_web_sync, termo)


    if "youtube" in cmd:
        termo = re.sub(r"^(pesquisar|pesquisa|buscar|busca)?\s*(no\s*)?youtube\s*", "", cmd).strip()
        termo = re.sub(r"^(tocar)\s*", "", termo).strip()
        if termo:
            return jarvis_web.run(jarvis_web.tocar_youtube(termo))


    if "fechar" in cmd and "aba" in cmd:
        return jarvis_web.run(jarvis_web.fechar_aba())


    if "about:blank" in cmd or "página em branco" in cmd:
        return jarvis_web.run(jarvis_web.navigate_to_blank())


    return False