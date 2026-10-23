import json
from datetime import datetime
from pathlib import Path

from classifier import load_rules
from report import (
    build_report, print_files, print_move_plan, print_sorting_plan, print_statistics,
)
from scanner import scan_folder, validate_folder
from storage import load_report, save_report
from sorter import create_sort_plan, move_files


PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIR / "config.json"
REPORT_PATH = PROJECT_DIR / "data" / "last_scan.json"


def show_previous_report():
    if input("Прочитать предыдущий отчёт? [д/Н]: ").strip().lower() != "д":
        return
    try:
        previous = load_report(REPORT_PATH)
    except (OSError, ValueError) as error:
        print(f"Не удалось прочитать предыдущий отчёт: {error}")
        return
    print("\nПредыдущий отчёт (сохранённые данные):")
    print("Это снимок сканирования, а не текущее состояние папки.")
    print(json.dumps(previous, ensure_ascii=False, indent=2))


def prepare_report(action: str, current_report) -> dict:
    """Готовит отчёт по новой папке или результатам прошлого сканирования."""
    rules = load_rules(CONFIG_PATH)
    if action == "1":
        folder = validate_folder(input("Введите путь к папке: ").strip())
        # Отчёт не должен менять содержимое сканируемой папки.
        if folder == REPORT_PATH.parent.resolve():
            raise ValueError("Папку хранения отчётов сканировать нельзя.")
        files = scan_folder(folder)
        scanned_at = datetime.now().astimezone().isoformat(timespec="seconds")
    else:
        folder = current_report["folder"]
        files = current_report["files"]
        scanned_at = current_report["scanned_at"]
    return build_report(folder, files, scanned_at, rules)


def main():
    show_previous_report()
    current_report = None
    while True:
        print(
            "\nFile Organizer\n\n"
            "1. Сканировать папку\n"
            "2. Показать классификацию файлов\n"
            "3. Показать статистику\n"
            "4. Разложить файлы по папкам\n"
            "5. Выйти"
        )
        action = input("Выберите действие: ").strip()
        if action == "5":
            return
        if action not in ("1", "2", "3", "4"):
            print("Введите число от 1 до 5.")
            continue
        if action != "1" and current_report is None:
            print("Сначала просканируйте папку: пункт 1.")
            continue

        if action == "4":
            try:
                rules = load_rules(CONFIG_PATH)
                plan = create_sort_plan(
                    current_report["files"], Path(current_report["folder"]), rules,
                )
            except (OSError, ValueError, RuntimeError) as error:
                print(f"Не удалось подготовить сортировку: {error}")
                continue
            print_move_plan(plan)
            if not plan:
                continue
            if input("Продолжить? (да/нет): ") != "да":
                print("Сортировка отменена.")
                continue
            # После попытки перемещения снимок больше нельзя использовать.
            current_report = None
            result = move_files(plan)
            print("\nСортировка завершена.")
            print(f"Перемещено: {result['moved']}")
            print(f"Пропущено: {result['skipped']}")
            print(f"Ошибок: {result['errors']}")
            print(
                "Просканируйте папку заново. Сохранённый JSON содержит "
                "снимок до сортировки."
            )
            continue

        try:
            new_report = prepare_report(action, current_report)
        except (OSError, ValueError, RuntimeError) as error:
            print(f"Не удалось выполнить действие: {error}")
            continue

        current_report = new_report
        if action == "1":
            print(f"\nПапка: {current_report['folder']}")
            print_files(current_report["files"])
        elif action == "2":
            print_sorting_plan(current_report["files"])
        else:
            print_statistics(current_report)
        try:
            save_report(current_report, REPORT_PATH)
        except (OSError, ValueError, TypeError) as error:
            print(f"Не удалось сохранить новый отчёт: {error}")
        else:
            print("Отчёт сохранён в data/last_scan.json.")


if __name__ == "__main__":
    main()
