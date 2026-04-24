import asyncio
import threading
import os
import shutil
from playwright.async_api import async_playwright
import re


class JarvisWeb:







    def __init__(self):
        self.loop = None
        self.browser_thread = None
        self.ready = threading.Event()
        self.ctx = None
        self.page = None
        self.pw = None
        self.browser = None







    def start_system(self):
        if self.browser_thread and self.browser_thread.is_alive():
            return
        self.browser_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.browser_thread.start()
        self.ready.wait(timeout=15)







    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._boot_sequence())
            self.ready.set()
            self.loop.run_forever()
        except Exception as e:
            print(f"[BROWSER] erro loop: {e}")
            self.ready.set()







    def run(self, coro):
        self.start_system()
        if not self.loop or not self.loop.is_running():
            return "Erro: navegador nao inicializado."
        try:
            return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=30)
        except Exception as e:
            return f"Erro execucao: {e}"







    async def _boot_sequence(self):
        if not self.pw:
            self.pw = await async_playwright().start()

        chrome_path = (
            shutil.which("chrome")
            or shutil.which("google-chrome")
            or shutil.which("msedge")
        )

        try:
            self.browser = await self.pw.chromium.launch(
                headless=False,
                executable_path=chrome_path,
            )

            self.ctx = await self.browser.new_context(viewport=None)

            self.page = await self.ctx.new_page()

        except Exception as e:
            print(f"[BROWSER] falha boot: {e}")
            if self.pw:
                await self.pw.stop()
                self.pw = None







    async def _ensure_alive(self):
        try:
            if not self.browser or not self.browser.is_connected():
                await self._boot_sequence()
                return

            if not self.ctx or self.ctx.pages is None:
                self.ctx = await self.browser.new_context(viewport=None)

            if not self.page or self.page.is_closed():
                self.page = await self.ctx.new_page()

        except Exception:
            await self._boot_sequence()







    async def smart_search(self, termo, private=False):
        await self._ensure_alive()

        if private:
            ctx = await self.browser.new_context()
        else:
            ctx = self.ctx

        page = await ctx.new_page()

        try:
            await page.goto("https://www.google.com", timeout=15000)
            search = page.get_by_role("combobox").or_(page.get_by_role("searchbox"))
            await search.fill(termo)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded")
            return await self._extract_google_result(page)

        except Exception as e:
            return f"Erro busca: {e}"

        finally:
            await page.close()







    async def _extract_google_result(self, page):
        try:
            rhs = page.locator("#rhs")
            if await rhs.count() > 0:
                return (await rhs.inner_text())[:400]
            return (await page.inner_text("body"))[:500]
        except Exception:
            return "Sem resultado"







    async def tocar_youtube(self, termo):
        await self._ensure_alive()

        try:
            await self.page.goto(
                f"https://www.youtube.com/results?search_query={termo}",
                timeout=15000,
            )

            video = self.page.locator("a#video-title").first
            await video.click()

            return f"Tocando: {termo}"

        except Exception as e:
            return f"Erro YouTube: {e}"







    async def fechar_aba(self):
        if self.page and not self.page.is_closed():
            await self.page.close()
            return "Aba fechada"
        return "Nenhuma aba ativa"


jarvis_web = JarvisWeb()







async def web_controller(command: str):
    cmd = command.lower().strip()

    if cmd.startswith("jarvis"):
        cmd = cmd.replace("jarvis", "", 1).strip()

    if cmd.startswith(("pesquisa", "busca")):
        termo = re.sub(r"^(pesquisa|busca)\s*(no\s*)?(google|youtube)?", "", cmd).strip()
        if termo:
            return jarvis_web.run(jarvis_web.smart_search(termo))

    if "youtube" in cmd:
        termo = re.sub(r"^(pesquisar|pesquisa|buscar|busca)?\s*(no\s*)?youtube\s*", "", cmd).strip()
        termo = re.sub(r"^(tocar)\s*", "", termo).strip()
        if termo:
            return jarvis_web.run(jarvis_web.tocar_youtube(termo))

    return False