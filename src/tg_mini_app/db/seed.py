from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tg_mini_app.db import models


@dataclass(frozen=True, slots=True)
class SeedProduct:
    name: str
    description: str
    price_rub: int
    weight_g: int


DEFAULT_CATEGORIES: list[str] = [
    "Горячие жаренные ролы",
    "Запеченые ролы",
    "Холодные ролы",
]


DEFAULT_PRODUCTS: list[SeedProduct] = [
    SeedProduct("Ахи", "Тунец", 150, 180),
    SeedProduct("Аджи", "Испанская скумбрия", 190, 200),
    SeedProduct("Ама эби", "Сладкие креветки", 210, 155),
    SeedProduct("Анаго", "Морской угорь", 250, 160),
    SeedProduct("Аояги", "Круглый моллюск", 300, 185),
    SeedProduct("Бинчо", "Белый длинноперый тунец", 280, 210),
    SeedProduct("Кацуо", "Полосатый тунец", 300, 220),
    SeedProduct("Эби", "Тигровая креветка", 200, 180),
    SeedProduct("Эсколар", "Рыба-баттерфиш", 160, 180),
    SeedProduct("Хамачи", "Рыба желтохвост", 260, 140),
    SeedProduct("Хамачи Торо", "Жирная часть желтохвоста", 140, 110),
    SeedProduct("Хираме", "Палтус", 195, 140),
    SeedProduct("Хоккигай", "Мелководный моллюск", 255, 210),
    SeedProduct("Хотатэ", "Гребешок", 180, 160),
    SeedProduct("Ика", "Кальмар", 220, 170),
    SeedProduct("Икура", "Икра лосося", 165, 215),
    SeedProduct("Кани", "Мясо краба", 190, 140),
    SeedProduct("Канпачи", "Амберджек", 160, 200),
    SeedProduct("Саба", "Скумбрия", 100, 150),
    SeedProduct("Сяке", "Лосось", 110, 160),
    SeedProduct("Сяке Торо", "Жирная часть лосося", 180, 200),
    SeedProduct("Тай", "Морской окунь", 230, 130),
    SeedProduct("Тако", "Осьминог", 180, 150),
    SeedProduct("Томаго", "Сладкий яичный омлет", 200, 150),
    SeedProduct("Торо", "Жирная часть голубого тунца", 170, 110),
    SeedProduct("Цубугай", "Брюхоногие моллюски", 180, 120),
    SeedProduct("Уми Масу", "Морская форель", 260, 160),
    SeedProduct("Унаги", "Пресноводный угорь на гриле", 260, 160),
    SeedProduct("Уни", "Морской ёж", 250, 150),
]


async def seed_if_empty(session: AsyncSession) -> None:
    existing_categories = (
        await session.execute(select(models.Category.id).limit(1))
    ).first()
    if existing_categories is not None:
        return

    categories: dict[str, models.Category] = {}
    for idx, name in enumerate(DEFAULT_CATEGORIES):
        c = models.Category(name=name, sort_order=idx, is_active=True)
        session.add(c)
        categories[name] = c

    n_products = len(DEFAULT_PRODUCTS)
    n_cats = len(DEFAULT_CATEGORIES)
    sort_in_cat: defaultdict[str, int] = defaultdict(int)

    for idx, p in enumerate(DEFAULT_PRODUCTS):
        cat_index = min(idx * n_cats // n_products, n_cats - 1)
        cat_name = DEFAULT_CATEGORIES[cat_index]
        target = categories[cat_name]
        so = sort_in_cat[cat_name]
        sort_in_cat[cat_name] += 1
        session.add(
            models.Product(
                category=target,
                name=p.name,
                description=p.description,
                composition="",
                weight_g=p.weight_g,
                price=Decimal(p.price_rub),
                image_url="",
                is_available=True,
                sort_order=so,
            )
        )

    await session.commit()

