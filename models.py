"""Модели данных, используемые в игре с ОКВЭД."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorInfo:
    """Описание ошибки."""

    code: str
    message: str


@dataclass(frozen=True)
class OkvedItem:
    """Запись ОКВЭД."""

    code: str
    name: str


@dataclass(frozen=True)
class MatchResult:
    """Результат сопоставления номера и ОКВЭД."""

    normalized_phone: str
    okved_code: str
    okved_name: str
    match_length: int
    fallback_used: bool


@dataclass(frozen=True)
class GameResult:
    """Результат выполнения игры."""

    error: ErrorInfo | None
    match: MatchResult | None


class OkvedLoadError(Exception):
    """Ошибка при загрузке данных ОКВЭД из удалённого источника."""
