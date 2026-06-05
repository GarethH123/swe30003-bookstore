"""
stats_routes.py - Admin statistics dashboard for the Online Bookstore
SWE30003 - Assignment 3
OWNER: Andrew

Computes and displays key business metrics for admin users:
  - Total revenue from paid orders
  - Top 3 best-selling books by units sold
  - Order volume grouped by date
"""

from collections import defaultdict

from flask import Blueprint, render_template
from storage import load_json
from utils import admin_required

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_stats(orders: list) -> dict:
    """
    Derive all dashboard metrics from a flat list of order dicts.

    Separates computation from the route function so each metric can be
    unit-tested independently without a Flask application context.

    Args:
        orders: Raw list of order dicts loaded from orders.json.

    Returns:
        A dict with keys:
            total_revenue   (float)
            total_orders    (int)
            paid_orders     (int)
            best_sellers    (list of dicts: title, book_id, units_sold)
            orders_by_date  (list of dicts: date, count, revenue — sorted asc)
    """
    paid_orders = [o for o in orders if o.get("payment_status") == "paid"]

    # ------------------------------------------------------------------ #
    # 1. Total revenue — sum of Order.total across all paid orders         #
    # ------------------------------------------------------------------ #
    total_revenue = sum(o.get("total", 0.0) for o in paid_orders)

    # ------------------------------------------------------------------ #
    # 2. Best sellers — aggregate quantity per book across all paid orders #
    #                                                                      #
    # Order.items is a list of OrderItem-shaped dicts:                     #
    #   { book_id, title, quantity, unit_price }                           #
    # ------------------------------------------------------------------ #
    units_by_book: dict[str, dict] = {}   # book_id → { title, units_sold }

    for order in paid_orders:
        for item in order.get("items", []):
            book_id = item.get("book_id", "")
            if book_id not in units_by_book:
                units_by_book[book_id] = {
                    "book_id":    book_id,
                    "title":      item.get("title", "Unknown"),
                    "units_sold": 0,
                    "revenue":    0.0,
                }
            units_by_book[book_id]["units_sold"] += item.get("quantity", 0)
            units_by_book[book_id]["revenue"] += (
                item.get("quantity", 0) * item.get("unit_price", 0.0)
            )

    best_sellers = sorted(
        units_by_book.values(),
        key=lambda b: b["units_sold"],
        reverse=True,
    )[:3]

    # ------------------------------------------------------------------ #
    # 3. Orders by date — group ALL orders (paid + unpaid) by the date     #
    #    portion of Order.created_at ("YYYY-MM-DD HH:MM:SS")               #
    # ------------------------------------------------------------------ #
    date_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "revenue": 0.0})

    for order in orders:
        raw_date = order.get("created_at", "")
        # created_at format: "2026-05-30 14:22:01" — take the date part only
        date_key = raw_date[:10] if len(raw_date) >= 10 else "Unknown"

        date_stats[date_key]["count"] += 1

        if order.get("payment_status") == "paid":
            date_stats[date_key]["revenue"] += order.get("total", 0.0)

    orders_by_date = [
        {"date": date, "count": stats["count"], "revenue": stats["revenue"]}
        for date, stats in date_stats.items()
    ]
    # Sort chronologically so the table reads naturally top-to-bottom
    orders_by_date.sort(key=lambda r: r["date"])

    return {
        "total_revenue":  round(total_revenue, 2),
        "total_orders":   len(orders),
        "paid_orders":    len(paid_orders),
        "best_sellers":   best_sellers,
        "orders_by_date": orders_by_date,
    }


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@stats_bp.route("/")
@admin_required
def dashboard():
    """
    Admin statistics dashboard.

    Reads orders.json once and delegates all computation to _compute_stats
    so the route function stays thin — its only job is load → compute → render.
    """
    orders = load_json("orders.json")
    stats  = _compute_stats(orders)

    return render_template("stats/dashboard.html", **stats)