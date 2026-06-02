"""
models.py - Core data models for the Online Bookstore
SWE30003 - Assignment 3
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    user_id: str
    name: str
    email: str
    password_hash: str
    address: str = ""
    phone: str = ""
    role: str = "customer"  # "customer" or "admin"


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    genre: str
    price: float
    stock: int
    description: str = ""
    isbn: str = ""
    publisher: str = ""
    year: int = 2024


@dataclass
class OrderItem:
    book_id: str
    title: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Order:
    order_id: str
    user_id: str
    items: list = field(default_factory=list)  # list of OrderItem dicts
    status: str = "pending"                    # pending, paid, processing, shipped, delivered
    total: float = 0.0
    created_at: str = ""
    shipping_address: str = ""
    payment_status: str = "unpaid"             # unpaid, paid


@dataclass
class Shipment:
    shipment_id: str
    order_id: str
    status: str = "processing"                 # processing, dispatched, delivered
    tracking_number: str = ""
    carrier: str = ""
    dispatched_at: str = ""
    delivered_at: str = ""
    estimated_delivery: str = ""
