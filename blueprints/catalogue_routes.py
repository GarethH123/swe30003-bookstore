"""
catalogue_routes.py - Browse and search the bookstore catalogue
SWE30003 - Assignment 3
OWNER: Gareth Hand
"""

from flask import Blueprint, render_template, request
from storage import load_json

catalogue_bp = Blueprint("catalogue", __name__, url_prefix="/catalogue")


@catalogue_bp.route("/")
def list_books():
    """Display all books in the catalogue."""
    books = load_json("books.json")
    return render_template("catalogue/list.html", books=books)


@catalogue_bp.route("/search")
def search():
    """Search books by title, author, or genre."""
    query = request.args.get("q", "").lower()
    books = load_json("books.json")
    if query:
        books = [
            b for b in books
            if query in b.get("title", "").lower()
            or query in b.get("author", "").lower()
            or query in b.get("genre", "").lower()
        ]
    return render_template("catalogue/list.html", books=books, query=query)


@catalogue_bp.route("/<book_id>")
def book_detail(book_id):
    """Display a single book's details."""
    books = load_json("books.json")
    book = next((b for b in books if b["book_id"] == book_id), None)
    if not book:
        return render_template("shared/error.html", message="Book not found."), 404
    return render_template("catalogue/detail.html", book=book)