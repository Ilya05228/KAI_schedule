"""точка входа"""

from pathlib import Path

from datetime import datetime
from zoneinfo import ZoneInfo
from kai_schedule.parser import ICSScheduleItem, JSONScheduleParser, create_ics_calendar
def main()->None:

    path = Path("./local_files/r.json")
    with path.open(encoding="utf-8") as f:
        json_content = f.read()

    # Ввод начальной и конечной даты семестра
    start_date_str = input("Начало семестра (ДД.ММ.ГГГГ, Enter=02.02.2026): ") or "02.02.2026"
    end_date_str = input("Конец семестра (ДД.ММ.ГГГГ, Enter=31.05.2026): ") or "31.05.2026"
    
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y").replace(tzinfo=ZoneInfo("Europe/Moscow"))
    end_date = datetime.strptime(end_date_str, "%d.%m.%Y").replace(tzinfo=ZoneInfo("Europe/Moscow"))
    
    print(f"Генерация с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}")
    
    parser = JSONScheduleParser(json_content, start_date=start_date, end_date=end_date)
    items = parser.parse()

    # Преобразуем каждый элемент в VEVENT
    events = [str(ICSScheduleItem(schedule_item=item).to_ics()) for item in items]

    # Собираем календарь через функцию
    ics_content = create_ics_calendar(events)

    ics_path = Path("./local_files/schedule.ics")
    with ics_path.open("w", encoding="utf-8") as ics_file:
        ics_file.write(ics_content)

    print(f"Файл ICS успешно сохранён: {ics_path}")
    print(f"События сгенерированы с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}!")
if __name__ == "__main__":
    main()