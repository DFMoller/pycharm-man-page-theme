"""Sample code for theme screenshots.

This module exists only to fill the editor with as many kinds of syntax highlighting as possible:
keywords, strings, numbers, decorators, type hints, docstrings, comments and a few deliberate
inspection warnings. It is not meant to be imported by anything.
"""

import dataclasses
import os
import re
from collections.abc import Iterator
from enum import StrEnum

MAX_ITEMS = 1_000
PATTERN = re.compile(r"^(?P<sku>[A-Z]{3})-(?P<number>\d{4})$")


class Category(StrEnum):
    TOOL = "tool"
    PART = "part"


@dataclasses.dataclass(frozen=True)
class Item:
    """One line of stock."""

    sku: str
    category: Category
    quantity: int = 0
    price: float = 0.0

    @property
    def value(self) -> float:
        return self.quantity * self.price


def parse_line(line: str) -> Item | None:
    # Lines that do not match the SKU pattern are skipped, not reported.
    sku, _, rest = line.partition(",")
    if not PATTERN.match(sku):
        return None
    quantity, price = rest.split(",")
    return Item(sku, Category.PART, int(quantity), float(price))


def read_items(path: str) -> Iterator[Item]:
    unused = os.sep
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if number > MAX_ITEMS:
                raise ValueError(f"Too many items in {path!r}: more than {MAX_ITEMS}.")
            if (item := parse_line(line.strip())) is not None:
                yield item


def total_value(items: list[Item]) -> float:
    return sum(item.value for item in items if item.quantity > 0)


if __name__ == "__main__":
    print(total_value(list(read_items("stock.csv"))))
