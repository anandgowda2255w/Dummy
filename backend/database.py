import sqlite3

DB_NAME = "database/manufacturing.db"

def get_connection():
    return sqlite3.connect(DB_NAME)