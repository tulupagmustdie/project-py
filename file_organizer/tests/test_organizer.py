import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

import main
from classifier import load_rules, classify_file, classify_files, count_by_category
from report import build_report, build_statistics
from scanner import scan_folder, validate_folder
from storage import load_report, save_report


PROJECT_DIR = Path(__file__).resolve().parent.parent


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(dir=PROJECT_DIR / "test_files")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / "source"
        self.folder.mkdir()
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            (PROJECT_DIR / "config.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.report_path = self.root / "reports" / "last_scan.json"
        self.rules = load_rules(self.config_path)

    def make_report(self):
        return build_report(
            self.folder, scan_folder(self.folder), "2026-01-01", self.rules,
        )

    def run_menu(self, answers):
        with patch.object(main, "CONFIG_PATH", self.config_path):
            with patch.object(main, "REPORT_PATH", self.report_path):
                with patch("builtins.input", side_effect=answers):
                    with redirect_stdout(io.StringIO()) as output:
                        main.main()
        return output.getvalue()

    def test_file_categories(self):
        examples = {
            "lecture.pdf": "Документы", "photo.JPG": "Изображения",
            "README": "Прочее", "unknown.xyz": "Прочее",
            "report.final.pdf": "Документы", "архив с пробелами.tar.gz": "Архивы",
        }
        for name in examples:
            (self.folder / name).touch()
        files = scan_folder(self.folder)
        classified = classify_files(files, self.rules)
        self.assertEqual(
            {item["name"]: item["category"] for item in classified}, examples,
        )
        self.assertTrue(all("category" not in item for item in files))
        self.assertEqual(count_by_category(classified)["Документы"], 2)
        self.assertEqual(classify_file(".JPG", self.rules), "Изображения")

    def test_empty_folder(self):
        report = self.make_report()
        self.assertEqual(report["file_count"], 0)
        self.assertEqual(report["total_size_bytes"], 0)
        self.assertEqual(report["by_category"], {})
        save_report(report, self.report_path)
        self.assertEqual(load_report(self.report_path), report)

    def test_scanner_filters_and_invalid_paths(self):
        (self.folder / "visible.txt").write_bytes(b"abc")
        (self.folder / ".hidden").touch()
        (self.folder / "nested").mkdir()
        (self.folder / "nested" / "inside.txt").touch()
        (self.folder / "link.txt").symlink_to("visible.txt")
        (self.folder / "broken.txt").symlink_to("missing.txt")
        files = scan_folder(self.folder)
        self.assertEqual([item["name"] for item in files], ["visible.txt"])
        self.assertEqual(files[0]["size_bytes"], 3)
        with self.assertRaises(FileNotFoundError):
            validate_folder(str(self.folder / "missing"))
        with self.assertRaises(NotADirectoryError):
            validate_folder(str(self.folder / "visible.txt"))
        with self.assertRaises(ValueError):
            validate_folder("")

    def test_metadata_error_continues(self):
        (self.folder / "bad.txt").touch()
        (self.folder / "good.txt").touch()
        original_stat = Path.stat

        def failing_stat(path, *args, **kwargs):
            if path.name == "bad.txt":
                raise PermissionError("Нет доступа")
            return original_stat(path, *args, **kwargs)

        with patch.object(Path, "stat", failing_stat):
            with redirect_stdout(io.StringIO()) as output:
                files = scan_folder(self.folder)
        self.assertEqual([item["name"] for item in files], ["good.txt"])
        self.assertIn("Предупреждение", output.getvalue())

    def test_invalid_configurations(self):
        examples = [
            "{", "[]", '{"A": ".pdf"}', '{"A": null}',
            '{"A": [12]}', '{"A": [""]}', '{"A": ["."]}',
            '{"A": ["PDF"], "B": [".pdf"]}', '{"": []}',
        ]
        for text in examples:
            with self.subTest(text=text):
                self.config_path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_rules(self.config_path)
        self.config_path.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            load_rules(self.config_path)
        self.config_path.unlink()
        with self.assertRaises(ValueError):
            load_rules(self.config_path)

    def test_custom_rules(self):
        self.config_path.write_text(
            json.dumps({"Фото": ["JPG", ".jpg"], "Новое": [" xyz "]}),
            encoding="utf-8",
        )
        rules = load_rules(self.config_path)
        self.assertEqual(rules["Фото"], [".jpg"])
        self.assertEqual(classify_file(".JPG", rules), "Фото")
        self.assertEqual(classify_file(".xyz", rules), "Новое")
        self.assertEqual(classify_file("без расширения", rules), "Прочее")

    def test_statistics(self):
        files = [
            {"extension": ".pdf", "size_bytes": 10},
            {"extension": ".txt", "size_bytes": 20},
            {"extension": ".jpg", "size_bytes": 30},
        ]
        stats = build_statistics(classify_files(files, self.rules))
        self.assertEqual(stats["file_count"], 3)
        self.assertEqual(stats["total_size_bytes"], 60)
        documents = stats["by_category"]["Документы"]
        self.assertEqual(documents["count"], 2)
        self.assertEqual(documents["size_bytes"], 30)
        self.assertAlmostEqual(documents["percentage"], 200 / 3)
        self.assertAlmostEqual(
            sum(item["percentage"] for item in stats["by_category"].values()), 100,
        )
        self.assertEqual(stats["by_extension"][".jpg"]["size_bytes"], 30)

    def test_save_failure_preserves_previous(self):
        report = self.make_report()
        save_report(report, self.report_path)
        previous = self.report_path.read_bytes()
        with patch.object(Path, "replace", side_effect=PermissionError("Нет доступа")):
            with self.assertRaises(OSError):
                save_report({"new": True}, self.report_path)
        self.assertEqual(self.report_path.read_bytes(), previous)
        self.assertEqual(list(self.report_path.parent.glob("*.tmp")), [])
        with self.assertRaises(TypeError):
            save_report({"invalid": object()}, self.report_path)
        self.assertEqual(self.report_path.read_bytes(), previous)

    def test_menu_uses_cached_scan_and_keeps_source(self):
        file_path = self.folder / "report.pdf"
        file_path.write_bytes(b"example")
        before = file_path.stat().st_mtime_ns
        with patch.object(main, "scan_folder", wraps=scan_folder) as scanner:
            output = self.run_menu(
                ["н", "2", "bad", "1", str(self.folder), "2", "3", "4"],
            )
        self.assertEqual(scanner.call_count, 1)
        self.assertIn("report.pdf -> Документы/", output)
        self.assertIn("100.0%", output)
        self.assertEqual(file_path.read_bytes(), b"example")
        self.assertEqual(file_path.stat().st_mtime_ns, before)
        self.assertEqual(list(self.folder.iterdir()), [file_path])
        report = load_report(self.report_path)
        self.assertEqual(report["rules"], self.rules)
        self.assertIn("classified_at", report)
        self.assertIn("Предыдущий отчёт", self.run_menu(["д", "4"]))

    def test_menu_errors_preserve_previous(self):
        save_report(self.make_report(), self.report_path)
        previous = self.report_path.read_bytes()
        with patch.object(
            main, "scan_folder", side_effect=PermissionError("Нет доступа"),
        ):
            self.run_menu(["н", "1", str(self.folder), "4"])
        self.assertEqual(self.report_path.read_bytes(), previous)
        self.config_path.write_text("{", encoding="utf-8")
        output = self.run_menu(["н", "1", "4"])
        self.assertIn("Ошибка JSON", output)
        self.assertEqual(self.report_path.read_bytes(), previous)

    def test_menu_reloads_rules_without_scan(self):
        (self.folder / "photo.JPG").touch()
        answers = iter(["н", "1", str(self.folder), "2", "4"])

        def answer(prompt):
            value = next(answers)
            if value == "2":
                self.config_path.write_text(
                    json.dumps({"Фото": ["jpg"]}), encoding="utf-8",
                )
            return value

        output = self.run_menu(answer)
        self.assertIn("photo.JPG -> Фото/", output)
        self.assertEqual(load_report(self.report_path)["rules"], {"Фото": [".jpg"]})

    def test_write_failure_preserves_previous(self):
        save_report(self.make_report(), self.report_path)
        previous = self.report_path.read_bytes()
        with patch("storage.NamedTemporaryFile") as temporary:
            temporary_file = temporary.return_value.__enter__.return_value
            temporary_file.name = str(
                self.report_path.parent / ".failed.tmp"
            )
            temporary_file.write.side_effect = OSError("Ошибка записи")
            with self.assertRaises(OSError):
                save_report({"new": True}, self.report_path)
        self.assertEqual(self.report_path.read_bytes(), previous)

    def test_invalid_previous_report(self):
        self.report_path.parent.mkdir()
        for text in ["{", "[]", "{}"]:
            self.report_path.write_text(text, encoding="utf-8")
            output = self.run_menu(["д", "4"])
            self.assertIn("Не удалось прочитать предыдущий отчёт", output)


if __name__ == "__main__":
    unittest.main()
