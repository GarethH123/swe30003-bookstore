"""
order_routes.py - Shopping cart, checkout, place order and payment confirmation
SWE30003 - Assignment 3


Cart is stored in the Flask session as a mapping of book_id -> quantity.
Checkout creates an Order (orders.json) and an Invoice (invoices.json).
Payment confirmation creates a Receipt (receipts.json) and marks the order paid.
Payment processing is simplified per the assignment spec - no real transaction occurs.
"""

from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash
)

from blueprints.auth_routes import login_required
from storage import load_json, append_record, update_record, find_by_id

order_bp = Blueprint("order", __name__, url_prefix="/order")

BOOKS_FILE = "books.json"
ORDERS_FILE = "orders.json"
INVOICES_FILE = "invoices.json"
RECEIPTS_FILE = "receipts.json"
USERS_FILE = "users.json"

TAX_RATE = 0.10  # 10% GST, applied for invoice breakdown


def _get_cart() -> dict:
    """Return the current session cart as a {book_id: quantity} dict."""
    return session.get("cart", {})


def _save_cart(cart: dict) -> None:
    """Persist the cart back to the session."""
    session["cart"] = cart
    session.modified = True


def _build_cart_items():
    """Join the session cart with book data to produce line items and a total."""
    cart = _get_cart()
    books = load_json(BOOKS_FILE)
    books_by_id = {b["book_id"]: b for b in books}

    items = []
    total = 0.0
    for book_id, quantity in cart.items():
        book = books_by_id.get(book_id)
        if not book:
            continue
        unit_price = book.get("price", 0.0)
        subtotal = unit_price * quantity
        total += subtotal
        items.append({
            "book_id": book_id,
            "title": book.get("title", "Unknown"),
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
            "stock": book.get("stock", 0),
        })
    return items, total


def _next_id(filename: str, prefix: str, width: int) -> str:
    """Generate the next sequential ID for a JSON file (e.g. O001, INV001)."""
    count = len(load_json(filename))
    return f"{prefix}{count + 1:0{width}}"


@order_bp.route("/cart")
def cart():
    """Display the current shopping cart."""
    items, total = _build_cart_items()
    return render_template("order/cart.html", items=items, total=total)


@order_bp.route("/cart/add/<book_id>", methods=["POST"])
def add_to_cart(book_id):
    """Add a book to the cart from the catalogue detail page."""
    book = find_by_id(BOOKS_FILE, "book_id", book_id)
    if not book:
        flash("That book could not be found.", "error")
        return redirect(url_for("catalogue.list_books"))

    try:
        quantity = int(request.form.get("quantity", 1))
    except (TypeError, ValueError):
        flash("Please enter a valid quantity.", "error")
        return redirect(url_for("catalogue.book_detail", book_id=book_id))

    if quantity < 1:
        flash("Quantity must be at least 1.", "error")
        return redirect(url_for("catalogue.book_detail", book_id=book_id))

    cart = _get_cart()
    cart[book_id] = cart.get(book_id, 0) + quantity
    _save_cart(cart)

    flash(f"Added \"{book['title']}\" to your cart.", "success")
    return redirect(url_for("order.cart"))


@order_bp.route("/cart/update/<book_id>", methods=["POST"])
def update_cart(book_id):
    """Update the quantity of a book in the cart (0 removes it)."""
    cart = _get_cart()
    if book_id not in cart:
        flash("That item is not in your cart.", "error")
        return redirect(url_for("order.cart"))

    try:
        quantity = int(request.form.get("quantity", 1))
    except (TypeError, ValueError):
        flash("Please enter a valid quantity.", "error")
        return redirect(url_for("order.cart"))

    if quantity < 1:
        cart.pop(book_id, None)
        flash("Item removed from cart.", "success")
    else:
        cart[book_id] = quantity
        flash("Cart updated.", "success")

    _save_cart(cart)
    return redirect(url_for("order.cart"))


@order_bp.route("/cart/remove/<book_id>", methods=["POST"])
def remove_from_cart(book_id):
    """Remove a book from the cart entirely."""
    cart = _get_cart()
    if cart.pop(book_id, None) is not None:
        _save_cart(cart)
        flash("Item removed from cart.", "success")
    return redirect(url_for("order.cart"))


@order_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """Confirm shipping details, then create the Order and Invoice."""
    items, total = _build_cart_items()

    if not items:
        flash("Your cart is empty. Add some books before checking out.", "error")
        return redirect(url_for("order.cart"))

    user = find_by_id(USERS_FILE, "user_id", session["user_id"])

    if request.method == "POST":
        shipping_address = request.form.get("shipping_address", "").strip()

        if not shipping_address:
            flash("A shipping address is required to place an order.", "error")
            return render_template(
                "order/checkout.html",
                items=items,
                total=total,
                user=user,
            )

        now = datetime.now().isoformat(timespec="seconds")
        order_id = _next_id(ORDERS_FILE, "O", 3)

        order = {
            "order_id": order_id,
            "user_id": session["user_id"],
            "items": [
                {
                    "book_id": item["book_id"],
                    "title": item["title"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "subtotal": item["subtotal"],
                }
                for item in items
            ],
            "total": round(total, 2),
            "status": "pending",
            "payment_status": "unpaid",
            "shipping_address": shipping_address,
            "created_at": now,
        }
        append_record(ORDERS_FILE, order)

        tax = round(total - (total / (1 + TAX_RATE)), 2)
        invoice = {
            "invoice_id": _next_id(INVOICES_FILE, "INV", 3),
            "order_id": order_id,
            "user_id": session["user_id"],
            "issue_date": now,
            "total": round(total, 2),
            "tax": tax,
            "payment_status": "unpaid",
        }
        append_record(INVOICES_FILE, invoice)

        flash("Order placed. Please complete payment.", "success")
        return redirect(url_for("order.payment", order_id=order_id))

    return render_template(
        "order/checkout.html",
        items=items,
        total=total,
        user=user,
    )


@order_bp.route("/payment/<order_id>", methods=["GET", "POST"])
@login_required
def payment(order_id):
    """Simplified payment confirmation - creates a Receipt and marks the order paid."""
    order = find_by_id(ORDERS_FILE, "order_id", order_id)

    if not order or order.get("user_id") != session["user_id"]:
        flash("Order not found.", "error")
        return redirect(url_for("order.cart"))

    if order.get("payment_status") == "paid":
        flash("This order has already been paid.", "error")
        return redirect(url_for("order.confirmation", order_id=order_id))

    invoice = next(
        (i for i in load_json(INVOICES_FILE) if i.get("order_id") == order_id),
        None,
    )

    if request.method == "POST":
        payment_method = request.form.get("payment_method", "").strip()

        if not payment_method:
            flash("Please select a payment method.", "error")
            return render_template(
                "order/payment.html", order=order, invoice=invoice
            )

        now = datetime.now().isoformat(timespec="seconds")

        order["payment_status"] = "paid"
        order["status"] = "paid"
        update_record(ORDERS_FILE, "order_id", order_id, order)

        if invoice:
            invoice["payment_status"] = "paid"
            update_record(INVOICES_FILE, "invoice_id", invoice["invoice_id"], invoice)

        payment_id = _next_id(RECEIPTS_FILE, "PAY", 3)
        receipt = {
            "receipt_id": _next_id(RECEIPTS_FILE, "RC", 3),
            "invoice_id": invoice["invoice_id"] if invoice else "",
            "order_id": order_id,
            "payment_id": payment_id,
            "amount_paid": order["total"],
            "payment_method": payment_method,
            "date": now,
        }
        append_record(RECEIPTS_FILE, receipt)

        session.pop("cart", None)

        flash("Payment processed successfully.", "success")
        return redirect(url_for("order.confirmation", order_id=order_id))

    return render_template("order/payment.html", order=order, invoice=invoice)


@order_bp.route("/confirmation/<order_id>")
@login_required
def confirmation(order_id):
    """Display the final order, invoice and receipt summary."""
    order = find_by_id(ORDERS_FILE, "order_id", order_id)

    if not order or order.get("user_id") != session["user_id"]:
        flash("Order not found.", "error")
        return redirect(url_for("order.cart"))

    invoice = next(
        (i for i in load_json(INVOICES_FILE) if i.get("order_id") == order_id),
        None,
    )
    receipt = next(
        (r for r in load_json(RECEIPTS_FILE) if r.get("order_id") == order_id),
        None,
    )

    return render_template(
        "order/confirmation.html",
        order=order,
        invoice=invoice,
        receipt=receipt,
    )
