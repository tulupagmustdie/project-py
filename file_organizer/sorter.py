from os import link
from pathlib import Path
from stat import S_ISDIR, S_ISREG

from classifier import classify_file


def create_sort_plan(files: list, folder: Path, rules: dict) -> list:
    """Создаёт план без изменений на диске. Ожидает проверенные правила."""
    folder = Path(folder).resolve(strict=True)
    folder_info = folder.stat()
    if not S_ISDIR(folder_info.st_mode):
        raise ValueError("Для сортировки нужно указать папку.")

    plan = []
    for file_info in files:
        name = file_info["name"]
        category = classify_file(file_info["extension"], rules)
        for value in (name, category):
            if (
                not isinstance(value, str) or not value.strip()
                or value.startswith(".") or "/" in value
                or "\\" in value or "\x00" in value
            ):
                raise ValueError(f"Небезопасное имя файла или категории: {value!r}")

        expected = {}
        for key in ("size_bytes", "mtime_ns", "ctime_ns", "device", "inode"):
            if key not in file_info:
                raise ValueError("Недостаточно метаданных: просканируйте папку заново.")
            expected[key] = file_info[key]
        plan.append({
            "folder": folder,
            "folder_device": folder_info.st_dev,
            "folder_inode": folder_info.st_ino,
            "source": folder / name,
            "destination": folder / category / name,
            "expected": expected,
        })
    return plan


def move_files(plan: list) -> dict:
    """Выполняет готовый план. Вызывать только после подтверждения пользователя."""
    result = {"moved": 0, "skipped": 0, "errors": 0}
    for item in plan:
        source = item["source"]
        destination = item["destination"]
        folder = item["folder"]
        expected = item["expected"]
        linked = False
        try:
            folder_info = folder.stat(follow_symlinks=False)
            if (
                not S_ISDIR(folder_info.st_mode)
                or folder_info.st_dev != item["folder_device"]
                or folder_info.st_ino != item["folder_inode"]
            ):
                raise ValueError("Исходная папка была заменена.")
            if source.parent != folder or destination.parent.parent != folder:
                raise ValueError("Пути плана выходят за пределы выбранной папки.")
            metadata = source.stat(follow_symlinks=False)
            if not S_ISREG(metadata.st_mode) or source.name.startswith("."):
                raise ValueError("Источник не является обычным видимым файлом.")
            if (
                metadata.st_size != expected["size_bytes"]
                or metadata.st_mtime_ns != expected["mtime_ns"]
                or metadata.st_ctime_ns != expected["ctime_ns"]
                or metadata.st_dev != expected["device"]
                or metadata.st_ino != expected["inode"]
            ):
                raise ValueError("Файл изменился после сканирования.")

            category_folder = destination.parent
            if category_folder.is_symlink():
                raise ValueError("Папка категории является символической ссылкой.")
            if category_folder.exists() and not category_folder.is_dir():
                raise ValueError("Вместо папки категории находится файл.")
            category_folder.mkdir(exist_ok=True)
            if not S_ISDIR(category_folder.stat(follow_symlinks=False).st_mode):
                raise ValueError("Папка категории была заменена.")

            # link не перезаписывает даже появившееся в последний момент имя.
            link(source, destination, follow_symlinks=False)
            linked = True
            # Создание жёсткой ссылки меняет ctime, поэтому здесь его не сравниваем.
            for path in (source, destination):
                current = path.stat(follow_symlinks=False)
                if (
                    not S_ISREG(current.st_mode)
                    or current.st_dev != expected["device"]
                    or current.st_ino != expected["inode"]
                    or current.st_size != expected["size_bytes"]
                    or current.st_mtime_ns != expected["mtime_ns"]
                ):
                    raise ValueError("Файл изменился во время сортировки.")
            source.unlink()
        except (OSError, ValueError) as error:
            if linked:
                result["errors"] += 1
                print(f"Ошибка: {source.name}: {error}. Целевое имя сохранено: {destination}")
            elif isinstance(error, (ValueError, FileNotFoundError, FileExistsError)):
                result["skipped"] += 1
                print(f"Пропущено: {source.name}: {error}")
            else:
                result["errors"] += 1
                print(f"Ошибка: {source.name}: {error}")
        else:
            result["moved"] += 1
    return result
