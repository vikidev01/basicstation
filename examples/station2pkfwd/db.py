import sqlite3
from tabulate import tabulate
from datetime import datetime
DB_FILE = 'database.db'

def connect_db():
    return sqlite3.connect(DB_FILE)

def initialize_database():
    db = connect_db()
    cursor = db.cursor()

    # Tabla de dispositivos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deveui TEXT NOT NULL UNIQUE
        );
    """)

    # Tabla de mensajes generales
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            datetime TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
            frec TEXT NOT NULL,
            rssi TEXT NOT NULL,
            snr TEXT NOT NULL,
            fcnt TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES device(id)
        );
    """)

    # Tabla GNSS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gnss (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            timestamp_scan TEXT NOT NULL,
            status TEXT NOT NULL,
            payload TEXT NOT NULL,
            FOREIGN KEY (message_id) REFERENCES message(id)
        );
    """)

    # Tabla WiFi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wifi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            timestamp_scan TEXT NOT NULL,
            balizas TEXT NOT NULL,
            FOREIGN KEY (message_id) REFERENCES message(id)
        );
    """)

    # Tabla Status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            battery TEXT,
            energy TEXT,
            millisec_in_charge TEXT,
            flag_status TEXT,
            cant_reset TEXT,
            temp TEXT,
            FOREIGN KEY (message_id) REFERENCES message(id)
        );
    """)

    db.commit()
    db.close()
    print("Base de datos inicializada correctamente.")

def insert_device_if_not_exists(deveui):
    db = connect_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM device WHERE deveui = ?", (deveui,))
    result = cursor.fetchone()
    
    if result:
        device_id = result[0]
    else:
        cursor.execute("INSERT INTO device (deveui) VALUES (?)", (deveui,))
        db.commit()
        device_id = cursor.lastrowid

    db.close()
    return device_id

def insert_message(deveui, datetime, frec, rssi, snr, fcnt):
    device_id = insert_device_if_not_exists(deveui)
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO message (device_id, datetime, frec, rssi, snr, fcnt)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (device_id, datetime, frec, rssi, snr, fcnt))
    
    db.commit()
    message_id = cursor.lastrowid
    db.close()
    return message_id

def insert_gnss(message_id, timestamp_scan, status, payload):
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO gnss (message_id, timestamp_scan, status, payload)
        VALUES (?, ?, ?, ?)
    """, (message_id, timestamp_scan, status, payload))

    db.commit()
    db.close()

def insert_wifi(message_id, timestamp_scan, balizas):
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO wifi (message_id, timestamp_scan, balizas)
        VALUES (?, ?, ?)
    """, (message_id, timestamp_scan, balizas))

    db.commit()
    db.close()

def insert_status(message_id, battery, energy, millisec_in_charge, flag_status, cant_reset, temp):
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO status (
            message_id, battery, energy, millisec_in_charge,
            flag_status, cant_reset, temp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message_id, battery, energy, millisec_in_charge, flag_status, cant_reset, temp))

    db.commit()
    db.close()

def get_all_devices():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM device")
    rows = cursor.fetchall()
    db.close()
    print("Dispositivos:")
    print(tabulate(rows, headers=["id", "deveui"], tablefmt="grid"))
    return rows

def get_all_messages():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT m.id, d.deveui, m.datetime, m.frec, m.rssi, m.snr, m.fcnt
        FROM message m
        JOIN device d ON m.device_id = d.id
        ORDER BY m.datetime DESC
    """)
    rows = cursor.fetchall()
    db.close()
    print("Mensajes:")
    print(tabulate(rows, headers=["id", "deveui", "datetime", "frec", "rssi", "snr", "fcnt"], tablefmt="grid"))
    return rows

def get_all_gnss():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT g.id, g.message_id, g.timestamp_scan, g.status, g.payload
        FROM gnss g
        ORDER BY g.timestamp_scan DESC
    """)
    rows = cursor.fetchall()
    db.close()
    print("GNSS:")
    print(tabulate(rows, headers=["id", "message_id", "timestamp_scan", "status", "payload"], tablefmt="grid"))
    return rows

def get_all_wifi():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT w.id, w.message_id, w.timestamp_scan, w.balizas
        FROM wifi w
        ORDER BY w.timestamp_scan DESC
    """)
    rows = cursor.fetchall()
    db.close()
    print("WiFi:")
    print(tabulate(rows, headers=["id", "message_id", "timestamp_scan", "balizas"], tablefmt="grid"))
    return rows

def get_all_status():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.id, s.message_id, s.battery, s.energy, s.millisec_in_charge,
               s.flag_status, s.cant_reset, s.temp
        FROM status s
        ORDER BY s.id DESC
    """)
    rows = cursor.fetchall()
    db.close()
    print("Status:")
    print(tabulate(rows, headers=[
        "id", "message_id", "battery", "energy", "millisec_in_charge",
        "flag_status", "cant_reset", "temp"
    ], tablefmt="grid"))
    return rows

def clear_all_tables_and_reset_ids():
    db = connect_db()
    cursor = db.cursor()

    # Borrado en orden para respetar claves foráneas
    cursor.execute("DELETE FROM status;")
    cursor.execute("DELETE FROM wifi;")
    cursor.execute("DELETE FROM gnss;")
    cursor.execute("DELETE FROM message;")
    cursor.execute("DELETE FROM device;")

    # Reiniciar los contadores AUTOINCREMENT
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='status';")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='wifi';")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='gnss';")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='message';")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='device';")

    db.commit()
    db.close()
    print("Tablas vaciadas y contadores reiniciados correctamente.")


# Llamar a la función si se ejecuta directamente
if __name__ == '__main__':
    #initialize_database()
    
    #get_all_devices()
    #clear_all_tables_and_reset_ids()
    get_all_messages()
    #get_all_gnss()
    #get_all_wifi()
    #get_all_status()
