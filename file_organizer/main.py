import json
from datetime import datetime
from pathlib import Path

from classifier import load_rules
from report import build_report, print_files, print_sorting_plan, print_statistics
from scanner import scan_folder, validate_folder
from storage import load_report, save_report


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
            "4. Выйти"
        )
        action = input("Выберите действие: ").strip()
        if action == "4":
            return
        if action not in ("1", "2", "3"):
            print("Введите число от 1 до 4.")
            continue
        if action != "1" and current_report is None:
            print("Сначала просканируйте папку: пункт 1.")
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
