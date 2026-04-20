import asyncio
import threading
import os
import shutil
from playwright.async_api import async_playwright






class JarvisWeb:
    def __init__(self):
        self.loop = None
        self.browser_thread = None
        self.ready = threading.Event()
        self.ctx = None
        self.page = None
        self.pw = None






    def start_system(self):
        if self.browser_thread and self.browser_thread.is_alive():
            return

        self.browser_thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )

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
            print(f"Erro Loop: {e}")
            self.ready.set()






    def run(self, coro):
        self.start_system()

        try:
            return asyncio.run_coroutine_threadsafe(
                coro, self.loop
            ).result(timeout=60)

        except Exception as e:
            return f"Erro execução: {e}"






    async def _boot_sequence(self):
        if not self.pw:
            self.pw = await async_playwright().start()

        profile = os.path.join(os.getcwd(), "logs", "jarvis_profile")

        chrome_path = (
            shutil.which("chrome")
            or shutil.which("google-chrome")
            or shutil.which("msedge")
        )

        try:
            self.ctx = await self.pw.chromium.launch_persistent_context(
                profile,
                executable_path=chrome_path,
                headless=False,
                no_viewport=True,
                args=[
                    "--start-maximized"
                ],
            )

            self.page = (
                self.ctx.pages[0]
                if self.ctx.pages
                else await self.ctx.new_page()
            )

        except Exception:
            if self.pw:
                await self.pw.stop()
                self.pw = None






    async def _ensure_page_alive(self):
        if not self.ctx:
            await self._boot_sequence()
            return

        try:
            if not self.page or self.page.is_closed():
                self.page = (
                    self.ctx.pages[-1]
                    if self.ctx.pages
                    else await self.ctx.new_page()
                )

            await self.page.bring_to_front()

        except Exception:
            await self._boot_sequence()






    async def smart_search(self, termo, private=False):
        await self._ensure_page_alive()

        context = (
            await self.ctx.browser.new_context()
            if private and self.ctx and self.ctx.browser
            else self.ctx
        )

        page = await context.new_page()

        try:
            await page.goto("https://www.google.com", timeout=15000)

            search = page.get_by_role("combobox").or_(
                page.get_by_role("searchbox")
            )

            await search.fill(termo)
            await page.keyboard.press("Enter")

            await page.wait_for_load_state("domcontentloaded")

            return await self._extract_google_result(page)

        except Exception as e:
            return f"Erro rede: {e}"






    async def _extract_google_result(self, page):
        try:
            rhs = page.locator("#rhs")

            if await rhs.count() > 0:
                return (await rhs.inner_text())[:400]

            return (await page.inner_text("body"))[:500]

        except Exception:
            return "Sem resultado"






    async def tocar_youtube(self, termo):
        await self._ensure_page_alive()

        try:
            await self.page.goto(
                f"https://www.youtube.com/results?search_query={termo}",
                timeout=15000
            )

            video = self.page.locator(
                "a#video-title, ytd-video-renderer a#thumbnail"
            ).first

            await video.click()

            return f"Tocando: {termo}"

        except Exception as e:
            return f"Erro YouTube: {e}"






    async def fechar_aba(self):
        if self.page and not self.page.is_closed():
            await self.page.close()

            if self.ctx.pages:
                self.page = self.ctx.pages[-1]
                return "Aba fechada"

        return "Nenhuma aba ativa"






_jarvis_web = JarvisWeb()






async def web_controller(command: str):
    cmd = command.lower().strip()

    if cmd.startswith("jarvis"):
        cmd = cmd.replace("jarvis", "", 1).strip()

    if cmd.startswith("pesquisa") or cmd.startswith("busca"):
        termo = cmd.replace("pesquisa", "", 1).replace("busca", "", 1).strip()

        if termo:
            return _jarvis_web.run(_jarvis_web.smart_search(termo))

    if "youtube" in cmd:
        termo = cmd.replace("youtube", "").replace("tocar", "").strip()

        if termo:
            return _jarvis_web.run(_jarvis_web.tocar_youtube(termo))

    return False