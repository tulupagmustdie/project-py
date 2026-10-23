from datetime import datetime

from classifier import classify_files, count_by_category


def print_files(files: list):
    """Выводит метаданные найденных файлов в терминал."""
    if not files:
        print("Подходящих файлов не найдено.")
        return

    for file_info in files:
        print(f"\nФайл: {file_info['name']}")
        print(f"  Расширение: {file_info['extension']}")
        print(f"  Размер: {file_info['size_bytes']} байт")
        print(f"  Изменён: {file_info['modified_at']}")


def print_sorting_plan(files: list):
    """Показывает будущие папки без изменения файлов."""
    print("\nПлан сортировки:")
    for file_info in files:
        print(f"{file_info['name']} -> {file_info['category']}/")
    if not files:
        print("Подходящих файлов не найдено.")
    print(f"Всего файлов: {len(files)}")
    print(f"Категорий: {len(count_by_category(files))}")


def build_statistics(files: list) -> dict:
    """Считает размеры, количество и доли файлов."""
    total_size = 0
    by_extension = {}
    by_category = {}
    file_count = len(files)
    for file_info in files:
        size = file_info["size_bytes"]
        total_size += size
        extension = file_info["extension"]
        if extension not in by_extension:
            by_extension[extension] = {"count": 0, "size_bytes": 0}
        by_extension[extension]["count"] += 1
        by_extension[extension]["size_bytes"] += size

        category = file_info["category"]
        if category not in by_category:
            by_category[category] = {
                "count": 0,
                "size_bytes": 0,
                "percentage": 0,
            }
        category_statistics = by_category[category]
        category_statistics["count"] += 1
        category_statistics["size_bytes"] += size

    for category_statistics in by_category.values():
        category_statistics["percentage"] = (
            category_statistics["count"] / file_count * 100
        )
    return {
        "file_count": file_count,
        "total_size_bytes": total_size,
        "by_extension": by_extension,
        "by_category": by_category,
    }


def print_statistics(statistics: dict):
    """Выводит общую статистику и распределение по категориям."""
    print("\nСтатистика по категориям:")
    for category, values in statistics["by_category"].items():
        print(
            f"{category}: {values['count']} файлов, "
            f"{values['size_bytes']} байт, {values['percentage']:.1f}%"
        )
    print(f"Всего файлов: {statistics['file_count']}")
    print(f"Общий размер: {statistics['total_size_bytes']} байт")


def build_report(folder, files: list, scanned_at: str, rules: dict) -> dict:
    """Собирает снимок сканирования и классификации для сохранения."""
    classified_files = classify_files(files, rules)
    report = {
        "folder": str(folder),
        "scanned_at": scanned_at,
        "classified_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rules": rules,
        "files": classified_files,
    }
    report.update(build_statistics(classified_files))
    return report


def print_move_plan(plan: list):
    """Показывает точные назначения перед подтверждением перемещения."""
    print("\nПлан сортировки:\n")
    for item in plan:
        destination = item["destination"].relative_to(item["folder"])
        print(f"{item['source'].name} -> {destination}")
    print(f"Будет перемещено: {len(plan)} файлов")
