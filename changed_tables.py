from bs4 import BeautifulSoup
import requests
from datetime import date
import pymysql
from config import host, user, password, db_name

# ссылка на страницу
url_laptops = 'https://www.nix.ru/price/price_list.html?section=notebooks_all?page=all'
url_printers = 'https://www.nix.ru/price/price_list.html?section=printers_mfu_all#page=all'

headers = {
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
}
date_now = str(date.today())

def req(url):
    req = requests.get(url, headers=headers)
    src = req.text
    soup = BeautifulSoup(src, 'lxml')
    return soup

# удаление переносов строки
def dels(text):
    return ''.join(text.split('\n'))

# возврат среднего значения цены (строка)
def average(x, y):
    if y == '':
        y = x
    x = int(''.join(x.split()))
    y = int(''.join(y.split()))
    s_rev = str((x + y) // 2)[::-1]
    res = []
    for i in range(len(s_rev) // 3 + 1):
        res.append(s_rev[:3])
        s_rev = s_rev[3:]
    res = ' '.join([i for i in res if i != ''])
    return res[::-1]

# имя файла
def info_name(url):
    soup = req(url)
    filename = (dels(soup.find(id='price-list-title').text)).replace(' ', '_').replace('-', '_')
    filename = filename.lower() + '_nix'
    return filename

# заполнение таблицы
def insert_sql(connection, filename, url, names, data):
    with connection.cursor() as cursor:
        soup = req(url)
        items = soup.find_all(class_='search-result-row highlight')
        print(len(items))
        for item in items:
            link = str('https://www.nix.ru/' + item.find(class_='t').get('href'))
            name = item.find(class_='t').text
            price = item.find_all(class_='d tar cell-half-price')
            price_from, price_to = dels(price[0].text), dels(price[1].text)
            average_price = average(price_from, price_to)
            if name not in names:
                query = f"INSERT INTO `{filename}` (name, link, from_price, to_price, average_price, date) VALUES ('{name}', '{link}', '{price_from}', '{price_to}', '{average_price}', '{date_now}');"
                cursor.execute(query)
            elif name in names:
                el = data[names.index(name)]
                id = el[0]
                if average_price != el[5]:
                    # изменения цен в таблице
                    update_table(connection, filename, 'from_price', price_from, id)
                    update_table(connection, filename, 'to_price', price_to, id)
                    update_table(connection, filename, 'average_price', average_price, id)
                    update_table(connection, filename, 'date', date_now, id)

                    # добавление записи о изменениях в таблицу изменений
                    insert_changes(connection, el, price_from, price_to, average_price)
                    print('добавлены изменения')

# удаление таблицы
def delete_table(connection, filename):
    with connection.cursor() as cursor:
        query = f'DROP TABLE {filename};'
        cursor.execute(query)

# проверка существования таблицы
def check_exist(connection, filename):
    with connection.cursor() as cursor:
        query = 'SHOW TABLES;'
        cursor.execute(query)
        tables = cursor.fetchall()
        key = f'Tables_in_{db_name}'
        for table in tables:
            if key in table:
                if table[key].lower() == filename.lower():
                    return 1
        return 0

# обновление таблицы
def update_table(connection, filename, param, value, id):
    with connection.cursor() as cursor:
        query = f"UPDATE `{filename}` SET `{param}` = '{value}' WHERE (`id` = '{id}');"
        cursor.execute(query)

# добавление изменения в таблицу изменений
def insert_changes(connection, data, new_price_from, new_price_to, new_average_price):
    filename = 'изменения_в_цене_nix'
    name = data[1]
    link = data[2]
    old_price_from = data[3]
    old_price_to = data[4]
    old_average_price = data[5]
    with connection.cursor() as cursor:
        query_1 = f"INSERT INTO `{filename}` (name, link, old_from_price, old_to_price, old_average_price, new_from_price, new_to_price, new_average_price, date) "
        query_2 = f"VALUES ('{name}', '{link}', '{old_price_from}', '{old_price_to}', '{old_average_price}', '{new_price_from}', '{new_price_to}', '{new_average_price}', '{date_now}');"
        query = query_1 + query_2
        cursor.execute(query)

# существующие значения в таблице
def data_table(connection, filename):
    with connection.cursor() as cursor:
        data = []
        names = []
        select = f'SELECT * FROM {filename};'
        cursor.execute(select)
        rows = cursor.fetchall()
        for row in rows:
            dat = []
            dat.append(row['id'])
            dat.append(row['name'])
            dat.append(row['link'])
            dat.append(row['from_price'])
            dat.append(row['to_price'])
            dat.append(row['average_price'])
            data.append(dat)
            names.append(row['name'])
        return data, names

# создание таблицы изменений
def create_table_of_changes(connection):
    filename = 'изменения_в_цене_nix'
    table_exist = check_exist(connection, filename)
    if table_exist == 0:
        # создание таблицы
        with connection.cursor() as cursor:
            create_table_query = f'CREATE TABLE `{filename}`(id int AUTO_INCREMENT, name varchar(350), link varchar(255), old_from_price varchar(32), old_to_price varchar(32), old_average_price varchar(32), new_from_price varchar(32), new_to_price varchar(32), new_average_price varchar(32), date varchar(16), PRIMARY KEY (id));'
            cursor.execute(create_table_query)
            print(f'таблица "{filename}" создана.')
    else:
        print(f'таблица "{filename}" уже существует.')

def main_create(url):
    filename = info_name(url)
    try:
        connection = pymysql.connect(
            host=host,
            port=3306,
            user=user,
            password=password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f'Подключение к базе данных успешно.')
        try:
            # проверка на существование таблицы
            table_exist = check_exist(connection, filename)
            if table_exist == 0:
                # создание таблицы
                with connection.cursor() as cursor:
                    create_table_query = f'CREATE TABLE `{filename}`(id int AUTO_INCREMENT, name varchar(350), link varchar(255), from_price varchar(32), to_price varchar(32), average_price varchar(32), date varchar(16), PRIMARY KEY (id));'
                    cursor.execute(create_table_query)
                    print(f'таблица "{filename}" создана.')
            else:
                print(f'таблица "{filename}" уже существует.')

            # сбор данных из таблицы
            data, names = data_table(connection, filename)
            # создание таблицы изменений
            create_table_of_changes(connection)
            # заполнение существующих таблиц
            insert_sql(connection, filename, url, names, data)
            connection.commit()
            print('данные записаны')

        finally:
            connection.close()

    except Exception as ex:
        print('ОШИБКА')
        print(ex)

main_create(url_laptops)
main_create(url_printers)
