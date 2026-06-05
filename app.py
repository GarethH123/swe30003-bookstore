"""
app.py - Main Flask application entry point
SWE30003 - Assignment 3 - Online Bookstore
"""

from flask import Flask, render_template, session
import os

app = Flask(__name__)
app.secret_key = "swe30003-bookstore-secret-key"

@app.errorhandler(403)
def forbidden(e):
    return render_template("shared/error.html", message="Admin access only. Please log in as admin."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("shared/error.html", message="Page not found."), 404

from flask import render_template

@app.errorhandler(403)
def forbidden(e):
    return render_template("shared/error.html", message="Admin access only."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("shared/error.html", message="Page not found."), 404

# Register blueprints 
# Each team member adds their blueprint here once their file is ready.
# Until then, the import is commented out so the app still runs.

from blueprints.catalogue_routes import catalogue_bp
app.register_blueprint(catalogue_bp)

from blueprints.auth_routes import auth_bp
app.register_blueprint(auth_bp)

from blueprints.order_routes import order_bp
app.register_blueprint(order_bp)

from blueprints.shipment_routes import shipment_bp
app.register_blueprint(shipment_bp)

from blueprints.stats_routes import stats_bp
app.register_blueprint(stats_bp)


# Home route 
@app.route("/")
def index():
    return render_template("shared/index.html")


# Run 
if __name__ == "__main__":
    app.run(debug=True, port=8080)
