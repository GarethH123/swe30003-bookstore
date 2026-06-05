"""
order_routes.py - Shopping cart, checkout, and payment (simulated)
SWE30003 - Assignment 3
"""

import uuid
from datetime import datetime

from flask import (
    Blueprint, render_template, request,
    session, redirect, url_for, flash
)
from storage import load_json, save_json, find_by_id, update_record, append_record

order_bp = Blueprint("order", __name__, url_prefix="/order")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_cart() -> list:
    """Return the current session cart (list of dicts)."""
    return session.get("cart", [])


def _save_cart(cart: list) -> None:
    session["cart"] = cart
    session.modified = True


def _cart_total(cart: list) -> float:
    return sum(item["unit_price"] * item["quantity"] for item in cart)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@order_bp.route("/cart")
def view_cart():
    """Display the current shopping cart."""
    cart = _get_cart()
    total = _cart_total(cart)
    return render_template("order/cart.html", cart=cart, total=total)


@order_bp.route("/cart/add/<book_id>", methods=["POST"])
def add_to_cart(book_id: str):
    """Add a book to the cart (called from catalogue detail page)."""
    try:
        quantity = int(request.form.get("quantity", 1))
        if quantity < 1:
            raise ValueError
    except ValueError:
        flash("Invalid quantity.")
        return redirect(url_for("catalogue.book_detail", book_id=book_id))

    book = find_by_id("books.json", "book_id", book_id)
    if not book:
        flash("Book not found.")
        return redirect(url_for("catalogue.list_books"))

    if book["stock"] < quantity:
        flash(f"Only {book['stock']} copies available.")
        return redirect(url_for("catalogue.book_detail", book_id=book_id))

    cart = _get_cart()

    # If already in cart, increase quantity
    for item in cart:
        if item["book_id"] == book_id:
            new_qty = item["quantity"] + quantity
            if new_qty > book["stock"]:
                flash("Cannot add more than available stock.")
                return redirect(url_for("catalogue.book_detail", book_id=book_id))
            item["quantity"] = new_qty
            _save_cart(cart)
            flash(f'Updated "{book["title"]}" quantity in cart.')
            return redirect(url_for("order.view_cart"))

    cart.append({
        "book_id":    book["book_id"],
        "title":      book["title"],
        "unit_price": book["price"],
        "quantity":   quantity,
    })
    _save_cart(cart)
    flash(f'"{book["title"]}" added to cart.')
    return redirect(url_for("order.view_cart"))


@order_bp.route("/cart/remove/<book_id>", methods=["POST"])
def remove_from_cart(book_id: str):
    """Remove a specific book from the cart."""
    cart = [item for item in _get_cart() if item["book_id"] != book_id]
    _save_cart(cart)
    flash("Item removed from cart.")
    return redirect(url_for("order.view_cart"))


@order_bp.route("/cart/clear", methods=["POST"])
def clear_cart():
    """Empty the entire cart."""
    _save_cart([])
    flash("Cart cleared.")
    return redirect(url_for("order.view_cart"))


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@order_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    """
    GET  — Show checkout form (shipping address + payment method selection).
    POST — Validate inputs; redirect to payment confirmation step.
    """
    if "user_id" not in session:
        flash("Please log in to proceed to checkout.")
        return redirect(url_for("auth.login"))

    cart = _get_cart()
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("catalogue.list_books"))

    errors = []

    if request.method == "POST":
        shipping_address = request.form.get("shipping_address", "").strip()
        payment_method   = request.form.get("payment_method", "").strip()

        # --- Validation ---
        if not shipping_address:
            errors.append("Shipping address cannot be blank.")

        valid_methods = {"credit_card", "gift_card"}
        if payment_method not in valid_methods:
            errors.append("Please select a valid payment method.")

        if not errors:
            # Stash checkout data in session for the payment step
            session["pending_checkout"] = {
                "shipping_address": shipping_address,
                "payment_method":   payment_method,
            }
            session.modified = True
            return redirect(url_for("order.payment"))

    total = _cart_total(cart)
    return render_template(
        "order/checkout.html",
        cart=cart,
        total=total,
        errors=errors,
        # Re-populate fields on validation failure
        form_data=request.form if request.method == "POST" else {},
    )


# ---------------------------------------------------------------------------
# Payment (simulated — no real gateway per assignment spec)
# ---------------------------------------------------------------------------

@order_bp.route("/payment", methods=["GET", "POST"])
def payment():
    """
    GET  — Show payment summary + simulated 'Pay Now' button.
    POST — Simulate processing; create the order record; clear cart.

    Per assignment spec: no real payment gateway is integrated.
    A simulated confirmation message is shown instead.
    """
    if "user_id" not in session:
        flash("Please log in to complete payment.")
        return redirect(url_for("auth.login"))

    pending = session.get("pending_checkout")
    cart    = _get_cart()

    if not pending or not cart:
        flash("Nothing to pay for. Please start checkout again.")
        return redirect(url_for("order.view_cart"))

    total          = _cart_total(cart)
    payment_method = pending["payment_method"]
    # Human-readable label for the template
    method_label   = "Credit Card" if payment_method == "credit_card" else "Gift Card"

    if request.method == "POST":
        # ---- Simulate payment processing ----
        # In a real system this is where you'd call a payment gateway API.
        # Per the assignment spec, we simply mark the order as paid.

        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        order = {
            "order_id":         order_id,
            "user_id":          session["user_id"],
            "items":            cart,
            "status":           "processing",
            "total":            round(total, 2),
            "created_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "shipping_address": pending["shipping_address"],
            "payment_status":   "paid",
            "payment_method":   payment_method,
        }
        append_record("orders.json", order)

        # Deduct stock for each purchased book
        books = load_json("books.json")
        for item in cart:
            for book in books:
                if book["book_id"] == item["book_id"]:
                    book["stock"] = max(0, book["stock"] - item["quantity"])
        save_json("books.json", books)

        # Clean up session
        _save_cart([])
        session.pop("pending_checkout", None)

        flash(f"Payment processed successfully via {method_label}. Order {order_id} confirmed!")
        return redirect(url_for("order.confirmation", order_id=order_id))

    return render_template(
        "order/payment.html",
        cart=cart,
        total=total,
        pending=pending,
        method_label=method_label,
    )


@order_bp.route("/confirmation/<order_id>")
def confirmation(order_id: str):
    """Show order confirmation after successful payment."""
    order = find_by_id("orders.json", "order_id", order_id)
    if not order:
        return render_template("shared/error.html", message="Order not found."), 404
    return render_template("order/confirmation.html", order=order)