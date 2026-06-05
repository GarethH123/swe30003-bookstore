"""
utils.py - Shared utility functions and decorators
SWE30003 - Assignment 3 - Online Bookstore
"""

from functools import wraps
from flask import session, redirect, url_for, abort


def admin_required(f):
    """
    Decorator that restricts a route to admin users only.

    Checks session['user_role'] == 'admin'.
    - If the user is not logged in at all  → redirect to login page.
    - If the user is logged in but not admin → abort with 403 Forbidden.

    Usage:
        @app.route("/admin/something")
        @admin_required
        def admin_something():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            # Not logged in — send to login
            return redirect(url_for("auth.login"))

        if session.get("user_role") != "admin":
            # Logged in, but not an admin
            abort(403)

        return f(*args, **kwargs)

    return decorated_function