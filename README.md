# Найди свой ОКВЭД по номеру телефона

Игра: вводишь номер телефона, программа подбирает код ОКВЭД с максимальным совпадением по окончанию номера.

## Установка и запуск

```bash
pip install -r requirements.txt

python main.py
```

Введи номер телефона в любом формате (например: `89123456789`, `+79123456789`, `8 (912) 345-67-89`).

## Структура проекта

- `models.py` - модели данных (ErrorInfo, OkvedItem, MatchResult, GameResult)
- `game.py` - основная логика:
  - `PhoneNormalizer` - нормализация номера к формату `+79XXXXXXXXX`
  - `OkvedRepository` - загрузка `okved.json` по HTTPS
  - `OkvedMatcher` - поиск ОКВЭД по совпадению окончания
  - `OkvedPhoneGame` - основной класс игры
- `main.py` - точка входа

## Данные ОКВЭД

Файл `okved.json` загружается по HTTPS из GitHub. URL можно изменить в `main.py`.

## Используемые библиотеки

- `requests` - https://github.com/psf/requests (Apache License 2.0)

## Стандарты кода

- PEP 8 (стиль кода)
- PEP 257 (документация в docstrings)
