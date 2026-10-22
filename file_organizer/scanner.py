from datetime import datetime
from pathlib import Path


def validate_folder(folder_text: str) -> Path:
    """Проверяет введённый путь и возвращает абсолютный путь к папке."""
    if not folder_text:
        raise ValueError("Путь к папке не введён.")

    folder = Path(folder_text).expanduser().resolve()
    if not folder.exists():
        raise FileNotFoundError(f"Папка не существует: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Указанный путь не является папкой: {folder}")
    return folder


def scan_folder(folder: Path) -> list:
    """Собирает метаданные файлов только на первом уровне папки."""
    files = []

    # Ошибку чтения самой папки обрабатывает main(), а не цикл ниже.
    for entry in sorted(folder.iterdir()):
        if entry.name.startswith("."):
            continue

        try:
            # Ссылку проверяем до is_file(), который следует по ссылкам.
            if entry.is_symlink() or not entry.is_file():
                continue

            metadata = entry.stat()
            modified_at = datetime.fromtimestamp(metadata.st_mtime)
            file_info = {
                "name": entry.name,
                "extension": entry.suffix.lower() or "без расширения",
                "size_bytes": metadata.st_size,
                "modified_at": modified_at.isoformat(timespec="seconds"),
            }
        except (OSError, ValueError, OverflowError) as error:
            print(f"Предупреждение: не удалось прочитать {entry.name}: {error}")
            continue

        files.append(file_info)

    return files
