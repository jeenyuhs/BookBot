import itertools
import math
import aiohttp

import numpy


HYPIXEL_API = "https://api.hypixel.net/v2/skyblock"


def integer_to_roman(num: int) -> str:
    symbols = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]

    roman = ""
    for value, symbol in symbols:
        while num >= value:
            roman += symbol
            num -= value

    return roman


def readable_skyblock_book_name(book_id: str) -> str:
    name = book_id.lower().split("_")
    return " ".join(part.capitalize() for part in name[1:])


class Book:
    def __init__(self, book_id: str):
        self.book_id: str = book_id

        self.buy_order_price: float = 0.0
        self.sell_order_price: float = 0.0

        self.instant_buy_price: float = 0.0
        self.instant_sell_price: float = 0.0

        self.weekly_instant_buys: int = 0
        self.weekly_instant_sells: int = 0

    @property
    def is_min(self):
        return self.book_id.endswith("_1")

    @property
    def is_max(self):
        return self.book_id.endswith("_5")

    @property
    def readable_name(self):
        if self.book_id == "unknown":
            return self.book_id

        name = self.book_id.lower().split("_")
        level = integer_to_roman(int(name[-1]))

        return " ".join([*[part.capitalize() for part in name[1:-1]], level])


class CombinableBook:
    def __init__(self):
        self.min: Book = Book("unknown")
        self.max: Book = Book("unknown")

    @property
    def margin(self):
        return self.max.sell_order_price - self.min.buy_order_price * 16

    @property
    def score(self):
        if self.min.weekly_instant_sells <= 0 or self.max.weekly_instant_buys <= 0:
            return 0

        # quick scoring system to determine
        # which combinable book would be best
        # invest in.

        difference = abs(
            self.max.weekly_instant_buys * 1.87 - self.min.weekly_instant_sells * 0.9
        )

        margin_importance = self.margin**1.15 / 1_000_000
        score = (
            1 / difference
            + (
                self.max.weekly_instant_buys
                / 5000
                * self.min.weekly_instant_sells
                / 2000
            )
        ) * margin_importance

        # wtf?
        if not isinstance(score, complex):
            return score

        return 0

    def insert(self, book: Book):
        if book.is_min:
            self.min = book
        elif book.is_max:
            self.max = book
        else:
            return


class BestBooks:
    def __init__(self):
        self.books: dict[str, CombinableBook] = {}

    def __iter__(self):
        return iter(self.books.items())

    @classmethod
    async def fetch(cls) -> "BestBooks":
        c = cls()
        async with aiohttp.ClientSession() as session:
            url = HYPIXEL_API + "/bazaar"
            async with session.get(url) as resp:
                resp = await resp.json()

                if resp["success"] != True:
                    return c

                for product, info in resp["products"].items():
                    # skip any product, that isn't an enchantment book
                    if not product.startswith("ENCHANTMENT"):
                        continue

                    # remove the last 2 characters, as in `_1`, `_2`
                    actual_book_name = "_".join(product.split("_")[:-1])

                    if actual_book_name not in c.books:
                        c.books[actual_book_name] = CombinableBook()

                    book = Book(product)

                    # get buy order price and sell order price
                    if latest_instant_sell := info["sell_summary"]:
                        book.buy_order_price = latest_instant_sell[0]["pricePerUnit"]
                        book.instant_sell_price = latest_instant_sell[0]["pricePerUnit"]

                    if latest_instant_buy := info["buy_summary"]:
                        book.sell_order_price = latest_instant_buy[0]["pricePerUnit"]
                        book.instant_buy_price = latest_instant_buy[0]["pricePerUnit"]

                    status = info["quick_status"]

                    book.weekly_instant_buys = status["buyMovingWeek"]
                    book.weekly_instant_sells = status["sellMovingWeek"]

                    # finally insert into dictionary
                    c.books[actual_book_name].insert(book)

            # at the absolute end we'll sort the books
            # descending according to the score property.

            c.books = dict(
                sorted(c.books.items(), key=lambda value: value[1].score, reverse=True)
            )

            return c

    def as_chunks(self, size: int = 5):
        it = iter(self.books)
        for i in range(0, len(self.books), size):
            yield {k: self.books[k] for k in itertools.islice(it, size)}
