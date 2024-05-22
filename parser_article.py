import requests


def get_item_json(article: str) -> dict:
    """Get a JSON representation of an article"""
    part = article[:-3]
    vol = article[:-5]
    baskets = [item for item in range(0, 20)]

    for basket in baskets:
        url_json = f"https://basket-{basket:02}.wbbasket.ru/vol{vol}/part{part}/{article}/info/ru/card.json"
        try:
            json_data = requests.get(url_json).json()
            return json_data
        except:
            continue
    return f"Товар не найден!"


if __name__ == "__main__":
    article = input("Введите артикул: ")
    # print(get_item_json(article=article))
    print(get_item_json(article))
