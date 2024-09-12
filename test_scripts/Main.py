import sqlite3
import sys, os
import threading
import time
import sqlite3 as sql
import csv
from datetime import date
import pandas as pd
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import pyqtSignal, QThread, Qt, QTimer
from PyQt5.uic import loadUi
import cv2
from deepface import DeepFace
from collections import Counter
from VentanaRegistrar import *

DB_PATH = r'../utils/final_attendance.db'
REG_PATH = r'../registros'
fecha_actual = date.today()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.FaceVerificationThread = FaceVerificationThread()
        self.UpdateDateThread = UpdateDateThread()
        self.RegisterWindow = RegisterWindow(self)
        self.init_ui()

    def init_ui(self):
        loadUi('windows_skeletons/MainWindow.ui', self)

        self.FaceVerificationThread.start()
        self.FaceVerificationThread.image_update.connect(self.image_update_slot)
        self.FaceVerificationThread.student_data_update.connect(self.update_student_data_labels)

        self.UpdateDateThread.start()
        self.UpdateDateThread.date_update.connect(self.date_update_slot)

        self.actionRegistrarAlumno.triggered.connect(self.open_register_window)
        self.actionExportar.triggered.connect(self.export_to_csv)
        self.actionSalir.triggered.connect(self.close)

        self.RegisterWindow.backButton.clicked.connect(self.return_to_main_window)
        self.RegisterWindow.registerButton.clicked.connect(self.register_student)

    def image_update_slot(self, image):
        self.imageLabel.setPixmap(QPixmap.fromImage(image))

    def date_update_slot(self, date_now):
        self.timeNowLabel.setText(date_now)
        self.RegisterWindow.timeNowLabel.setText(date_now)

    def update_student_data_labels(self, code):
        with sqlite3.connect(DB_PATH) as connection:
            self.actualNameLabel.setText('------------------------')
            self.actualCodeLabel.setText('------------------------')
            self.actualNumberOfAttendanceLabel.setText('------------------------')
            self.actualNumberOfNoAttendanceLabel.setText('------------------------')
            self.actualLastAttendanceLabel.setText('------------------------')
            try:
                cursor = connection.cursor()
                cursor.execute('''
                                SELECT nombres, apellido_paterno, apellido_materno, codigo_matricula
                                FROM tabla_estudiantes
                                WHERE codigo_matricula = ?
                                ''', (code,))
                query_result_1 = cursor.fetchone()
                # print(query_result_1)

                cursor.execute('''
                                SELECT  COUNT(asistencia), CASE 
	                                WHEN asistencia = false Then 'NO'
	                                WHEN asistencia = true Then 'SI'
	                                END AS asistencias_inasistencias
                                FROM tabla_historial_asistencias
                                WHERE codigo_matricula = (
	                                SELECT codigo_matricula
	                                FROM tabla_estudiantes
	                                WHERE codigo_matricula = ?) 
                                GROUP BY asistencias_inasistencias
                ''', (code,))

                query_result_2 = cursor.fetchall()
                # print(query_result_2)

                cursor.execute('''
                                SELECT fecha_asistencia
                                FROM tabla_historial_asistencias
                                WHERE codigo_matricula = (
                                    SELECT codigo_matricula
                                    FROM tabla_estudiantes
                                    WHERE codigo_matricula = ?)
                                AND asistencia = true
                                ORDER BY fecha_asistencia DESC
                                LIMIT 1
                ''', (code,))

                query_result_3 = cursor.fetchone()
                # print(query_result_3)

                if query_result_1 is not None and query_result_2 is not None and query_result_3 is not None:
                    nombres, apellido_materno, apellido_paterno, codigo_matricula = query_result_1

                    for datos_asistencias in query_result_2:
                        if datos_asistencias[1] == 'NO':
                            numero_inasistencias = datos_asistencias[0]
                        if datos_asistencias[1] == 'SI':
                            numero_asistencias = datos_asistencias[0]

                    ultima_fecha_asistencia = query_result_3[0]

                    self.actualNameLabel.setText(f'{nombres} {apellido_paterno} {apellido_materno}')
                    self.actualCodeLabel.setText(str(codigo_matricula))
                    self.actualNumberOfAttendanceLabel.setText(str(numero_asistencias))
                    self.actualNumberOfNoAttendanceLabel.setText(str(numero_inasistencias))
                    self.actualLastAttendanceLabel.setText(ultima_fecha_asistencia)

            except Exception as e:
                print(e)
                pass

    def cancel_feed(self):
        self.FaceVerificationThread.stop()

    def resume_feed(self):
        self.FaceVerificationThread = FaceVerificationThread()
        self.FaceVerificationThread.start()
        self.FaceVerificationThread.image_update.connect(self.image_update_slot)
        self.FaceVerificationThread.student_data_update.connect(self.update_student_data_labels)

    def open_register_window(self):
        self.cancel_feed()
        self.hide()
        self.RegisterWindow.show()
        self.RegisterWindow.resume_feed()

    def return_to_main_window(self):
        self.RegisterWindow.cancel_feed()
        self.RegisterWindow.hide()
        self.show()
        self.resume_feed()

    def export_to_csv(self):

        # Retrieve information from database
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute('''SELECT DISTINCT fecha_asistencia 
                              FROM tabla_historial_asistencias 
                              ORDER BY fecha_asistencia''')
            fechas = [row[0] for row in cursor.fetchall()]
            fechas_columnas = []
            for fecha in fechas:
                fechas_columnas.append(
                    f"MAX(CASE WHEN tabla_historial_asistencias.fecha_asistencia = '{fecha}' THEN "
                    f"tabla_historial_asistencias.asistencia ELSE 0 END) AS '{fecha}'")

            fechas_columnas_sql = ",\n    ".join(fechas_columnas)

            consulta_sql = f"""
                            SELECT 
                                tabla_estudiantes.codigo_matricula,
                                tabla_estudiantes.apellido_paterno,
                                tabla_estudiantes.apellido_materno,
                                tabla_estudiantes.nombres,
                                {fechas_columnas_sql},
                                count(CASE WHEN tabla_historial_asistencias.asistencia = true Then 1 END) AS asistencia,
	                            count(CASE WHEN tabla_historial_asistencias.asistencia = false Then 0 END) AS inasistencia
                            FROM tabla_estudiantes
                            LEFT JOIN tabla_historial_asistencias 
                            ON tabla_estudiantes.codigo_matricula = tabla_historial_asistencias.codigo_matricula
                            GROUP BY 
                                tabla_estudiantes.codigo_matricula
                            ORDER BY 
                                tabla_estudiantes.codigo_matricula;
                            """

            cursor.execute(consulta_sql)
            query_result = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]

            # Save retrieved information into a Excel file
            nombre_excel = f'{fecha_actual}.xlsx'
            ruta_excel = os.path.join(REG_PATH, nombre_excel)

            if nombre_excel in os.listdir(REG_PATH):
                os.remove(ruta_excel)

            df = pd.DataFrame(query_result, columns=column_names)
            df.to_excel(ruta_excel, index=False, engine='openpyxl')

            msg = QMessageBox()
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle('Exportación')
            msg.setText(f'Exportación Exitosa {nombre_excel}')
            msg.exec_()

    def register_student(self):
        msg = QMessageBox()
        msg.setStandardButtons(QMessageBox.Ok)

        nombre_validado = False
        apellido_paterno_validado = False
        apellido_materno_validado = False
        codigo_numero_validado = False

        if self.RegisterWindow.nameInput.text() == '':
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle('Incompleto')
            msg.setText('Ingrese un nombre.')
            msg.exec_()
        else:
            nombre_validado = True

            if self.RegisterWindow.firstSurnameInput.text() == '':

                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle('Incompleto')
                msg.setText('Ingrese un apellido paterno.')
                msg.exec_()
            else:
                apellido_paterno_validado = True

                if self.RegisterWindow.secondSurnameInput.text() == '':
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle('Incompleto')
                    msg.setText('Ingrese un apellido materno.')
                    msg.exec_()
                else:
                    apellido_materno_validado = True

                    if self.RegisterWindow.codeInput.text() == '':
                        msg.setIcon(QMessageBox.Warning)
                        msg.setWindowTitle('Incompleto')
                        msg.setText('Ingrese un codigo de matrícula.')
                        msg.exec_()
                    else:
                        codigo_numero_validado = True

        validacion_completa = (nombre_validado
                               and apellido_paterno_validado
                               and apellido_materno_validado
                               and codigo_numero_validado)

        if validacion_completa:
            nombre = self.RegisterWindow.nameInput.text()
            apellido_paterno = self.RegisterWindow.firstSurnameInput.text()
            apellido_materno = self.RegisterWindow.secondSurnameInput.text()

            try:
                codigo_numero = int(self.RegisterWindow.codeInput.text())

                with sqlite3.connect(DB_PATH) as connection:
                    cursor = connection.cursor()
                    cursor.execute('SELECT codigo_matricula FROM tabla_estudiantes')
                    lista_codigos = cursor.fetchall()

                    if (codigo_numero,) in lista_codigos:
                        msg.setIcon(QMessageBox.Warning)
                        msg.setWindowTitle('Incompleto')
                        msg.setText('Alumno ya registrado.')
                        msg.exec_()

                    else:
                        cursor.execute('''INSERT INTO 
                                          tabla_estudiantes (nombres, 
                                                             apellido_paterno, 
                                                             apellido_materno,
                                                             codigo_matricula)
                                          VALUES (?, ?, ?, ?)
                        ''', (nombre, apellido_paterno, apellido_materno, codigo_numero))

                        # Guardar imagen en carpeta com codigo
                        image_folder = 'faces_databases/' + str(codigo_numero)
                        os.makedirs(image_folder, exist_ok=True)

                        # Crea el registro de asistencia del día en la tabla_historial_asistencias

                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle('Atención')
                        msg.setText('Presiona OK para tomar la primera foto')
                        msg.exec_()
                        self.RegisterWindow.image_feed_thread.capture_and_save_image(image_folder, 1)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle('Atención')
                        msg.setText('Presiona OK para tomar la segunda foto')
                        msg.exec_()
                        self.RegisterWindow.image_feed_thread.capture_and_save_image(image_folder, 2)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle('Atención')
                        msg.setText('Presiona OK para tomar la tercera foto')
                        msg.exec_()
                        self.RegisterWindow.image_feed_thread.capture_and_save_image(image_folder, 3)
                        msg.setIcon(QMessageBox.Information)
                        msg.setWindowTitle('Correcto')
                        msg.setText('Se registró correctamente el alumno.')
                        msg.exec_()

                        self.RegisterWindow.nameInput.clear()
                        self.RegisterWindow.firstSurnameInput.clear()
                        self.RegisterWindow.secondSurnameInput.clear()
                        self.RegisterWindow.codeInput.clear()

            except ValueError:
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle('Incompleto')
                msg.setText('Ingrese un codigo de matrícula válido.')
                msg.exec_()
                pass


class UpdateDateThread(QThread):
    date_update = pyqtSignal(str)

    def __init__(self):
        super(QThread, self).__init__()
        self.thread_active = False

    def run(self):
        self.thread_active = True

        while self.thread_active:
            global fecha_actual
            fecha_actual = date.today()
            hora_actual = time.strftime('%d/%m/%Y %H:%M:%S')
            self.date_update.emit(hora_actual)
            time.sleep(1)
            pass

    def stop(self):
        self.thread_active = False
        self.quit()


class FaceVerificationThread(QThread):
    image_update = pyqtSignal(QImage)
    student_data_update = pyqtSignal(int)

    def __init__(self):
        super(QThread, self).__init__()
        self.counter = 0
        self.name = 'unknown'
        self.code = 0000
        self.IMAGE_DB_PATH = '../faces_databases'
        self.thread_active = False

    def run(self):
        self.thread_active = True
        Capture = cv2.VideoCapture(0)

        def check_face(face_image):
            try:
                df = pd.DataFrame(DeepFace.find(
                    face_image,
                    db_path=self.IMAGE_DB_PATH,
                    silent=True,
                    enforce_detection=False)[:][:][0])
                student_codes = []

                for n in df[df.columns[0]]:
                    student_codes.append(os.path.split(os.path.split(n)[0])[1])

                most_common_match_name = 'unknown'
                most_common_match_code = 0000000000000000000000000
                matches = Counter(student_codes).most_common(n=1)

                if matches:
                    most_common_match_code = matches[0][0]
                    # print(most_common_match_code)

                connection = sqlite3.connect(DB_PATH)
                cursor = connection.cursor()
                cursor.execute('''
                                SELECT nombres, apellido_materno, apellido_paterno
                                FROM tabla_estudiantes
                                WHERE codigo_matricula = ?
                ''', (most_common_match_code,))

                query_result = cursor.fetchone()

                if query_result is not None:
                    nombres, apellido_materno, apellido_paterno = query_result
                    most_common_match_name = f'{nombres} {apellido_paterno} {apellido_materno}'
                    cursor.execute('''
                                    UPDATE tabla_historial_asistencias
                                    SET asistencia = true
                                    WHERE codigo_matricula = (
                                        SELECT codigo_matricula
                                        FROM tabla_estudiantes
                                        WHERE codigo_matricula = ?)
                                    AND fecha_asistencia = ?
                    ''', (most_common_match_code, fecha_actual))
                    connection.commit()

                return most_common_match_name, int(most_common_match_code)

            except ValueError:
                pass

            except sqlite3.Error:
                pass

            except Exception as e:
                print(e)
                pass

        while self.thread_active:
            ret, frame = Capture.read()

            if ret:
                zoom_factor = 1.5
                height, width, _ = frame.shape
                if width > height:
                    # Si la imagen es más ancha, recortar el ancho
                    new_dim = height
                else:
                    # Si la imagen es más alta, recortar el alto
                    new_dim = width

                # Aplicar zoom (ajustar el área de recorte según el factor de zoom)
                zoomed_dim = int(new_dim / zoom_factor)

                # Calcular el centro y los márgenes para el recorte
                x1 = max((width - zoomed_dim) // 2, 0)
                y1 = max((height - zoomed_dim) // 2, 0)
                x2 = min((width + zoomed_dim) // 2, width)
                y2 = min((height + zoomed_dim) // 2, height)

                # Recortar la imagen para mantener el ratio 1:1 con zoom
                cropped_frame = frame[y1:y2, x1:x2]

                # Redimensionar la imagen recortada para que coincida con la resolución original
                resized_frame = cv2.resize(cropped_frame, (new_dim, new_dim))

                if self.counter % 30 == 0:
                    try:
                        self.name, self.code = check_face(resized_frame.copy())
                    except ValueError:
                        pass

                Image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                FlippedImage = cv2.flip(Image, 1)

                if self.name == 'unknown':
                    cv2.putText(FlippedImage,
                                'No identificado',
                                (20, 450),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1,
                                (255, 0, 0),
                                3)
                else:
                    cv2.putText(FlippedImage,
                                str(self.name),
                                (20, 450),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1,
                                (0, 255, 0),
                                3)

                ConvertToQtFormat = QImage(FlippedImage.data,
                                           FlippedImage.shape[1],
                                           FlippedImage.shape[0],
                                           QImage.Format_RGB888)
                Pic = ConvertToQtFormat.scaled(480, 480, Qt.KeepAspectRatio)
                self.image_update.emit(Pic)
                self.student_data_update.emit(self.code)
                self.counter += 1

        Capture.release()

    def stop(self):
        self.thread_active = False
        self.quit()


if __name__ == '__main__':
    DeepFace.find('../utils/test.png', db_path='faces_databases', enforce_detection=False)
    try:
        App = QApplication(sys.argv)
        Root = MainWindow()
        Root.show()
        sys.exit(App.exec_())
    except Exception as e:
        print(e)