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
