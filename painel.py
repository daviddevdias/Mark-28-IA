import json
import config
import psutil
from pathlib import Path
import asyncio

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl, QTimer
from PyQt6.QtWidgets import QMainWindow


_main_loop = None

CONFIG_CORE_FILE = "config_core.json"
SMART_FILE = "config_smart.json"
NOTAS_FILE = "notas.json"

CAMPOS_CONFIG_CORE = {
    "nome_mestre",
    "cidade_padrao",
    "voz",
    "device_index",
    "modo_silencioso",
    "tema_ativo",
    "THEME_ACTIVE",
    "tema",
    "tema_custom_accent",
    "tema_custom_secondary",
    "tema_custom_bg",
    "ia_mode",
}

def _resolver_arquivo(chave: str) -> str:
    if chave == "notas":
        return NOTAS_FILE
    if chave in CAMPOS_CONFIG_CORE:
        return CONFIG_CORE_FILE
    return SMART_FILE

def _limpar_prefixo(cmd: str) -> str:
    c = cmd.strip().lower()
    for prefixo in ("core,", "core"):
        if c.startswith(prefixo):
            c = c[len(prefixo):].strip()
    return c

class JarvisBridge(QObject):
    dados_para_ui = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cpu_atual = 0.0
        self.ram_atual = 0.0

    @pyqtSlot(str)
    def executar_comando(self, cmd: str):
        global _main_loop
        diretriz = _limpar_prefixo(cmd)

        if _main_loop is not None and not _main_loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._executar_e_emitir(diretriz), _main_loop
            )

        self.dados_para_ui.emit(json.dumps({"resposta": f"Processando: {diretriz}"}))

    async def _executar_e_emitir(self, diretriz: str):
        try:
            from engine.core import processar_comando
            processou = await processar_comando(diretriz)

            if processou:
                self.dados_para_ui.emit(json.dumps({"resposta": "Comando enviado ao core."}))

        except Exception as e:
            self.dados_para_ui.emit(json.dumps({"resposta": f"Erro: {e}"}))

    @pyqtSlot(str, result=str)
    def alternar_ia(self, modo: str) -> str:
        from engine.ia_router import router

        msg = router.definir_modo(modo)
        status = router.status

        self.dados_para_ui.emit(json.dumps({
            "resposta": msg,
            "ia_status": status
        }))

        return json.dumps({"ok": True, "modo": modo, "msg": msg})

    @pyqtSlot(result=str)
    def obter_ia_status(self) -> str:
        from engine.ia_router import router
        return json.dumps(router.status)

    @pyqtSlot(str, str)
    def salvar_configuracao(self, chave: str, valor: str):
        config.__dict__[chave] = valor

        try:
            config.update_memory("config_core.json", {chave: valor})
        except Exception:
            pass

    @pyqtSlot(result=str)
    def obter_biblioteca_comandos(self) -> str:
        biblioteca = []

        for nome, dados in config.COMANDOS_JARVIS.items():
            biblioteca.append({
                "cmd": nome.upper(),
                "cat": dados.get("cat", "GERAL"),
                "desc": dados.get("desc", ""),
                "poder": dados.get("poder", "⚡"),
                "passos": dados.get("passos", []),
                "handler": nome.replace("core,", "").strip(),
                "icon": "◈",
            })

        return json.dumps(biblioteca)

    @pyqtSlot(result=str)
    def obter_configuracoes_atuais(self) -> str:
        from engine.ia_router import router
        dados = config._carregar_json(config.API_DIR / CONFIG_CORE_FILE)

        return json.dumps({
            "gemini": config.GEMINI_API_KEY,
            "qwen": config.QWEN_API_KEY,
            "spotify_id": config.SPOTIFY_ID,
            "spotify_sec": config.SPOTIFY_SECRET,
            "smartthings": config.SMARTTHINGS_TOKEN,
            "nome_mestre": config.NOME_MESTRE,
            "ia_mode": router.modo_atual,
            "notas": config.notas,
            "cidade_padrao": dados.get("cidade_padrao", "São Paulo")
        })

    @pyqtSlot(result=str)
    def obter_temas_sistema(self) -> str:
        try:
            from app_ul.theme import TEMAS_CORE
            return json.dumps(TEMAS_CORE)
        except Exception:
            return json.dumps({})

    @pyqtSlot(result=str)
    def obter_tema_ativo(self) -> str:
        dados = config._carregar_json(config.API_DIR / CONFIG_CORE_FILE)
        tema = dados.get("tema", dados.get("tema_ativo", ""))
        return json.dumps(tema)

    @pyqtSlot(result=str)
    def get_status(self) -> str:
        return json.dumps({
            "cpu": self.cpu_atual,
            "ram": self.ram_atual,
            "online": True
        })

    @pyqtSlot()
    def solicitar_analise_visual(self):
        global _main_loop
        if _main_loop is not None and not _main_loop.is_closed():
            import asyncio
            asyncio.run_coroutine_threadsafe(self._rotina_visao_ui(), _main_loop)

    async def _rotina_visao_ui(self):
        try:
            from vision.capture import capturar_frame_base64, analisar_tela
            import asyncio
            
            self.dados_para_ui.emit(json.dumps({"visao_status": "A capturar o ecrã..."}))
            
            loop = asyncio.get_running_loop()
            b64 = await loop.run_in_executor(None, capturar_frame_base64)
            
            if not b64:
                self.dados_para_ui.emit(json.dumps({"visao_erro": "Falha na captura."}))
                return
                
            self.dados_para_ui.emit(json.dumps({
                "visao_img": b64, 
                "visao_status": "Imagem capturada. A enviar para a rede neural..."
            }))
            
            analise = await analisar_tela("Analisa este ecrã e diz-me o que o utilizador está a fazer ou se há algum erro visível.")
            
            self.dados_para_ui.emit(json.dumps({"visao_resultado": analise}))
            
        except Exception as e:
            self.dados_para_ui.emit(json.dumps({"visao_erro": str(e)}))

    @pyqtSlot(str)
    def solicitar_clima(self, cidade: str):
        if not cidade:
            dados = config._carregar_json(config.API_DIR / CONFIG_CORE_FILE)
            cidade = dados.get("cidade_padrao", "São Paulo")

        global _main_loop
        if _main_loop is not None and not _main_loop.is_closed():
            import asyncio
            asyncio.run_coroutine_threadsafe(self._rotina_clima(cidade), _main_loop)

    async def _rotina_clima(self, cidade: str):
        try:
            from tasks.weather import obter_clima_raw
            import asyncio
            loop = asyncio.get_running_loop()
            
            resultado_str = await loop.run_in_executor(None, obter_clima_raw, cidade)
            resultado_json = json.loads(resultado_str)
            
            self.dados_para_ui.emit(json.dumps({"clima_dados": resultado_json, "cidade_buscada": cidade}))
        except Exception as e:
            self.dados_para_ui.emit(json.dumps({"erro": f"Erro clima: {e}"}))

class PainelCore(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S ◈ MARK XXVIII")
        self.resize(1480, 750)

        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        self.channel = QWebChannel()
        self.bridge = JarvisBridge()

        self.channel.registerObject("jarvis", self.bridge)
        self.view.page().setWebChannel(self.channel)

        caminho_html = Path(__file__).resolve().parent / "web" / "index.html"
        self.view.load(QUrl.fromLocalFile(str(caminho_html)))

        self.timer_metricas = QTimer()
        self.timer_metricas.timeout.connect(self._atualizar_hardware)
        self.timer_metricas.start(2000)

        self.timer_ia = QTimer()
        self.timer_ia.timeout.connect(self._atualizar_ia_status)
        self.timer_ia.start(15000)

    def _enviar_para_html(self, json_str: str):
        script = f"if(window.receberDoJarvis){{window.receberDoJarvis({json_str});}}"
        self.view.page().runJavaScript(script)

    def _atualizar_hardware(self):
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent

            self.bridge.cpu_atual = cpu
            self.bridge.ram_atual = ram

            self._enviar_para_html(json.dumps({"cpu": cpu, "ram": ram}))
        except Exception:
            pass

    def _atualizar_ia_status(self):
        try:
            from engine.ia_router import router
            self._enviar_para_html(json.dumps({"ia_status": router.status}))
        except Exception:
            pass

def set_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop