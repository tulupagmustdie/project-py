from scanner import scan_folder, validate_folder
from report import print_files


def main():
    folder_text = input("Введите путь к папке: ").strip()

    try:
        folder = validate_folder(folder_text)
        files = scan_folder(folder)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Не удалось просканировать папку: {error}")
        return

    print(f"\nПапка: {folder}")
    print_files(files)


if __name__ == "__main__":
    main()
