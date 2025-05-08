import sqlite3
from datetime import datetime
from tabulate import tabulate
DB_FILE = 'database.db'

def connect_db():
    db = sqlite3.connect(DB_FILE)
    initialize_database(db)
    return db

def initialize_database(db):
    create_table_query = """
        CREATE TABLE IF NOT EXISTS data_lora (
            datetime TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            frec TEXT NOT NULL,
            rssi TEXT NOT NULL,
            snr TEXT NOT NULL,
            payload TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
        );
    """
    cursor = db.cursor()
    cursor.execute(create_table_query)
    db.commit()

def save_sqlite(datetime, frec, rssi, snr, payload, published):
    db = connect_db()
    cursor = db.cursor()
    query = """INSERT INTO data_lora (datetime, frec, rssi, snr, payload, done)
               VALUES (?, ?, ?, ?, ?, ?)"""
    cursor.execute(query, (datetime, frec, rssi, snr, payload, published))
    db.commit()
    last_id = cursor.lastrowid
    db.close()
    print("Datos guardados en SQLite.")
    return last_id

def get_all_data():
    db = connect_db()
    cursor = db.cursor()
    query = "SELECT * FROM data_lora"
    cursor.execute(query)
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    db.close()

    print(tabulate(rows, headers=column_names, tablefmt="grid"))
    return rows

def get_unpublished_messages():
    db = connect_db()
    cursor = db.cursor()
    query = "SELECT datetime, frec, rssi, snr, payload FROM data_lora WHERE done = 0"
    cursor.execute(query)
    rows = cursor.fetchall()
    db.close()
    print("Mensajes sin publicar recuperados.")
    return rows

def delete_old_data():
    db = connect_db()
    cursor = db.cursor()
    count_query = "SELECT COUNT(*) FROM data_lora WHERE datetime(datetime) < datetime('now', '-1 month')"
    cursor.execute(count_query)
    count = cursor.fetchone()[0]
    print(f"🔍 Registros a eliminar: {count}")
    if count > 0:
        delete_query = "DELETE FROM data_lora WHERE datetime(datetime) < datetime('now', '-1 month')"
        cursor.execute(delete_query)
        db.commit()
        print(f"Se eliminaron {count} registros antiguos.")
    else:
        print("No hay registros antiguos para eliminar.")
    db.close()

def delete_all_data():
    db = connect_db()
    cursor = db.cursor()
    query = "DELETE FROM data_lora"
    cursor.execute(query)
    db.commit()
    db.close()
    print("Todos los datos han sido eliminados.")

