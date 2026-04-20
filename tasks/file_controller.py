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





def create_item(path: Path, content: str = "", is_folder: bool = False):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        if is_folder:
            path.mkdir(exist_ok=True)
        else:
            path.write_text(content, encoding="utf-8")

    except Exception as e:
        print(f"Erro: {e}")





def read_file(path: Path):
    try:
        if not path.is_file():
            return print("Alvo inválido.")

        content = path.read_text(encoding="utf-8", errors="ignore")
        print(content[:1500])

    except Exception as e:
        print(f"Erro: {e}")





def delete_item(path: Path, permanent: bool = False):
    try:
        if not path.exists() or not _is_safe(path):
            return print("Bloqueado.")

        if permanent:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        else:
            send2trash.send2trash(str(path))

    except Exception as e:
        print(f"Erro: {e}")





def backup_to_zip(path: Path, dest_name: str = "backup"):
    try:
        if not path.exists():
            return

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

    except Exception as e:
        print(f"Erro: {e}")





def organize_directory(target_path: Path):
    try:
        types = {
            "Imagens": [".jpg", ".png", ".gif"],
            "Documentos": [".pdf", ".docx", ".txt"],
            "Videos": [".mp4", ".mkv"],
            "Audios": [".mp3", ".wav"],
            "Compactados": [".zip", ".rar"],
            "Codigos": [".py", ".json", ".js"],
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

    except Exception as e:
        print(f"Erro: {e}")





def file_controller(params: dict):
    action = params.get("action", "").lower()
    base_path = _resolve_path(params.get("path", "desktop"))
    name = params.get("name", "")
    full_path = base_path / name if name else base_path

    actions = {
        "list": lambda: print("\n".join([f.name for f in base_path.iterdir()][:15])),
        "create_file": lambda: create_item(full_path, params.get("content", "")),
        "create_folder": lambda: create_item(full_path, is_folder=True),
        "delete": lambda: delete_item(full_path, params.get("permanent", False)),
        "read": lambda: read_file(full_path),
        "organize": lambda: organize_directory(base_path),
        "backup": lambda: backup_to_zip(full_path, params.get("dest_name", "backup_auto")),
        "disk": lambda: print(f"Uso de Disco: {shutil.disk_usage(base_path).used / (1024**3):.1f} GB"),
    }

    if action in actions:
        actions[action]()
    else:
        print("Diretriz não reconhecida.")