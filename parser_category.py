import datetime

import requests
from retry import retry

from db.db_config import session_sync
from db.models import Product


def get_catalogs_wb() -> dict:
    """получаем полный каталог Wildberries"""
    url = 'https://static-basket-01.wbbasket.ru/vol0/data/main-menu-ru-ru-v2.json'
    headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    return requests.get(url, headers=headers).json()


def get_data_category(catalogs_wb: dict) -> list:
    """сбор данных категорий из каталога Wildberries"""
    catalog_data = []
    if isinstance(catalogs_wb, dict) and 'childs' not in catalogs_wb:
        catalog_data.append({
            'name': f"{catalogs_wb['name']}",
            'shard': catalogs_wb.get('shard', None),
            'url': catalogs_wb['url'],
            'query': catalogs_wb.get('query', None)
        })
    elif isinstance(catalogs_wb, dict):
        catalog_data.extend(get_data_category(catalogs_wb['childs']))
    else:
        for child in catalogs_wb:
            catalog_data.extend(get_data_category(child))
    return catalog_data


def search_category_in_catalog(url: str, catalog_list: list) -> dict:
    """проверка пользовательской ссылки на наличии в каталоге"""
    for catalog in catalog_list:
        if catalog['url'] == url.split('https://www.wildberries.ru')[-1]:
            print(f'найдено совпадение: {catalog["name"]}')
            return catalog


def get_data_from_json(json_file: dict) -> list:
    """извлекаем из json данные"""
    data_list = []
    for data in json_file['data']['products']:
        sku = data.get('id')
        name = data.get('name')
        price = int(data.get("priceU") / 100)
        sale = data.get('sale')
        brand = data.get('brand')
        rating = data.get('rating')
        supplier = data.get('supplier')
        supplierRating = data.get('supplierRating')

        data_list.append({
            'article_id': sku,
            'name': name,
            'price': price,
            'sale': sale,
            'brand': brand,
            'rating': rating,
            'supplier': supplier,
            'supplierRating': supplierRating,
        })
        # print(f"SKU:{data['id']} Цена: {int(data['salePriceU'] / 100)} Название: {data['name']} Рейтинг: {data['rating']}")
    return data_list


@retry(Exception, tries=-1, delay=0)
def scrap_page(page: int, shard: str, query: str, low_price: int, top_price: int, discount: int = None) -> dict:
    """Сбор данных со страниц"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        'Content-Type': 'application/json; charset=utf-8',
        'Transfer-Encoding': 'chunked',
        "Connection": "keep-alive",
        'Vary': 'Accept-Encoding',
        'Content-Encoding': 'gzip',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site"
    }
    url = f'https://catalog.wb.ru/catalog/{shard}/catalog?appType=1&curr=rub' \
          f'&dest=-1257786' \
          f'&locale=ru' \
          f'&page={page}' \
          f'&priceU={low_price * 100};{top_price * 100}' \
          f'&sort=popular&spp=0' \
          f'&{query}' \
          f'&discount={discount}'
    r = requests.get(url, headers=headers)
    print(f'Статус: {r.status_code} Страница {page} Идет сбор...')
    return r.json()


def save_db(data_list: list):
    """сохранение результата в БД """
    try:
        with session_sync() as session:
            products = [Product(**data) for data in data_list]
            session.add_all(products)
            session.commit()
    except Exception as e:
        raise ValueError from e


def clear_table():
    """Очистка таблицы"""
    try:
        with session_sync() as session:
            session.query(Product).delete()
            session.commit()
    except Exception as e:
        raise ValueError from e


def parser(url: str, low_price: int = 1, top_price: int = 1000000, discount: int = 0):
    """основная функция"""
    # получаем данные по заданному каталогу
    catalog_data = get_data_category(get_catalogs_wb())
    try:
        # поиск введенной категории в общем каталоге
        category = search_category_in_catalog(url=url, catalog_list=catalog_data)
        data_list = []

        for page in range(1, 51):  # вб отдает 50 страниц товара (раньше было 100)
            data = scrap_page(
                page=page,
                shard=category['shard'],
                query=category['query'],
                low_price=low_price,
                top_price=top_price,
                discount=discount)
            print(f'Добавлено позиций: {len(get_data_from_json(data))}')
            if len(get_data_from_json(data)) > 0:
                data_list.extend(get_data_from_json(data))
            else:
                break
        save_db(data_list)
        print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров. \n')
        print("Данные успешно сохранены в базе данных.\n")
        print(f'Ссылка для проверки: {url}?priceU={low_price * 100};{top_price * 100}&discount={discount}\n')
    except TypeError as e:
        print(f'Ошибка!{e} Возможно не верно указан раздел. Удалите все доп фильтры с ссылки\n')


if __name__ == '__main__':
    """данные для теста. собераем товар с раздела велосипеды в ценовой категории от 1тыс, до 100тыс, со скидкой 10%"""
    url = 'https://www.wildberries.ru/catalog/transportnye-sredstva/avtomobili'
    low_price = 70000  # нижний порог цены
    top_price = 10000000  # верхний порог цены
    discount = 10  # скидка в %
    start = datetime.datetime.now()  # запишем время старта
    # clear_table()  # очищаем таблицу перед следующим запуском если потребуется
    parser(url=url, low_price=low_price, top_price=top_price, discount=discount)
    end = datetime.datetime.now()  # запишем время завершения кода
    total = end - start
    print("Затраченное время:" + str(total))
