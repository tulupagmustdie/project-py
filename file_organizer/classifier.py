import json
from pathlib import Path


def load_rules(config_path: Path) -> dict:
    """Читает конфигурацию и возвращает проверенные правила."""
    try:
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except FileNotFoundError as error:
        raise ValueError(f"Файл конфигурации не найден: {config_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Ошибка JSON в конфигурации: строка {error.lineno}, "
            f"столбец {error.colno}."
        ) from error
    except UnicodeError as error:
        raise ValueError("Конфигурация должна быть сохранена в UTF-8.") from error
    except OSError as error:
        raise ValueError(f"Не удалось прочитать конфигурацию: {error}") from error

    if not isinstance(config, dict):
        raise ValueError("Конфигурация должна быть словарём категорий и расширений.")

    rules = {}
    extension_categories = {}
    for category, extensions in config.items():
        if not category.strip():
            raise ValueError("Название категории не должно быть пустым.")
        if not isinstance(extensions, list):
            raise ValueError(f"Категория «{category}» должна содержать список расширений.")

        rules[category] = []
        for extension in extensions:
            if not isinstance(extension, str):
                raise ValueError(f"Расширения в категории «{category}» должны быть строками.")
            extension = extension.strip().lower()
            if not extension or extension == ".":
                raise ValueError(f"Пустое расширение в категории «{category}».")
            if not extension.startswith("."):
                extension = "." + extension

            if extension in extension_categories:
                previous_category = extension_categories[extension]
                if previous_category != category:
                    raise ValueError(
                        f"Расширение {extension} указано в двух категориях: "
                        f"«{previous_category}» и «{category}»."
                    )
                continue

            extension_categories[extension] = category
            rules[category].append(extension)

    return rules


def classify_file(extension: str, rules: dict) -> str:
    """Определяет категорию по расширению, используя проверенные правила."""
    extension = extension.strip().lower()
    if not extension or extension == "без расширения":
        return "Прочее"
    if not extension.startswith("."):
        extension = "." + extension

    for category, extensions in rules.items():
        if extension in extensions:
            return category
    return "Прочее"


def classify_files(files: list, rules: dict) -> list:
    """Возвращает копии записей файлов с добавленной категорией."""
    classified_files = []
    for file_info in files:
        classified_file = file_info.copy()
        classified_file["category"] = classify_file(file_info["extension"], rules)
        classified_files.append(classified_file)
    return classified_files


def count_by_category(files: list) -> dict:
    """Считает файлы по категориям после классификации."""
    counts = {}
    for file_info in files:
        category = file_info["category"]
        if category not in counts:
            counts[category] = 0
        counts[category] += 1
    return counts
