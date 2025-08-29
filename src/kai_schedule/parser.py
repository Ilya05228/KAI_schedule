"""Парсер JSON расписания для создания ICS-файла."""

import json
import logging
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import icalendar

from kai_schedule.schedule_item import (
    DefaultScheduleItemFormatter,
    EndByDate,
    ScheduleItem,
    ScheduleItemFormatter,
    Weekday,
    WeeklyRepeatRule,
)

logger = logging.getLogger(__name__)


class JSONScheduleParser:
    """Парсер JSON-данных расписания для создания массива ScheduleItem."""

    def __init__(self, json_content: str, start_year: int = 2025):
        self.data = json.loads(json_content)
        self.start_year = start_year
        self.semester_start = datetime(start_year, 9, 1, tzinfo=ZoneInfo("Europe/Moscow"))
        self.semester_end = datetime(start_year, 12, 31, tzinfo=ZoneInfo("Europe/Moscow"))
        self.weekday_map = {
            "1": Weekday.MONDAY,
            "2": Weekday.TUESDAY,
            "3": Weekday.WEDNESDAY,
            "4": Weekday.THURSDAY,
            "5": Weekday.FRIDAY,
            "6": Weekday.SATURDAY,
            "7": Weekday.SUNDAY,
        }

    def _is_even_week(self, date: datetime) -> bool:
        """Проверяет, является ли неделя для данной даты четной."""
        week_num = date.isocalendar()[1]
        return week_num % 2 == 0

    def _parse_time(self, time_str: str) -> time:
        """Парсит время из строки формата 'ЧЧ:ММ'."""
        try:
            dt = datetime.strptime(time_str.strip(), "%H:%M")
            return dt.time()
        except ValueError as e:
            logger.critical(f"Ошибка в парсинге времени: {time_str}")
            raise e

    def _parse_dates(self, date_str: str) -> list[datetime]:
        """Парсит поле 'dayDate' и возвращает список дат."""
        date_str = date_str.strip()
        if not date_str:
            return []

        parsed_dates: list[datetime] = []
        dates = date_str.split()
        for d in dates:
            d = d.strip()
            if not d:
                continue
            try:
                parsed_date = datetime.strptime(f"{d}.{self.start_year}", "%d.%m.%Y").replace(tzinfo=ZoneInfo("Europe/Moscow"))
                parsed_dates.append(parsed_date)
            except ValueError as e:
                logger.critical(f"Ошибка в парсинге даты: {d}")
                raise e
        return parsed_dates

    def _get_first_occurrence(self, target_weekday: Weekday, start_date: datetime, is_even: bool) -> datetime:
        """Находит первую дату для заданного дня недели, учитывая четность."""
        current_date = start_date
        while current_date.weekday() != target_weekday:
            current_date += timedelta(days=1)
        if is_even != self._is_even_week(current_date):
            current_date += timedelta(days=7)
        return current_date

    def parse(self) -> list[ScheduleItem]:
        """Парсит JSON и возвращает список ScheduleItem."""
        schedule_items = []
        for day_num, events in self.data.items():
            if day_num not in self.weekday_map:
                logger.warning(f"Неизвестный день недели: {day_num}")
                continue
            target_weekday = self.weekday_map[day_num]
            logger.info(f"Парсинг дня недели: {day_num} ({target_weekday})")

            for event in events:
                subject = event.get("disciplName", "").strip()
                lesson_type = event.get("disciplType", "").strip()
                audience = event.get("audNum", "").strip()
                building = event.get("buildNum", "").strip()
                teacher = event.get("prepodName", "").strip()
                department = event.get("orgUnitName", "").strip()
                time_str = event.get("dayTime", "").strip()
                date_str = event.get("dayDate", "").strip()

                if not all([subject, lesson_type, audience, building, teacher, department, time_str]):
                    logger.warning(f"Пропущено событие из-за отсутствия данных: {event}")
                    continue

                start_time = self._parse_time(time_str)
                duration = timedelta(minutes=90)  # Предполагаемая длительность занятия 1.5 часа

                # Обработка дат и повторений
                if date_str in ["чет", "неч"]:
                    is_even = date_str == "чет"
                    start_date = self._get_first_occurrence(target_weekday, self.semester_start, is_even)
                    start_datetime = datetime.combine(start_date, start_time).replace(tzinfo=ZoneInfo("Europe/Moscow"))
                    end_datetime = start_datetime + duration
                    repeat_rule = WeeklyRepeatRule(
                        weekdays=[target_weekday],
                        interval=2,
                        end=EndByDate(self.semester_end),
                    )
                    item = ScheduleItem(
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        subject=subject,
                        lesson_type=lesson_type,
                        audience=audience,
                        building=building,
                        teacher=teacher,
                        department=department,
                        repeat_rule=repeat_rule,
                    )
                    schedule_items.append(item)
                elif date_str:
                    dates = self._parse_dates(date_str)
                    for d in dates:
                        start_datetime = datetime.combine(d, start_time).replace(tzinfo=ZoneInfo("Europe/Moscow"))
                        end_datetime = start_datetime + duration
                        item = ScheduleItem(
                            start_datetime=start_datetime,
                            end_datetime=end_datetime,
                            subject=subject,
                            lesson_type=lesson_type,
                            audience=audience,
                            building=building,
                            teacher=teacher,
                            department=department,
                            repeat_rule=None,
                        )
                        schedule_items.append(item)
                else:
                    start_date = self._get_first_occurrence(target_weekday, self.semester_start, self._is_even_week(self.semester_start))
                    start_datetime = datetime.combine(start_date, start_time).replace(tzinfo=ZoneInfo("Europe/Moscow"))
                    end_datetime = start_datetime + duration
                    repeat_rule = WeeklyRepeatRule(
                        weekdays=[target_weekday],
                        interval=1,
                        end=EndByDate(self.semester_end),
                    )
                    item = ScheduleItem(
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        subject=subject,
                        lesson_type=lesson_type,
                        audience=audience,
                        building=building,
                        teacher=teacher,
                        department=department,
                        repeat_rule=repeat_rule,
                    )
                    schedule_items.append(item)

        return schedule_items


def create_ics_calendar(events: Sequence[str]) -> str:
    """Принимает массив строк-мероприятий VEVENT и возвращает готовый ICS-календарь."""
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//KAI Schedule Parser//EN"]
    lines.extend(events)
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


class ICSScheduleItem:
    """Преобразование ScheduleItem в ICS-формат."""

    def __init__(self, schedule_item: ScheduleItem, formatter: ScheduleItemFormatter | None = None):
        self.schedule_item = schedule_item
        self.formatter = formatter or DefaultScheduleItemFormatter()

    def to_ics(self) -> str:
        """Возвращает только VEVENT, без VCALENDAR."""
        event = icalendar.Event()
        event.add("summary", self.formatter.format_header(self.schedule_item))
        event.add("dtstart", self.schedule_item.start_datetime)
        event.add("dtend", self.schedule_item.end_datetime)
        event.add("location", f"{self.schedule_item.building}, {self.schedule_item.audience}")
        event.add("description", self.formatter.format_description(self.schedule_item))
        if self.schedule_item.repeat_rule:
            event.add("rrule", self.schedule_item.repeat_rule.to_rrule_str())
        return event.to_ical().decode("utf-8")  # только VEVENT
