"""Бизнес-логика игры «Найди свой ОКВЭД по номеру телефона».

Содержит классы для нормализации телефона, загрузки ОКВЭД, сопоставления,
основной фасад игры, объединяющий все компоненты.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

import requests

from models import ErrorInfo, GameResult, MatchResult, OkvedItem, OkvedLoadError


@dataclass(frozen=True)
class NormalizationResult:
    """Результат нормализации номера телефона."""

    phone: str | None
    error: ErrorInfo | None


class PhoneNormalizer:
    """Нормализует номер телефона к формату +79XXXXXXXXX."""

    def normalize(self, raw: str) -> NormalizationResult:
        """Нормализует строку с номером или возвращает ошибку."""
        cleaned = self._clean(raw)
        if cleaned.startswith("+"):
            plus = "+"
            digits = cleaned[1:]
        else:
            plus = ""
            digits = cleaned

        if not digits:
            return NormalizationResult(
                phone=None,
                error=ErrorInfo(
                    code="NO_DIGITS",
                    message="В введённой строке не найдено цифр телефона.",
                ),
            )

        normalized = self._normalize_digits(plus, digits)
        if normalized is None:
            return NormalizationResult(
                phone=None,
                error=ErrorInfo(
                    code="UNSUPPORTED_FORMAT",
                    message="Формат номера не распознан как российский мобильный.",
                ),
            )

        if not self._is_valid_final(normalized):
            return NormalizationResult(
                phone=None,
                error=ErrorInfo(
                    code="INVALID_NORMALIZED",
                    message="Номер не удалось привести к формату +79XXXXXXXXX.",
                ),
            )

        return NormalizationResult(phone=normalized, error=None)

    def _clean(self, raw: str) -> str:
        """Извлекает цифры и плюс из строки."""
        raw = raw.strip()
        has_plus = raw.startswith("+")
        digits_only = "".join(ch for ch in raw if ch.isdigit())
        return ("+" if has_plus else "") + digits_only

    def _normalize_digits(self, plus: str, digits: str) -> str | None:
        """Приводит цифры к формату +7XXXXXXXXXXX."""
        length = len(digits)

        if plus == "+" and digits.startswith("7") and length == 11:
            return "+" + digits
        if plus == "" and digits.startswith("8") and length == 11:
            return "+7" + digits[1:]
        if plus == "" and digits.startswith("7") and length == 11:
            return "+" + digits
        if plus == "" and digits.startswith("9") and length == 10:
            return "+7" + digits

        return None

    def _is_valid_final(self, phone: str) -> bool:
        """Проверяет формат +79XXXXXXXXX."""
        return (
            phone.startswith("+79")
            and len(phone) == 12
            and phone[1:].isdigit()
        )


class OkvedRepository:
    """Загружает и кэширует записи ОКВЭД из JSON по URL."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._cache: list[OkvedItem] | None = None

    def get_all(self) -> list[OkvedItem]:
        """Возвращает все записи ОКВЭД."""
        if self._cache is None:
            self._cache = self._load()
        return self._cache

    def _load(self) -> list[OkvedItem]:
        """Загружает записи ОКВЭД из JSON."""
        data_text = self._fetch_json_text()
        data = self._parse_json(data_text)
        items = self._extract_okved_items(data)
        return items

    def _fetch_json_text(self) -> str:
        """Загружает JSON-файл по HTTP и возвращает текст."""
        try:
            response = requests.get(
                self._url,
                timeout=5,
                verify=True,
                stream=True,
            )
            response.raise_for_status()

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > 10 * 1024 * 1024:
                raise OkvedLoadError("Файл okved.json слишком большой (>10 МБ)")

            return response.text
        except requests.RequestException as exc:
            raise OkvedLoadError(f"Не удалось загрузить okved.json: {exc}") from exc

    def _parse_json(self, data_text: str) -> list:
        """Парсит JSON-текст и проверяет, что это массив."""
        try:
            data = json.loads(data_text)
        except json.JSONDecodeError as exc:
            raise OkvedLoadError("Некорректный JSON в okved.json") from exc

        if not isinstance(data, list):
            raise OkvedLoadError("okved.json должен содержать массив объектов")

        return data

    def _extract_okved_items(self, data: list) -> list[OkvedItem]:
        """Извлекает корректные записи ОКВЭД из массива данных."""
        items: list[OkvedItem] = []

        for entry in data:
            if not isinstance(entry, dict):
                continue

            code = str(entry.get("code", "")).strip()
            name = str(entry.get("name", "")).strip()
            if code and name:
                items.append(OkvedItem(code=code, name=name))

        if not items:
            raise OkvedLoadError("Не найдено ни одной корректной записи ОКВЭД")

        return items


@dataclass
class _Candidate:
    item: OkvedItem
    match_length: int
    full_match: bool


class OkvedMatcher:
    """Находит лучший ОКВЭД для номера телефона."""

    def __init__(self, items: Iterable[OkvedItem]) -> None:
        self._items: list[OkvedItem] = list(items)

        if not self._items:
            raise ValueError("Список ОКВЭД не может быть пустым")

        for idx, item in enumerate(self._items):
            if not isinstance(item, OkvedItem):
                raise TypeError(
                    f"Элемент #{idx} не является OkvedItem: {type(item).__name__}",
                )

    def match(self, normalized_phone: str) -> MatchResult:
        """Находит лучший код ОКВЭД для номера."""
        digits = normalized_phone.lstrip("+")
        candidates = self._collect_candidates(digits)
        if candidates:
            best = self._choose_best(candidates)
            return MatchResult(
                normalized_phone=normalized_phone,
                okved_code=best.item.code,
                okved_name=best.item.name,
                match_length=best.match_length,
                fallback_used=not bool(best.match_length),
            )

        phone_hash = hash(digits) % len(self._items)
        fallback_item = self._items[phone_hash]
        return MatchResult(
            normalized_phone=normalized_phone,
            okved_code=fallback_item.code,
            okved_name=fallback_item.name,
            match_length=0,
            fallback_used=True,
        )

    def _collect_candidates(self, phone_digits: str) -> list[_Candidate]:
        """Собирает кандидатов на совпадение."""
        candidates: list[_Candidate] = []
        for item in self._items:
            code_digits = self._normalize_code(item.code)
            if not code_digits:
                continue

            match_length = self._suffix_length(phone_digits, code_digits)
            if match_length <= 0:
                continue

            full_match = match_length == len(code_digits)
            candidates.append(
                _Candidate(
                    item=item,
                    match_length=match_length,
                    full_match=full_match,
                ),
            )
        return candidates

    @staticmethod
    def _normalize_code(code: str) -> str:
        """Оставляет только цифры из кода ОКВЭД."""
        return "".join(ch for ch in code if ch.isdigit())

    @staticmethod
    def _suffix_length(phone_digits: str, code_digits: str) -> int:
        """Возвращает длину общего суффикса номера и кода ОКВЭД."""
        i = 1
        max_len = min(len(phone_digits), len(code_digits))
        while i <= max_len and phone_digits[-i] == code_digits[-i]:
            i += 1
        return i - 1

    @staticmethod
    def _choose_best(candidates: list[_Candidate]) -> _Candidate:
        """Выбирает кандидата с максимальной длиной совпадения."""
        return max(candidates, key=lambda c: (c.match_length, c.full_match))


class OkvedPhoneGame:
    """Основная точка входа в игру."""

    def __init__(
        self,
        normalizer: PhoneNormalizer,
        repository: OkvedRepository,
    ) -> None:
        self._normalizer = normalizer
        self._repository = repository

    def play(self, raw_phone: str) -> GameResult:
        """Обрабатывает номер телефона и возвращает результат."""
        norm_result = self._normalizer.normalize(raw_phone)
        if norm_result.error is not None or norm_result.phone is None:
            return GameResult(error=norm_result.error, match=None)

        normalized_phone = norm_result.phone

        try:
            okved_items = self._repository.get_all()
        except OkvedLoadError as exc:
            return GameResult(
                error=ErrorInfo(
                    code="OKVED_LOAD_ERROR",
                    message=str(exc),
                ),
                match=None,
            )

        if not okved_items:
            return GameResult(
                error=ErrorInfo(
                    code="OKVED_EMPTY",
                    message="Список ОКВЭД пуст - игра не может быть выполнена.",
                ),
                match=None,
            )

        matcher = OkvedMatcher(okved_items)
        match = matcher.match(normalized_phone)

        return GameResult(error=None, match=match)
