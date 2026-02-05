"""Generate a realistic e-commerce dataset: ~50K orders over 1 year."""

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

DATA_DIR = Path(__file__).parent / "data"

# --- Product catalog ---

CATEGORIES = {
    "Electronics": [
        ("Wireless Earbuds", 29.99, 79.99),
        ("USB-C Hub", 19.99, 49.99),
        ("Phone Case", 9.99, 24.99),
        ("Bluetooth Speaker", 34.99, 89.99),
        ("Laptop Stand", 24.99, 59.99),
        ("Webcam HD", 39.99, 79.99),
        ("Portable Charger", 14.99, 39.99),
        ("Smart Watch Band", 9.99, 19.99),
        ("LED Desk Lamp", 19.99, 49.99),
        ("HDMI Cable", 7.99, 14.99),
    ],
    "Clothing": [
        ("Cotton T-Shirt", 12.99, 29.99),
        ("Running Shorts", 19.99, 39.99),
        ("Wool Beanie", 9.99, 24.99),
        ("Denim Jacket", 49.99, 89.99),
        ("Casual Sneakers", 39.99, 79.99),
        ("Linen Shirt", 24.99, 49.99),
        ("Athletic Socks 3-pack", 8.99, 16.99),
        ("Rain Jacket", 34.99, 69.99),
    ],
    "Home & Garden": [
        ("Scented Candle", 9.99, 24.99),
        ("Plant Pot Set", 14.99, 34.99),
        ("Kitchen Timer", 7.99, 14.99),
        ("Throw Blanket", 24.99, 49.99),
        ("Wall Shelf", 19.99, 44.99),
        ("Door Mat", 12.99, 29.99),
        ("Herb Garden Kit", 16.99, 34.99),
    ],
    "Sports": [
        ("Yoga Mat", 19.99, 39.99),
        ("Resistance Bands Set", 12.99, 29.99),
        ("Water Bottle 750ml", 9.99, 19.99),
        ("Jump Rope", 7.99, 16.99),
        ("Foam Roller", 14.99, 34.99),
        ("Gym Gloves", 9.99, 22.99),
    ],
    "Beauty": [
        ("Face Moisturizer", 14.99, 34.99),
        ("Lip Balm Set", 6.99, 14.99),
        ("Hair Serum", 12.99, 29.99),
        ("Sunscreen SPF50", 9.99, 19.99),
        ("Sheet Mask Pack", 8.99, 18.99),
        ("Nail Polish Set", 11.99, 24.99),
    ],
}

COUNTRIES = ["US", "UK", "DE", "FR", "PL", "CA"]
COUNTRY_WEIGHTS = [0.40, 0.18, 0.15, 0.12, 0.08, 0.07]

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]
PAYMENT_WEIGHTS = [0.35, 0.20, 0.25, 0.12, 0.08]

SHIPPING_COST_BY_COUNTRY = {
    "US": (3.99, 9.99),
    "UK": (4.99, 12.99),
    "DE": (5.99, 14.99),
    "FR": (5.99, 14.99),
    "PL": (4.99, 11.99),
    "CA": (5.99, 13.99),
}


def _seasonal_multiplier(day_of_year: int) -> float:
    """Return an order volume multiplier based on the day of year.

    Creates a natural annual cycle with a strong Nov-Dec spike.
    """
    base = 1.0 + 0.15 * math.sin(2 * math.pi * (day_of_year - 80) / 365)

    # Black Friday / Christmas spike (days ~320-360 → mid-Nov to late Dec)
    if 315 <= day_of_year <= 360:
        peak_center = 340
        spike = 0.8 * math.exp(-0.5 * ((day_of_year - peak_center) / 12) ** 2)
        base += spike

    # Small Valentine's Day bump
    if 38 <= day_of_year <= 52:
        base += 0.15

    return base


def _generate_customers(n: int) -> list[dict]:
    """Pre-generate a pool of customers with Pareto-like purchase frequency."""
    customers = []
    for i in range(n):
        customers.append(
            {
                "customer_id": f"CUST-{i + 1:06d}",
                "customer_email": fake.email(),
                "weight": float(np.random.pareto(1.5) + 1),
            }
        )
    return customers


def generate_orders(
    start_date: datetime,
    end_date: datetime,
    target_orders: int = 50_000,
) -> list[dict]:
    """Generate realistic e-commerce order data."""
    total_days = (end_date - start_date).days
    customer_pool = _generate_customers(n=12_000)
    customer_weights = np.array([c["weight"] for c in customer_pool])
    customer_weights /= customer_weights.sum()

    # Flatten product catalog
    all_products = []
    for category, products in CATEGORIES.items():
        for name, price_low, price_high in products:
            all_products.append((name, category, price_low, price_high))

    # Distribute orders across days using seasonal multiplier
    daily_multipliers = [_seasonal_multiplier(d) for d in range(1, total_days + 1)]
    total_mult = sum(daily_multipliers)
    daily_orders = [
        max(1, round(target_orders * m / total_mult)) for m in daily_multipliers
    ]

    orders = []
    order_counter = 0

    for day_idx, n_orders_today in enumerate(daily_orders):
        current_date = start_date + timedelta(days=day_idx)

        # Pick customers for today (weighted by purchase frequency)
        customer_indices = np.random.choice(
            len(customer_pool), size=n_orders_today, p=customer_weights
        )

        for cust_idx in customer_indices:
            order_counter += 1
            cust = customer_pool[cust_idx]

            # Random time of day (more orders in evening)
            hour = int(np.random.beta(5, 3) * 24) % 24
            minute = random.randint(0, 59)
            order_time = current_date.replace(
                hour=hour, minute=minute, second=random.randint(0, 59)
            )

            # Order-level attributes (same for all items in this order)
            country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
            ship_low, ship_high = SHIPPING_COST_BY_COUNTRY[country]
            shipping_cost = round(random.uniform(ship_low, ship_high), 2)
            payment = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0]

            # Order status: ~85% completed, ~8% refunded, ~7% cancelled
            status_roll = random.random()
            if status_roll < 0.08:
                order_status = "refunded"
            elif status_roll < 0.15:
                order_status = "cancelled"
            else:
                order_status = "completed"

            # Pick 1-4 items per order (most orders have 1-2)
            n_items = np.random.choice([1, 1, 1, 2, 2, 3, 4])
            chosen_products = random.sample(all_products, k=n_items)

            for product_name, category, price_low, price_high in chosen_products:
                unit_price = round(random.uniform(price_low, price_high), 2)
                quantity = np.random.choice([1, 1, 1, 1, 2, 2, 3])

                # Discount: 0% most of the time, occasional 5-25%
                discount_pct = 0.0
                if random.random() < 0.20:
                    discount_pct = random.choice([0.05, 0.10, 0.10, 0.15, 0.20, 0.25])
                # Higher discounts during holiday season
                if (
                    315 <= current_date.timetuple().tm_yday <= 360
                    and random.random() < 0.35
                ):
                    discount_pct = random.choice([0.10, 0.15, 0.20, 0.25, 0.30])

                orders.append(
                    {
                        "order_id": f"ORD-{order_counter:07d}",
                        "order_date": order_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "customer_id": cust["customer_id"],
                        "customer_email": cust["customer_email"],
                        "product_name": product_name,
                        "product_category": category,
                        "quantity": int(quantity),
                        "unit_price": unit_price,
                        "discount": discount_pct,
                        "shipping_cost": shipping_cost,
                        "shipping_country": country,
                        "payment_method": payment,
                        "order_status": order_status,
                    }
                )

    # Inject some messy data to make cleaning realistic
    _inject_data_issues(orders)
    random.shuffle(orders)
    return orders


def _inject_data_issues(orders: list[dict]) -> None:
    """Add realistic data quality issues: duplicates, missing values, format inconsistencies."""
    n = len(orders)

    # ~0.5% duplicate rows
    n_dupes = int(n * 0.005)
    for _ in range(n_dupes):
        idx = random.randint(0, n - 1)
        orders.append(orders[idx].copy())

    # ~1% missing emails
    for _ in range(int(n * 0.01)):
        idx = random.randint(0, n - 1)
        orders[idx]["customer_email"] = ""

    # ~0.3% negative quantities (data entry error)
    for _ in range(int(n * 0.003)):
        idx = random.randint(0, n - 1)
        orders[idx]["quantity"] = -abs(orders[idx]["quantity"])

    # ~0.5% mixed date formats
    for _ in range(int(n * 0.005)):
        idx = random.randint(0, n - 1)
        date_str = orders[idx]["order_date"]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            orders[idx]["order_date"] = dt.strftime("%m/%d/%Y %H:%M")
        except ValueError:
            pass  # already reformatted


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "raw_orders.csv"

    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)

    print("Generating e-commerce order data...")
    orders = generate_orders(start, end, target_orders=50_000)
    print(f"  Total rows (including duplicates/issues): {len(orders):,}")

    fieldnames = [
        "order_id",
        "order_date",
        "customer_id",
        "customer_email",
        "product_name",
        "product_category",
        "quantity",
        "unit_price",
        "discount",
        "shipping_cost",
        "shipping_country",
        "payment_method",
        "order_status",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(orders)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Saved to {output_path} ({size_mb:.1f} MB)")
    print("Done.")


if __name__ == "__main__":
    main()
