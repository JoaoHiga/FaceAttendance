import sqlite3
from datetime import date

# Conectar a la base de datos (o crearla si no existe)
conn = sqlite3.connect('../attendance.db')
cursor = conn.cursor()

# # Crear la tabla de historial de asistencias si no existe
# cursor.execute('DROP TABLE tabla_historial_asistencias ')
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS "tabla_historial_asistencias" (
#     "id_asistencia" INTEGER NOT NULL UNIQUE,
#     "id_estudiantes" INTEGER,
#     "fecha_asistencia" DATE,
#     "asistencia" BOOLEAN,
#     PRIMARY KEY("id_asistencia"),
#     FOREIGN KEY ("id_estudiantes") REFERENCES "tabla_estudiantes"("id_estudiante")
#     ON UPDATE NO ACTION ON DELETE NO ACTION
# );
# ''')

cursor.execute("""
                                SELECT fecha_asistencia
FROM tabla_historial_asistencias
WHERE id_estudiante = (
	SELECT id_estudiante
	FROM tabla_estudiantes
	WHERE codigo_matricula = ?) 
AND asistencia = false
ORDER BY fecha_asistencia DESC
LIMIT 1
                """, (1000000001, ))

# # Obtener todos los id_estudiante de la tabla_estudiantes
# cursor.execute('SELECT id_estudiante FROM tabla_estudiantes')
# estudiantes = cursor.fetchall()
#
#
# # # Insertar un registro en tabla_historial_asistencias para cada estudiante
# fecha_actual = "2024-08-12"
#
# for estudiante in estudiantes:
#     id_estudiante = estudiante[0]
#     cursor.execute('''
#     INSERT INTO tabla_historial_asistencias (id_estudiante, fecha_asistencia, asistencia)
#     VALUES (?, ?, ?)
#     ''', (id_estudiante, fecha_actual, 0))
#
# # Guardar (commit) los cambios y cerrar la conexión
# conn.commit()

commit = cursor.fetchone()

# for datos_asistencias in commit:
#     if datos_asistencias[1] == 'NO':
#         numero_inasistencias = datos_asistencias[0]
#         print(numero_inasistencias)
#     if datos_asistencias[1] == 'SI':
#         numero_asistencias = datos_asistencias[0]
#         print(numero_asistencias)

print(commit)
conn.close()
