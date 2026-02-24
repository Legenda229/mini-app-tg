import os

BOT_TOKEN = "8321125645:AAFCoHwRm2gzgIVzB-C_qKXXV7eCLzXvPBE"

# Секретный ключ для API между ботом и сервером
API_SECRET = "joonix_secret_key_2024_change_me"

GOLD_PRICE = 0.67
MIN_GOLD = 100
MARKET_COMMISSION = 0.20
REQUIRED_SKIN = "M4 Flock"

TERMS_URL = "http://docs.google.com/document/d/1yjXpk6-H1sA4hkUCwutFBEwHv25--k1zBYZgH16i1Ok"
PRIVACY_URL = "http://docs.google.com/document/d/1o4LBBlGi1iy8omOh8c1bLSexxm4MeW3iW4PQZRBRt_A"

COMPENSATION_RULES = [
    {"min": 100, "max": 200, "gold": 5},
    {"min": 200, "max": 400, "gold": 7},
    {"min": 400, "max": 700, "gold": 10},
    {"min": 700, "max": 1000, "gold": 15},
    {"min": 1000, "max": 999999, "gold": 20},
]

REVIEW_CASHBACK_RULES = [
    {"min": 100, "max": 200, "gold": 5},
    {"min": 200, "max": 400, "gold": 7},
    {"min": 400, "max": 700, "gold": 10},
    {"min": 700, "max": 1000, "gold": 15},
    {"min": 1000, "max": 999999, "gold": 20},
]

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "joonix.db")
PORT = int(os.environ.get("PORT", 5000))
