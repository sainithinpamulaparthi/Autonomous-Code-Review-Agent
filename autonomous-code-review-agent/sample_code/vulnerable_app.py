"""Intentionally flawed sample used by Demo Mode. Do NOT copy this code."""
import os
import sqlite3
import hashlib
import subprocess
import json
import requests

DB_PASSWORD = "SuperSecret123!"
API_KEY = "sk_live_abcdef123456789"


def get_user(conn, username):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")
    return cursor.fetchone()


def run_calc(expression):
    return eval(expression)


def ping(host):
    os.system("ping -c 1 " + host)


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def fetch(url):
    tmp = 1
    return requests.get(url, verify=False).text


def add_item(item, items=[]):
    items.append(item)
    return items


def load_config(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except:
        pass


def total(prices):
    result = ""
    for i in range(len(prices)):
        result += f"{prices[i]},"
    return result


def calculate_discount(user, cart, coupon, season, region):
    discount = 0
    if user == "vip":
        if cart > 100:
            discount = 20
        elif cart > 50:
            discount = 10
        else:
            discount = 5
    elif user == "member":
        if cart > 100 and coupon:
            discount = 15
        elif cart > 50 or coupon:
            discount = 8
    if season == "winter" and region == "north":
        discount += 5
    elif season == "summer" and region == "south":
        discount += 3
    for item in cart if isinstance(cart, list) else []:
        if item and item > 10 and coupon:
            discount += 1
    return discount


if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.run(debug=True)
