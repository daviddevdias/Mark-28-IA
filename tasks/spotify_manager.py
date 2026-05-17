import os
import time
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
        self.sp = None
        scope = (
            "user-read-playback-state user-modify-playback-state "
            "user-read-currently-playing playlist-read-private"
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
        self.inicializado = True


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
            self.sp.start_playback(context_uri=uri_escolhida)
            return f"Executando a playlist {nome_exibicao} via API."
        except Exception:
            return "Ocorreu um erro ao conectar ou comandar a API do Spotify."


    def abrir_e_buscar(self, termo: str) -> str:
        if self.executar_via_api(termo):
            return f"Tocando {termo} imediatamente pela integração direta."
        termo_formatado = termo.replace(" ", "%20")
        os.system(f"start spotify:search:{termo_formatado}")
        return f"Comando de inicialização enviado para busca de {termo}."


    def controlar_reproducao(self, acao: str = "playpause") -> str:
        if not self.sp:
            return "API indisponível."
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
            return "Barramento de controle remoto falhou."

spotify_stark = SpotifyManager()