import sqlite3
import os
DATA_BASE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'accounts_info2.sqlite')



    
try:   
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS Accounts ( id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL, prefered_name TEXT, email TEXT NOT NULL, phone_number TEXT, password TEXT NOT NULL, language TEXT NOT NULL, level TEXT NOT NULL, age INTEGER NOT NULL)')
except sqlite3.Error as e:
    print(f"SQLite error: {e}")
finally:
    connection.close()
