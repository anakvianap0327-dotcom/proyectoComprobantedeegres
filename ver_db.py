import sqlite3

conexion = sqlite3.connect("database.db")
cursor = conexion.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tablas = cursor.fetchall()

print("TABLAS:")
print(tablas)

for tabla in tablas:
    nombre = tabla[0]
    print("\nTabla:", nombre)

    cursor.execute(f"SELECT * FROM {nombre}")
    registros = cursor.fetchall()

    for r in registros:
        print(r)

conexion.close()