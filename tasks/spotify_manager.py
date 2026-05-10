import os
import time
import pyautogui
import pygetwindow as gw
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
from typing import Optional

class SpotifyManager:
    instancia_unica: Optional["SpotifyManager"] = None

    def __new__(cls) -> "SpotifyManager":
        if cls.instancia_unica is None:
            cls.instancia_unica = super(SpotifyManager, cls).__new__(cls)
            cls.instancia_unica.inicializado = False
        return cls.instancia_unica

    def __init__(self) -> None:
        if hasattr(self, "inicializado") and self.inicializado:
            return
        self.nome_janela: str = "Spotify"
        self.sp = None
        scope = (
            "user-read-playback-state user-modify-playback-state "
            "user-read-currently-playing playlist-read-private "
            "playlist-modify-public playlist-modify-private "
            "user-library-modify user-library-read "
            "user-top-read user-read-recently-played"
        )
        try:
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=config.SPOTIFY_ID,
                    client_secret=config.SPOTIFY_SECRET,
                    redirect_uri=config.SPOTIFY_REDIRECT_URI,
                    scope=scope,
                    cache_path=config.BASE_DIR / "api" / ".spotify_cache",
                )
            )
        except Exception:
            pass
        self.inicializado: bool = True

    def focar_spotify(self) -> bool:
        try:
            janelas = [
                w for w in gw.getAllWindows()
                if self.nome_janela.lower() in w.title.lower()
            ]
            if not janelas:
                return False
            win = janelas[0]
            if win.isMinimized:
                win.restore()
            pyautogui.press("alt")
            win.activate()
            return True
        except Exception:
            return False

    def executar_via_api(self, termo: str) -> bool:
        if not self.sp:
            return False
        try:
            resultados = self.sp.search(q=termo, limit=1, type='track')
            if resultados['tracks']['items']:
                track_uri = resultados['tracks']['items'][0]['uri']
                self.sp.start_playback(uris=[track_uri])
                return True
            return False
        except Exception:
            return False

    def listar_e_tocar_playlist(self, nome_busca: str = "") -> str:
        if not self.sp:
            return "API do Spotify não configurada."
        try:
            playlists = self.sp.current_user_playlists(limit=50)
            uri_escolhida = "spotify:user:me:collection"
            nome_exibicao = "Músicas Curtidas"
            if nome_busca:
                for playlist in playlists["items"]:
                    if nome_busca.lower() in playlist["name"].lower():
                        uri_escolhida = playlist["uri"]
                        nome_exibicao = playlist["name"]
                        break
            try:
                self.sp.start_playback(context_uri=uri_escolhida)
                return f"Executando a playlist {nome_exibicao} via API."
            except Exception:
                os.system(f"start {uri_escolhida}")
                time.sleep(7)
                if self.focar_spotify():
                    pyautogui.press("esc")
                    time.sleep(0.5)
                    pyautogui.press("playpause")
                    time.sleep(0.5)
                    pyautogui.press("space")
                    return f"Spotify ativado manualmente para tocar {nome_exibicao}."
                return "Spotify aberto, mas não consegui iniciar a música."
        except Exception:
            return "Ocorreu um erro ao conectar com o Spotify."

    def abrir_e_buscar(self, termo: str) -> str:
        if self.executar_via_api(termo):
            return f"Tocando {termo} imediatamente pela integração direta."
        termo_formatado = termo.replace(" ", "%20")
        os.system(f"start spotify:search:{termo_formatado}")
        time.sleep(4)
        if self.focar_spotify():
            pyautogui.press("tab", presses=2, interval=0.2)
            pyautogui.press("enter")
            return f"Busca local por {termo} executada."
        return "Aplicativo iniciado, mas necessita intervenção para tocar."

    def tocar_minhas_favoritas(self) -> str:
        if not self.sp:
            return "API ausente."
        try:
            self.sp.start_playback(context_uri="spotify:user:me:collection")
            return "Sua biblioteca de favoritas está tocando."
        except Exception:
            os.system("start spotify:collection:tracks")
            time.sleep(3)
            if self.focar_spotify():
                pyautogui.press("tab", presses=3, interval=0.1)
                pyautogui.press("enter")
                return "Favoritas ativadas pelo modo de segurança."
            return "Abri a lista de favoritas na sua tela."

    def controlar_reproducao(self, acao: str = "playpause") -> str:
        mapa_teclado = {
            "proxima": "nexttrack",
            "anterior": "prevtrack",
            "playpause": "playpause",
            "pause": "playpause",
            "tocar": "playpause",
            "continuar": "playpause",
        }
        if self.sp:
            try:
                acao_lower = acao.lower()
                if acao_lower in ["proxima", "proximo"]:
                    self.sp.next_track()
                elif acao_lower in ["anterior", "voltar"]:
                    self.sp.previous_track()
                elif acao_lower in ["pause", "pausar"]:
                    self.sp.pause_playback()
                elif acao_lower in ["continuar", "play", "retomar"]:
                    self.sp.start_playback()
                else:
                    atual = self.sp.current_playback()
                    if atual and atual["is_playing"]:
                        self.sp.pause_playback()
                    else:
                        self.sp.start_playback()
                return "Comando de reprodução aceito."
            except Exception:
                pass
        tecla = mapa_teclado.get(acao.lower(), "playpause")
        if acao.lower() == "anterior":
            pyautogui.press(tecla)
            time.sleep(0.2)
            pyautogui.press(tecla)
        else:
            pyautogui.press(tecla)
        return "Comando de teclado enviado ao sistema."

    def adicionar_aos_favoritos(self) -> str:
        if not self.sp:
            return "Inviável sem integração direta configurada."
        try:
            atual = self.sp.current_playback()
            if atual and atual["item"]:
                track_id = [atual["item"]["id"]]
                track_name = atual["item"]["name"]
                check = self.sp.current_user_saved_tracks_contains(track_id)
                if check[0]:
                    return f"A faixa '{track_name}' já é sua favorita."
                self.sp.current_user_saved_tracks_add(track_id)
                return f"Concluído. '{track_name}' guardada na biblioteca."
            return "Nenhuma música sendo reconhecida no momento."
        except Exception:
            return "Houve um bloqueio ao processar o salvamento."

spotify_stark = SpotifyManager()