import os
import time
import pyautogui
import pygetwindow as gw
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
from typing import Optional


class SpotifyManager:
    _instance: Optional["SpotifyManager"] = None

    def __new__(cls) -> "SpotifyManager":
        if cls._instance is None:
            cls._instance = super(SpotifyManager, cls).__new__(cls)
            cls._instance._inicializado = False
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_inicializado") and self._inicializado:
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
        except Exception as e:
            print(f"[SPOTIFY] Falha ao inicializar API: {e}")

        self._inicializado: bool = True

    def _focar_spotify(self) -> bool:
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
        except Exception as e:
            print(f"[SPOTIFY] Erro window manager: {e}")
            return False

    def listar_e_tocar_playlist(self, nome_busca: str = "") -> str:
        if not self.sp:
            return "API do Spotify não configurada no Painel."

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
                return f"Executando {nome_exibicao}, Chefe."
            except Exception:
                print("[SPOTIFY] Player offline. Forcando via Shell...")
                os.system(f"start {uri_escolhida}")
                time.sleep(7)

                if self._focar_spotify():
                    pyautogui.press("esc")
                    time.sleep(0.5)
                    pyautogui.press("playpause")
                    time.sleep(0.5)
                    pyautogui.press("space")
                    return f"Spotify despertado. {nome_exibicao} em execucao."
                return "Spotify aberto, mas o foco da janela falhou."

        except Exception as e:
            print(f"[SPOTIFY] Erro critico: {e}")
            return "Erro nos protocolos de audio."

    def abrir_e_buscar(self, termo: str) -> str:
        termo_formatado = termo.replace(" ", "%20")
        os.system(f"start spotify:search:{termo_formatado}")
        time.sleep(4)
        if self._focar_spotify():
            pyautogui.press("tab", presses=2, interval=0.2)
            pyautogui.press("enter")
            return f"Busca por {termo} concluida no player."
        return "Spotify aberto. Busca pode precisar de interacao manual."

    def tocar_minhas_favoritas(self) -> str:
        os.system("start spotify:collection:tracks")
        time.sleep(3)
        if self._focar_spotify():
            pyautogui.press("tab", presses=3, interval=0.1)
            pyautogui.press("enter")
            return "Playlist de favoritas em execucao."
        return "Spotify aberto com favoritas."

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
                return ""
            except Exception:
                pass

        tecla = mapa_teclado.get(acao.lower(), "playpause")
        if acao.lower() == "anterior":
            pyautogui.press(tecla)
            time.sleep(0.2)
            pyautogui.press(tecla)
        else:
            pyautogui.press(tecla)
        return ""

    def adicionar_aos_favoritos(self) -> str:
        if not self.sp:
            return "API do Spotify nao configurada."
        try:
            atual = self.sp.current_playback()
            if atual and atual["item"]:
                track_id = [atual["item"]["id"]]
                track_name = atual["item"]["name"]
                check = self.sp.current_user_saved_tracks_contains(track_id)
                if check[0]:
                    return f"A faixa '{track_name}' ja consta na base de dados."
                self.sp.current_user_saved_tracks_add(track_id)
                return f"'{track_name}' adicionada aos favoritos."
            return ""
        except Exception as e:
            print(f"[SPOTIFY] Erro favoritos: {e}")
            return ""


spotify_stark = SpotifyManager()