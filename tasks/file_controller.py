from __future__ import annotations

import os
import shutil
import send2trash
import zipfile
from pathlib import Path
from datetime import datetime


def _resolve_path(raw: str) -> Path:
    try:
        shortcuts = {
            "desktop": Path.home() / "Desktop",
            "downloads": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "pictures": Path.home() / "Pictures",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
            "home": Path.home(),
            "root": Path(Path.home().anchor),
        }
        return shortcuts.get(raw.lower().strip(), Path(raw).expanduser().resolve())
    except Exception:
        return Path.home() / "Desktop"


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def _is_safe(path: Path) -> bool:
    caminho = str(path).lower()
    return not any(
        p in caminho for p in ["windows", "system32", "program files", "appdata"]
    )


def create_item(path: Path, content: str = "", is_folder: bool = False) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_folder:
            path.mkdir(exist_ok=True)
            return f"Pasta '{path.name}' criada em {path.parent}."
        else:
            path.write_text(content, encoding="utf-8")
            return f"Arquivo '{path.name}' criado em {path.parent}."
    except Exception as e:
        return f"Erro ao criar: {e}"


def read_file(path: Path) -> str:
    try:
        if not path.is_file():
            return f"Arquivo não encontrado: {path}"
        content = path.read_text(encoding="utf-8", errors="ignore")
        return content[:1500]
    except Exception as e:
        return f"Erro ao ler: {e}"


def delete_item(path: Path, permanent: bool = False) -> str:
    try:
        if not path.exists():
            return f"Item não encontrado: {path}"
        if not _is_safe(path):
            return "Operação bloqueada por segurança."
        if permanent:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return f"'{path.name}' deletado permanentemente."
        else:
            send2trash.send2trash(str(path))
            return f"'{path.name}' enviado para a lixeira."
    except Exception as e:
        return f"Erro ao deletar: {e}"


def backup_to_zip(path: Path, dest_name: str = "backup") -> str:
    try:
        if not path.exists():
            return f"Caminho não encontrado: {path}"
        zip_fn = f"{dest_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = path.parent / zip_fn
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if path.is_dir():
                for root, _, files in os.walk(path):
                    for file in files:
                        if file == zip_fn:
                            continue
                        f_path = os.path.join(root, file)
                        zipf.write(f_path, os.path.relpath(f_path, path))
            else:
                zipf.write(path, path.name)
        return f"Backup criado: {zip_path}"
    except Exception as e:
        return f"Erro no backup: {e}"


def organize_directory(target_path: Path) -> str:
    try:
        types = {
            "Imagens": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "Documentos": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov"],
            "Audios": [".mp3", ".wav", ".ogg", ".flac"],
            "Compactados": [".zip", ".rar", ".7z", ".tar"],
            "Codigos": [".py", ".json", ".js", ".ts", ".html", ".css"],
        }
        moved = 0
        for file in target_path.iterdir():
            if not file.is_file():
                continue
            for folder, exts in types.items():
                if file.suffix.lower() in exts:
                    dest = target_path / folder
                    dest.mkdir(exist_ok=True)
                    shutil.move(str(file), str(dest / file.name))
                    moved += 1
                    break
        return f"{moved} arquivo(s) organizados em {target_path}."
    except Exception as e:
        return f"Erro ao organizar: {e}"


def list_directory(base_path: Path) -> str:
    try:
        itens = [f.name for f in base_path.iterdir()][:20]
        if not itens:
            return "Diretório vazio."
        return "\n".join(itens)
    except Exception as e:
        return f"Erro ao listar: {e}"


def disk_usage(base_path: Path) -> str:
    try:
        uso = shutil.disk_usage(base_path)
        total = _format_size(uso.total)
        usado = _format_size(uso.used)
        livre = _format_size(uso.free)
        return f"Disco em {base_path}: Total={total} | Usado={usado} | Livre={livre}"
    except Exception as e:
        return f"Erro ao obter uso de disco: {e}"


def file_controller(params: dict) -> str:
    action = params.get("action", "").lower()
    base_path = _resolve_path(params.get("path", "desktop"))
    name = params.get("name", "")
    full_path = base_path / name if name else base_path

    actions = {
        "list": lambda: list_directory(base_path),
        "create_file": lambda: create_item(full_path, params.get("content", "")),
        "create_folder": lambda: create_item(full_path, is_folder=True),
        "delete": lambda: delete_item(full_path, params.get("permanent", False)),
        "read": lambda: read_file(full_path),
        "organize": lambda: organize_directory(base_path),
        "backup": lambda: backup_to_zip(full_path, params.get("dest_name", "backup_auto")),
        "disk": lambda: disk_usage(base_path),
    }

    fn = actions.get(action)
    if fn:
        return fn()
    return f"Ação '{action}' não reconhecida. Opções: {', '.join(actions.keys())}"