import json
from pathlib import Path
from tempfile import NamedTemporaryFile


def save_report(report: dict, report_path: Path):
    """Сохраняет новый отчёт, заменяя старый только после успешной записи."""
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=report_path.parent,
            prefix=".scan-", suffix=".tmp", delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(text)
        temporary_path.replace(report_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_report(report_path: Path) -> dict:
    """Читает предыдущий отчёт для просмотра."""
    with report_path.open(encoding="utf-8") as report_file:
        report = json.load(report_file)
    if not isinstance(report, dict):
        raise ValueError("Отчёт должен содержать JSON-объект.")
    required = [
        "folder", "scanned_at", "classified_at", "rules", "files",
        "file_count", "total_size_bytes", "by_extension", "by_category",
    ]
    for key in required:
        if key not in report:
            raise ValueError(f"В отчёте отсутствует поле {key}.")
    return report
