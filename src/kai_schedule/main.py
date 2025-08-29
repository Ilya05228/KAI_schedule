"""точка входа"""

from pathlib import Path

from kai_schedule.parser import ICSScheduleItem, JSONScheduleParser, create_ics_calendar

if __name__ == "__main__":
    path = Path("./local_files/r.json")
    with path.open(encoding="utf-8") as f:
        json_content = f.read()

    parser = JSONScheduleParser(json_content)
    items = parser.parse()

    # Преобразуем каждый элемент в VEVENT
    events = [str(ICSScheduleItem(schedule_item=item).to_ics()) for item in items]

    # Собираем календарь через функцию
    ics_content = create_ics_calendar(events)

    ics_path = Path("./local_files/schedule.ics")
    with ics_path.open("w", encoding="utf-8") as ics_file:
        ics_file.write(ics_content)

    print(f"Файл ICS успешно сохранён: {ics_path}")
