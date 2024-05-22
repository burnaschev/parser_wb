import datetime

import requests
from retry import retry
from sqlalchemy.orm import Session

from db.db_config import engine
from db.models import Product

Session = Session(engine)


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
        salePriceU = int(data.get('salePriceU') / 100)
        sale = data.get('sale')
        brand = data.get('brand')
        rating = data.get('rating')
        supplier = data.get('supplier')
        supplierRating = data.get('supplierRating')
        feedbacks = data.get('feedbacks')
        reviewRating = data.get('reviewRating')
        promoTextCard = data.get('promoTextCard')
        promoTextCat = data.get('promoTextCat')
        data_list.append({
            'id': sku,
            'name': name,
            'price': price,
            'salePriceU': salePriceU,
            'sale': sale,
            'brand': brand,
            'rating': rating,
            'supplier': supplier,
            'supplierRating': supplierRating,
            'feedbacks': feedbacks,
            'reviewRating': reviewRating,
            'promoTextCard': promoTextCard,
            'promoTextCat': promoTextCat,
            'link': f'https://www.wildberries.ru/catalog/{data.get("id")}/detail.aspx?targetUrl=BP'
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
        with Session as session:
            session.query(Product).delete()
            session.commit()
            new_product = []
            for data in data_list:
                new_product.append(Product(
                    article_id=int(data.get('id', None)),
                    name=data.get('name', None),
                    price=int(data.get('price', None)),
                    sale=data.get('sale', None),
                    brand=data.get('brand', None),
                    rating=data.get('rating', None),
                    supplier=data.get('supplier', None),
                    supplierRating=data.get('supplierRating', None)
                ))
            session.add_all(new_product)
            session.commit()
        print(f' Идёт сбор данных:... \n')
    except Exception as e:
        print(e)


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
            data_list.append(data)
            print(f'Добавлено позиций: {len(get_data_from_json(data))}')
            if len(get_data_from_json(data)) > 0:
                save_db(get_data_from_json(data))
                data_list.extend(get_data_from_json(data))
            else:
                break
        print(f'Сбор данных завершен. Собрано: {len(data_list)} товаров.')
        print(f'Ссылка для проверки: {url}?priceU={low_price * 100};{top_price * 100}&discount={discount}')
    except TypeError:
        print('Ошибка! Возможно не верно указан раздел. Удалите все доп фильтры с ссылки')


if __name__ == '__main__':
    """данные для теста. собераем товар с раздела велосипеды в ценовой категории от 1тыс, до 100тыс, со скидкой 10%"""
    url = 'https://www.wildberries.ru/catalog/elektronika/noutbuki-pereferiya/noutbuki-ultrabuki'
    low_price = 5000  # нижний порог цены
    top_price = 100000  # верхний порог цены
    discount = 10  # скидка в %
    start = datetime.datetime.now()  # запишем время старта

    parser(url=url, low_price=low_price, top_price=top_price, discount=discount)

    end = datetime.datetime.now()  # запишем время завершения кода
    total = end - start
    print("Затраченное время:" + str(total))
