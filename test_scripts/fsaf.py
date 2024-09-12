import os
import sqlite3
most_common_match_code = 1
connection = sqlite3.connect('attendance.db')
cursor = connection.cursor()
cursor.execute('SELECT * FROM tabla_estudiantes')
lista_codigos = cursor.fetchall()


os.makedirs('../faces_databases/1000048001')
print(lista_codigos)