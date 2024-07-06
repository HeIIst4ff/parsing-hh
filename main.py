import requests
import psycopg2
from psycopg2 import sql


def sanitize_string(value):
    if value:
        return value.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    return value


def get_vacancies(keyword):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": 1,
        "per_page": 100,
    }
    headers = {
        "User-Agent": "Your User Agent",
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        vacancies = data.get("items", [])
        save_vacancies_to_db(vacancies)
    else:
        print(f"Request failed with status code: {response.status_code}")


def save_vacancies_to_db(vacancies):
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="db",
            port="5432",
            client_encoding="UTF8"
        )
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id SERIAL PRIMARY KEY,
                title TEXT,
                company TEXT,
                salary TEXT,
                url TEXT
            )
        """)

        for vacancy in vacancies:
            vacancy_title = sanitize_string(vacancy.get("name"))
            vacancy_url = sanitize_string(vacancy.get("alternate_url"))
            company_name = sanitize_string(vacancy.get("employer", {}).get("name"))
            salary = vacancy.get("salary", {})

            if salary:
                salary_from = salary.get("from", None)
                salary_to = salary.get("to", None)
                salary_currency = salary.get("currency", None)

                if salary_from and salary_to:
                    salary_range = f"{salary_from} - {salary_to} {salary_currency}"
                elif salary_from:
                    salary_range = f"от {salary_from} {salary_currency}"
                else:
                    salary_range = "Зарплата не указана"
            else:
                salary_range = "Зарплата не указана"

            cursor.execute(
                sql.SQL("INSERT INTO vacancies (title, company, salary, url) VALUES (%s, %s, %s, %s)"),
                [vacancy_title, company_name, salary_range, vacancy_url]
            )

        conn.commit()
        cursor.close()
        conn.close()

        print("Вакансии успешно сохранены в базу данных")
    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")


get_vacancies("")
