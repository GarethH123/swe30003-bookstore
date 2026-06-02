"""
storage.py - JSON file storage helpers for the Online Bookstore
SWE30003 - Assignment 3
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(filename: str) -> list:
    """Load a JSON data file and return its contents as a list."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str, data: list) -> None:
    """Save data to a JSON file."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def find_by_id(filename: str, id_field: str, value: str) -> dict | None:
    """Find a single record by its ID field."""
    records = load_json(filename)
    return next((r for r in records if r.get(id_field) == value), None)


def update_record(filename: str, id_field: str, value: str, updated: dict) -> bool:
    """Update a single record in a JSON file by ID. Returns True if found and updated."""
    records = load_json(filename)
    for i, record in enumerate(records):
        if record.get(id_field) == value:
            records[i] = updated
            save_json(filename, records)
            return True
    return False


def delete_record(filename: str, id_field: str, value: str) -> bool:
    """Delete a single record from a JSON file by ID. Returns True if found and deleted."""
    records = load_json(filename)
    filtered = [r for r in records if r.get(id_field) != value]
    if len(filtered) < len(records):
        save_json(filename, filtered)
        return True
    return False


def append_record(filename: str, record: dict) -> None:
    """Append a new record to a JSON file."""
    records = load_json(filename)
    records.append(record)
    save_json(filename, records)
