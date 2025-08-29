import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import sys

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_chrome_version():
    """Проверяет версию установленного Chrome.

    Возвращает:
        str: Версия Chrome или None, если Chrome не установлен.
    """
    try:
        result = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        logger.info(f"Версия Chrome: {version}")
        return version
    except FileNotFoundError:
        logger.error("Google Chrome не установлен. Установите его с помощью 'sudo apt-get install google-chrome-stable'.")
        return None
    except Exception as e:
        logger.error(f"Ошибка при проверке версии Chrome: {e}")
        return None


def setup_driver(headless=True):
    """
    Настраивает веб-драйвер Chrome.
    Аргументы:
        headless (bool): Запускать ли в фоновом режиме.
    Возвращает:
        webdriver: Объект драйвера Chrome или None в случае ошибки.
    """
    try:
        chrome_version = check_chrome_version()
        if not chrome_version:
            return None

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_window_size(1920, 1080)
        logger.info("Веб-драйвер успешно настроен.")
        return driver
    except Exception as e:
        logger.error(f"Ошибка при настройке веб-драйвера: {e}")
        return None


def get_schedule(group_number):
    """
    Получает расписание для указанной группы.
    Аргументы:
        group_number (str): Номер группы, например, "4301".
    Возвращает:
        list: Список словарей с данными расписания или None в случае ошибки.
    """
    driver = setup_driver(headless=True)  # Для отладки
    if not driver:
        return None

    try:
        # Шаг 1: Открываем страницу
        url = "https://kai.ru/web/studentu/raspisanie1"
        driver.get(url)
        logger.info(f"Открыта страница: {url}")

        # Шаг 2: Закрываем возможные модальные окна (например, cookies)
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button.accept-cookies, button[id*='cookie'], button[class*='cookie']",
                    )
                )
            )
            cookie_button.click()
            logger.info("Модальное окно (cookies) закрыто.")
        except:
            logger.info("Модальное окно не найдено, продолжаем.")

        # Шаг 3: Находим поле ввода
        input_field = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "_pubStudentSchedule_WAR_publicStudentSchedule10_group")))
        logger.info("Поле ввода найдено.")

        # Шаг 4: Вводим номер группы посимвольно
        input_field.clear()
        for char in group_number:
            input_field.send_keys(char)
            # time.sleep(0.5)  # Задержка для активации автодополнения
        logger.info(f"Введен номер группы: {group_number}")

        # Шаг 5: Ждем появления выпадающего списка
        dropdown_list = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "ul.yui3-aclist-list")))
        logger.info("Выпадающий список найден.")

        # Шаг 6: Выбираем группу
        dropdown_option = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, f"//li[@data-text='{group_number}']")))
        dropdown_option.click()
        logger.info(f"Выбрана группа: {group_number}")

        # # Шаг 7: Нажимаем кнопку для загрузки расписания
        # submit_button = WebDriverWait(driver, 20).until(
        #     EC.element_to_be_clickable(
        #         (
        #             By.CSS_SELECTOR,
        #             "button.btn, button[type='submit'], input[type='submit']",
        #         )
        #     )
        # )
        driver.find_element(By.ID, "_pubStudentSchedule_WAR_publicStudentSchedule10_schedule").click()
        html_content = driver.page_source
        print(html_content)
        with open("schedule.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        input()
        logger.info("Нажата кнопка для загрузки расписания.")

        # # Шаг 8: Ждем загрузки таблицы расписания
        # WebDriverWait(driver, 20).until(
        #     EC.presence_of_element_located(
        #         (By.CSS_SELECTOR, "table, div.table-responsive")
        #     )
        # )
        # logger.info("Таблица расписания найдена.")

        # # Шаг 9: Парсим HTML страницы
        # soup = BeautifulSoup(driver.page_source, "html.parser")
        # schedule_table = soup.find("table") or soup.find(
        #     "div", class_="table-responsive"
        # )
        # if not schedule_table:
        #     logger.warning("Таблица расписания не найдена в HTML.")
        #     driver.save_screenshot("error_screenshot.png")
        #     logger.info("Скриншот страницы сохранен как error_screenshot.png")
        #     return None

        # # Извлекаем данные из таблицы
        # schedule_data = []
        # rows = schedule_table.find_all("tr")[1:]  # Пропускаем заголовок
        # for row in rows:
        #     cols = row.find_all("td")
        #     if len(cols) >= 7:
        #         schedule_data.append(
        #             {
        #                 "day": cols[0].text.strip(),
        #                 "time": cols[1].text.strip(),
        #                 "date": cols[2].text.strip(),
        #                 "discipline": cols[3].text.strip(),
        #                 "type": cols[4].text.strip(),
        #                 "room": cols[5].text.strip(),
        #                 "building": cols[6].text.strip(),
        #                 "teacher": cols[7].text.strip(),
        #                 "department": cols[8].text.strip() if len(cols) > 8 else "",
        #             }
        #         )

        # logger.info(
        #     f"Расписание для группы {group_number} успешно получено. Найдено {len(schedule_data)} записей."
        # )
        # return schedule_data

    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        driver.save_screenshot("error_screenshot.png")
        logger.info("Скриншот страницы сохранен как error_screenshot.png")
        return None
    finally:
        driver.quit()
        logger.info("Веб-драйвер закрыт.")


def save_to_csv(schedule, filename="schedule.csv"):
    """
    Сохраняет расписание в CSV-файл.
    """
    if not schedule:
        logger.warning("Нет данных для сохранения в CSV.")
        return

    import csv

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=schedule[0].keys())
        writer.writeheader()
        writer.writerows(schedule)
    logger.info(f"Расписание сохранено в файл: {filename}")


def main():
    """
    Основная функция для выполнения парсинга.
    """
    group_number = "4301"

    schedule = get_schedule(group_number)
    if not schedule:
        logger.error("Не удалось получить расписание.")
        sys.exit(1)

    for entry in schedule:
        print(
            f"День: {entry['day']}, Время: {entry['time']}, Дата: {entry['date']}, "
            f"Дисциплина: {entry['discipline']}, Вид: {entry['type']}, "
            f"Аудитория: {entry['room']}, Здание: {entry['building']}, "
            f"Преподаватель: {entry['teacher']}, Кафедра: {entry['department']}"
        )

    save_to_csv(schedule)


if __name__ == "__main__":
    main()
