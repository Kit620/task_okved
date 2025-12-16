"""Точка входа в игру «Найди свой ОКВЭД по номеру телефона».

Скрипт инициализирует компоненты игры и запускает интерфейс
командной строки.
"""

from game import OkvedPhoneGame, OkvedRepository, PhoneNormalizer


def main() -> None:
    """Главная функция игры."""
    okved_url = "https://raw.githubusercontent.com/bergstar/testcase/master/okved.json"

    print("Игра «Найди свой ОКВЭД по номеру телефона»")
    print("Загрузка данных ОКВЭД...")

    try:
        normalizer = PhoneNormalizer()
        repository = OkvedRepository(okved_url)
        repository.get_all()
        game = OkvedPhoneGame(normalizer=normalizer, repository=repository)
        print("Данные загружены успешно!\n")
    except Exception as exc:
        print(f"\nОшибка инициализации игры: {exc}")
        print("Проверьте подключение к интернету и повторите попытку.")
        return

    print("Введите российский мобильный номер в любом формате.")
    print("(Для выхода нажмите Ctrl+C)\n")

    try:
        raw_phone = input("Номер телефона: ")
    except KeyboardInterrupt:
        print("\n\nДо свидания!")
        return
    except EOFError:
        print("\n\n Некорректный ввод")
        return

    result = game.play(raw_phone)

    if result.error is not None:
        print("\nОшибка нормализации номера:")
        print(f"- код: {result.error.code}")
        print(f"- сообщение: {result.error.message}")
        return

    assert result.match is not None

    print("\nРезультат:")
    print(f"- нормализованый номер: {result.match.normalized_phone}")
    print(
        f"- ОКВЭД: {result.match.okved_code} - {result.match.okved_name}",
    )
    print(f"- длина совпадения по окончанию: {result.match.match_length}")
    print(f"- резервная стратегия: {result.match.fallback_used}")


if __name__ == "__main__":
    main()
