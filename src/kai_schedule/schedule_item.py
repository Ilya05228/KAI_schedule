"""Модуль элемеента расписания."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum


class RepeatEnd(ABC):
    """Базовый класс для окончания повторения."""

    @abstractmethod
    def to_rrule_arg_str(self) -> str:
        pass


class EndByDate(RepeatEnd):
    """Повторение до определённой даты."""

    def __init__(self, until: datetime):
        self.until = until

    @property
    def until(self) -> datetime:
        return self._until

    @until.setter
    def until(self, value: datetime) -> None:
        self._until = value

    def to_rrule_arg_str(self) -> str:
        # Используем локальное время без Z (UTC)
        return f"UNTIL={self.until.strftime('%Y%m%dT%H%M%S')}"


class EndByCount(RepeatEnd):
    """Повторение определённое количество раз."""

    def __init__(self, count: int):
        self.count = count

    @property
    def count(self) -> int:
        return self._count

    @count.setter
    def count(self, value: int) -> None:
        if value < 1:
            raise ValueError("count должен быть >=1")
        self._count = value

    def to_rrule_arg_str(self) -> str:
        return f"COUNT={self.count}"


class Weekday(IntEnum):
    """Дни недели."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    @property
    def ical(self) -> str:
        mapping = {
            Weekday.MONDAY: "MO",
            Weekday.TUESDAY: "TU",
            Weekday.WEDNESDAY: "WE",
            Weekday.THURSDAY: "TH",
            Weekday.FRIDAY: "FR",
            Weekday.SATURDAY: "SA",
            Weekday.SUNDAY: "SU",
        }
        return mapping[self]


class BaseRepeatRule(ABC):
    """Базовый класс правил повторения с интервалом и окончанием."""

    def __init__(self, interval: int = 1, end: RepeatEnd | None = None):
        self.interval = interval
        self.end = end

    @property
    def interval(self) -> int:
        return self._interval

    @interval.setter
    def interval(self, value: int) -> None:
        if value < 1:
            raise ValueError("Интервал должен быть >=1")
        self._interval = value

    @abstractmethod
    def _to_rrule_str_args(self) -> list[str]:
        pass

    def to_rrule_str(self) -> str:
        parts: list[str] = self._to_rrule_str_args()
        parts.append(f"INTERVAL={self.interval}")
        if self.end:
            parts.append(self.end.to_rrule_arg_str())
        return f"FREQ=WEEKLY;{';'.join(parts)}"


class DailyRepeatRule(BaseRepeatRule):
    """Повторение каждый день с интервалом."""

    def _to_rrule_str_args(self) -> list[str]:
        return ["FREQ=DAILY"]


class WeeklyRepeatRule(BaseRepeatRule):
    """Повторение каждую неделю по выбранным дням."""

    def __init__(
        self,
        weekdays: list[Weekday] | None = None,
        interval: int = 1,
        end: RepeatEnd | None = None,
    ):
        super().__init__(interval, end)
        self.weekdays = weekdays or []

    def _to_rrule_str_args(self) -> list[str]:
        args = ["FREQ=WEEKLY"]
        if self.weekdays:
            args.append("BYDAY=" + ",".join(d.ical for d in self.weekdays))
        return args


class MonthlyRepeatRule(BaseRepeatRule):
    """Повтор раз в мес"""

    def __init__(
        self,
        bymonthday: int | None = None,
        interval: int = 1,
        end: RepeatEnd | None = None,
    ):
        super().__init__(interval, end)
        self.bymonthday = bymonthday

    def _to_rrule_str_args(self) -> list[str]:
        args = ["FREQ=MONTHLY"]
        if self.bymonthday:
            args.append(f"BYMONTHDAY={self.bymonthday}")
        return args


class YearlyRepeatRule(BaseRepeatRule):
    """Повторение каждый год в ту же дату."""

    def _to_rrule_str_args(self) -> list[str]:
        return ["FREQ=YEARLY"]


class ScheduleItem:
    """Класс элемента расписания.

    Args:
        start_datetime (datetime): Дата и время начала занятия.
        end_datetime (datetime): Дата и время окончания занятия.
        subject (str): Название дисциплины.
        lesson_type (str): Вид занятия (лек, л.р., сем и т.д.).
        audience (str): Аудитория.
        building (str): Здание.
        teacher (str): Преподаватель.
        department (str): Кафедра.
        repeat_rule (BaseRepeatRule | None): Правило повторения.
    """

    def __init__(
        self,
        start_datetime: datetime,
        end_datetime: datetime,
        subject: str,
        lesson_type: str,
        audience: str,
        building: str,
        teacher: str,
        department: str,
        repeat_rule: BaseRepeatRule | None = None,
    ):
        self._initialized: bool = False
        self.start_datetime: datetime = start_datetime
        self.end_datetime: datetime = end_datetime
        self.subject: str = subject
        self.lesson_type: str = lesson_type
        self.audience: str = audience
        self.building: str = building
        self.teacher: str = teacher
        self.department: str = department
        self.repeat_rule = repeat_rule
        self._initialized = True
        self._validate()

    def _validate(self) -> None:
        self._validate_dates()

    @property
    def duration(self) -> timedelta:
        return self.end_datetime - self.start_datetime

    @property
    def start_datetime(self) -> datetime:
        return self._start_datetime

    @start_datetime.setter
    def start_datetime(self, value: datetime) -> None:
        self._start_datetime = value
        self._validate_dates()

    @property
    def end_datetime(self) -> datetime:
        return self._end_datetime

    @end_datetime.setter
    def end_datetime(self, value: datetime) -> None:
        self._end_datetime = value
        self._validate_dates()

    def _validate_dates(self) -> None:
        """Валидирует, что дата начала меньше даты окончания.

        Вызывает ValueError, если проверка не проходит.
        """
        if self._initialized and self.start_datetime >= self.end_datetime:
            msg = f"Дата начала ({self.start_datetime}) должна быть меньше даты окончания ({self.end_datetime})"
            raise ValueError(msg)


@dataclass(frozen=True)
class FormatedScheduleItem:
    """Датакласс, представляющий форматированный элемент расписания."""

    header: str
    description: str


class ScheduleItemFormatter(ABC):
    """Абстрактный базовый класс для форматировщиков расписания."""

    @abstractmethod
    def format_header(self, item: "ScheduleItem") -> str:
        """Форматирование заголовка"""

    @abstractmethod
    def format_description(self, item: "ScheduleItem") -> str:
        """Форматирование описания"""

    def format(self, item: "ScheduleItem") -> FormatedScheduleItem:
        """Возвращает готовый объект FormatedScheduleItem"""
        return FormatedScheduleItem(header=self.format_header(item), description=self.format_description(item))


class DefaultScheduleItemFormatter(ScheduleItemFormatter):
    """Форматировщик по умолчанию."""

    def format_header(self, item: "ScheduleItem") -> str:
        return f"{item.building} - {item.audience} | {item.lesson_type} - {item.subject}"

    def format_description(self, item: "ScheduleItem") -> str:
        return (
            f"Дисциплина: {item.subject}\n"
            f"Вид занятия: {item.lesson_type}\n"
            f"Здание: {item.building}\n"
            f"Аудитория: {item.audience}\n"
            f"Преподаватель: {item.teacher}\n"
            f"Кафедра: {item.department}"
        )
