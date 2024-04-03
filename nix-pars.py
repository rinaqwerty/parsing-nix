from bs4 import BeautifulSoup
import requests
import csv
from datetime import date

# ссылка на страницу
url_laptops = 'https://www.nix.ru/price/price_list.html?section=notebooks_all#c_id=256&fn=256&g_id=10&new_goods=0&page=all&sort=%2Bp8116%2B8120%2B8119%2B330%2B90&spoiler=&store=msk-0_1721_1&thumbnail_view=2'
url_printers = 'https://www.nix.ru/price/price_list.html?section=printers_mfu_all#c_id=104&fn=104&g_id=38&new_goods=0&page=all&sort=%2Bp1766%2B8102&spoiler=1&store=msk-0_1721_1&thumbnail_view=2'
headers = {
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
}

def req(url):
    req = requests.get(url, headers=headers)
    src = req.text
    soup = BeautifulSoup(src, 'lxml')
    return src, soup

# удаление переносов строки
def dels(text):
    return ''.join(text.split('\n'))

# шапка таблицы
def table_header(filename):
    spisok = ['Наименование', 'Ссылка', 'Цена от', 'Цена до', 'Средняя цена']
    with open(filename + '.csv', 'w', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';', lineterminator='\n')
        writer.writerow(spisok)

# запись данных в таблицу csv
def record_csv(filename, name, link, price_from, price_to, average_price):
    with open(filename + '.csv', 'a', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';', lineterminator='\n')
        writer.writerow(
            (
                name,
                link,
                price_from,
                price_to,
                average_price
            )
        )

# возврат среднего значения цены
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

def create_table(url):
    src, soup = req(url)
    filename = dels(soup.find(id='price-list-title').text) + ' ' + str(date.today())
    table_header(filename)
    items = soup.find_all(class_='search-result-row highlight')
    for item in items:
        link = 'https://www.nix.ru/' + item.find(class_='t').get('href')
        name = item.find(class_='t').text
        price = item.find_all(class_='d tar cell-half-price')
        price_from, price_to = dels(price[0].text), dels(price[1].text)
        average_price = average(price_from, price_to)
        record_csv(filename, name, link, price_from, price_to, average_price)
    print(f'Создан файл "{filename}.csv"')

create_table(url_laptops)
create_table(url_printers)
