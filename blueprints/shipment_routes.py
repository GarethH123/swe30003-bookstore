"""
shipment_routes.py - Shipment management for the Online Bookstore
SWE30003 - Assignment 3
OWNER: Andrew

Handles admin-only shipment tracking:
  - View all paid orders and their shipment statuses
  - Dispatch an order (processing → dispatched)
  - Mark an order as delivered (dispatched → delivered)

Shipment records are created lazily on first dispatch — an order that has
never been dispatched will not yet have a row in shipments.json.
"""

import uuid
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, abort
from storage import load_json, save_json, find_by_id, append_record, update_record
from utils import admin_required

shipment_bp = Blueprint("shipment", __name__, url_prefix="/shipment")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Valid one-way status transitions for shipments.
# A shipment can only move forward, never backward.
_VALID_TRANSITIONS = {
    "processing": "dispatched",
    "dispatched":  "delivered",
}

# The corresponding Order.status value to set when a shipment transitions.
_ORDER_STATUS_MAP = {
    "dispatched": "shipped",
    "delivered":  "delivered",
}


def _get_shipment_map() -> dict:
    """
    Return a dict keyed by order_id for O(1) shipment lookups.
    e.g. { "ORD-ABCD1234": { shipment record }, ... }
    """
    shipments = load_json("shipments.json")
    return {s["order_id"]: s for s in shipments}


def _transition_shipment(order_id: str, target_status: str):
    """
    Core logic shared by dispatch and deliver routes.

    1. Validates that the order exists and is paid.
    2. Creates a shipment record if one does not exist yet (dispatch only).
    3. Validates the status transition is legal.
    4. Updates shipments.json and orders.json atomically (both saves
       succeed or neither is visible to the next request).

    Returns (success: bool, error_message: str | None).
    """
    # --- Load order ---
    order = find_by_id("orders.json", "order_id", order_id)
    if not order:
        return False, f"Order '{order_id}' not found."

    if order.get("payment_status") != "paid":
        return False, f"Order '{order_id}' has not been paid and cannot be shipped."

    # --- Load or create shipment record ---
    shipments = load_json("shipments.json")
    shipment  = next((s for s in shipments if s["order_id"] == order_id), None)

    if shipment is None:
        # First time this order is being dispatched — create the record now.
        if target_status != "dispatched":
            return False, f"Order '{order_id}' has no shipment record yet. Dispatch it first."

        shipment = {
            "shipment_id":        f"SHP-{uuid.uuid4().hex[:8].upper()}",
            "order_id":           order_id,
            "status":             "processing",   # will be updated below
            "tracking_number":    f"TRK-{uuid.uuid4().hex[:10].upper()}",
            "carrier":            "Standard Post",
            "dispatched_at":      "",
            "delivered_at":       "",
            "estimated_delivery": "",
        }
        shipments.append(shipment)

    # --- Validate transition ---
    current_status = shipment["status"]
    allowed_next   = _VALID_TRANSITIONS.get(current_status)

    if allowed_next != target_status:
        if current_status == target_status:
            return False, f"Shipment for order '{order_id}' is already '{target_status}'."
        return False, (
            f"Cannot move shipment from '{current_status}' to '{target_status}'. "
            f"Expected next status: '{allowed_next}'."
        )

    # --- Apply transition ---
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    shipment["status"] = target_status

    if target_status == "dispatched":
        shipment["dispatched_at"]      = now
        shipment["estimated_delivery"] = "3–5 business days"
    elif target_status == "delivered":
        shipment["delivered_at"] = now

    # Persist shipments.json
    save_json("shipments.json", shipments)

    # Keep Order.status in sync
    order["status"] = _ORDER_STATUS_MAP[target_status]
    update_record("orders.json", "order_id", order_id, order)

    return True, None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@shipment_bp.route("/")
@admin_required
def list_shipments():
    """
    Display all paid orders alongside their current shipment status.

    Only orders with payment_status == 'paid' are relevant to shipping —
    unpaid/pending orders are filtered out to keep the view focused.
    """
    orders       = load_json("orders.json")
    shipment_map = _get_shipment_map()

    # Only show orders that have been paid
    paid_orders = [o for o in orders if o.get("payment_status") == "paid"]

    # Attach the matching shipment record (or None) to each order for the template
    rows = []
    for order in paid_orders:
        rows.append({
            "order":    order,
            "shipment": shipment_map.get(order["order_id"]),  # None if not yet dispatched
        })

    # Sort: unshipped first (so actionable items are at the top), then by created_at desc
    status_priority = {"processing": 0, "dispatched": 1, "delivered": 2}
    rows.sort(key=lambda r: (
        status_priority.get(r["shipment"]["status"] if r["shipment"] else "processing", 0),
        r["order"].get("created_at", ""),
    ))

    return render_template("shipment/list.html", rows=rows)


@shipment_bp.route("/dispatch/<order_id>", methods=["POST"])
@admin_required
def dispatch(order_id: str):
    """Mark a shipment as dispatched (processing → dispatched)."""
    success, error = _transition_shipment(order_id, "dispatched")

    if success:
        flash(f"Order {order_id} has been dispatched successfully.", "success")
    else:
        flash(f"Dispatch failed: {error}", "error")

    return redirect(url_for("shipment.list_shipments"))


@shipment_bp.route("/deliver/<order_id>", methods=["POST"])
@admin_required
def deliver(order_id: str):
    """Mark a shipment as delivered (dispatched → delivered)."""
    success, error = _transition_shipment(order_id, "delivered")

    if success:
        flash(f"Order {order_id} has been marked as delivered.", "success")
    else:
        flash(f"Deliver failed: {error}", "error")

    return redirect(url_for("shipment.list_shipments"))