import asyncio
import threading
import os
import shutil
from playwright.async_api import async_playwright
import re
import random


try:
       from playwright_stealth import stealth as stealth_func
except ImportError:
       stealth_func = None







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
              except Exception:
                     print(f"[BROWSER] erro loop:")
                     self.ready.set()







       def run(self, coro):
              self.start_system()
              if not self.loop or not self.loop.is_running():
                     return "Erro: navegador nao inicializado."
              try:
                     return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=30)
              except Exception:
                     return f"Erro execucao:"







       async def _boot_sequence(self):
              if self.pw:
                     try:
                            await self.pw.stop()
                     except:
                            pass
              
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
                            args=[
                                   "--disable-blink-features=AutomationControlled",
                                   "--no-sandbox",
                                   "--disable-infobars"
                            ]
                     )

                     self.ctx = await self.browser.new_context(
                            viewport={'width': 1280, 'height': 720},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                     )

                     self.page = await self.ctx.new_page()
                     
                     if stealth_func:
                            try:
                                   await stealth_func(self.page)
                            except:
                                   pass

              except Exception:
                     print(f"[BROWSER] falha boot:")
                     if self.pw:
                            await self.pw.stop()
                            self.pw = None







       async def _ensure_alive(self):
              try:
                     if not self.browser or not self.browser.is_connected():
                            await self._boot_sequence()
                            return

                     if not self.ctx:
                            self.ctx = await self.browser.new_context(viewport={'width': 1280, 'height': 720})

                     try:
                            pages = self.ctx.pages
                            if not self.page or self.page.is_closed() or self.page not in pages:
                                   self.page = await self.ctx.new_page()
                                   if stealth_func:
                                          await stealth_func(self.page)
                     except:
                            self.page = await self.ctx.new_page()

              except Exception:
                     await self._boot_sequence()







       async def smart_search(self, termo, private=False):
              await self._ensure_alive()

              if private:
                     temp_ctx = await self.browser.new_context()
                     page = await temp_ctx.new_page()
                     if stealth_func:
                            try:
                                   await stealth_func(page)
                            except:
                                   pass
              else:
                     page = await self.ctx.new_page()
                     if stealth_func:
                            try:
                                   await stealth_func(page)
                            except:
                                   pass

              try:
                     await page.goto("https://www.google.com.br", timeout=20000)
                     await asyncio.sleep(random.uniform(1.0, 2.0))

                     content = await page.content()
                     if "Nossos sistemas detectaram tráfego incomum" in content:
                            return "Bloqueio de tráfego detectado. Resolva o CAPTCHA na janela."

                     search = page.get_by_role("combobox").or_(page.get_by_role("searchbox"))
                     await search.click()
                     
                     for char in termo:
                            await page.keyboard.type(char)
                            await asyncio.sleep(random.uniform(0.05, 0.15))

                     await page.keyboard.press("Enter")
                     await page.wait_for_load_state("networkidle", timeout=15000)
                     
                     return await self._extract_google_result(page)

              except Exception:
                     return f"Erro busca:"

              finally:
                     if private:
                            await temp_ctx.close()
                     else:
                            await page.close()







       async def _extract_google_result(self, page):
              try:
                     rhs = page.locator("#rhs")
                     if await rhs.count() > 0 and await rhs.is_visible():
                            text = await rhs.inner_text()
                            return text[:500]
                     
                     snippet = page.locator("div.VwiC3b").first
                     if await snippet.count() > 0:
                            return await snippet.inner_text()

                     return "Resultado extraído, verifique o navegador."
              except Exception:
                     return "Não foi possível extrair o texto."







       async def tocar_youtube(self, termo):
              await self._ensure_alive()

              try:
                     await self.page.goto(
                            f"https://www.youtube.com/results?search_query={termo}",
                            timeout=20000,
                     )

                     await asyncio.sleep(2)
                     video = self.page.locator("a#video-title").first
                     await video.wait_for(state="visible", timeout=10000)
                     await video.click()

                     return f"Tocando: {termo}"

              except Exception:
                     return f"Erro YouTube:"







       async def fechar_aba(self):
              if self.page and not self.page.is_closed():
                     await self.page.close()
                     return "Aba fechada"
              return "Nenhuma aba ativa"







       async def fechar_sistema(self):
              if self.browser:
                     await self.browser.close()
              if self.pw:
                     await self.pw.stop()
              if self.loop:
                     self.loop.stop()
              return "Sistema encerrado"







       async def navigate_to_blank(self):
              await self._ensure_alive()
              try:
                     await self.page.goto("about:blank")
                     return "Navegando para página em branco"
              except Exception:
                     return f"Erro ao navegar:"







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

       if "fechar" in cmd and "aba" in cmd:
              return jarvis_web.run(jarvis_web.fechar_aba())

       if "about:blank" in cmd or "página em branco" in cmd:
              return jarvis_web.run(jarvis_web.navigate_to_blank())

       return False