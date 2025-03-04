import os
import time

import cv2
import dlib
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi


class RegisterWindow(QMainWindow):
    def __init__(self, main_window):
        super(RegisterWindow, self).__init__()
        self.main_window = main_window
        self.image_feed_thread = ImageFeedThread()
        self.init_ui()

    def init_ui(self):
        loadUi('windows_skeletons/RegisterWindow.ui', self)

        self.image_feed_thread.image_update.connect(self.image_update_slot)

        logoPixmap = QPixmap('windows_skeletons/logomecat_resized.png')
        self.logoLabel.setPixmap(logoPixmap)

    def closeEvent(self, event):
        self.main_window.return_to_main_window()
        event.ignore()
        self.hide()

    def image_update_slot(self, image):
        self.imageLabel.setPixmap(QPixmap.fromImage(image))

    def resume_feed(self):
        self.image_feed_thread = ImageFeedThread()
        self.image_feed_thread.start()
        self.image_feed_thread.image_update.connect(self.image_update_slot)

    def cancel_feed(self):
        self.image_feed_thread.stop()
        self.image_feed_thread.wait()


class ImageFeedThread(QThread):
    image_update = pyqtSignal(QImage)

    def __init__(self):
        super(QThread, self).__init__()
        self.current_image = None
        self.thread_active = False

    def run(self):
        self.thread_active = True
        Capture = cv2.VideoCapture(cv2.CAP_DSHOW)

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

                Image = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                FlippedImage = cv2.flip(Image, 1)
                self.current_image = FlippedImage.copy()

                ConvertToQtFormat = QImage(FlippedImage.data,
                                           FlippedImage.shape[1],
                                           FlippedImage.shape[0],
                                           self.current_image.shape[1] * 3,
                                           QImage.Format_RGB888)
                Pic = ConvertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
                self.image_update.emit(Pic)

        Capture.release()

    def capture_and_save_image(self, folder_path, image_number):
        try:
            if self.current_image is None:
                raise ValueError("No hay imagen disponible para procesar.")

            model_file = "utils/mmod_human_face_detector.dat"

            if not os.path.exists(model_file):
                raise FileNotFoundError("Archivo del modelo DNN no encontrado. Verifica la ruta.")

            detector = dlib.get_frontal_face_detector()

            os.makedirs(folder_path, exist_ok=True)

            image_path = os.path.join(folder_path, f'{image_number}.jpg')

            rgb_image = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)

            faces = detector(rgb_image)

            if len(faces) == 0:
                print("No se detectaron rostros.")
                return

            face = faces[0]
            x, y, w, h = (face.left(), face.top(), face.right(), face.bottom())

            face_roi = self.current_image[y:h, x:w]

            scale_percent = 70  # Cambia este valor según sea necesario
            new_width = int(face_roi.shape[1] * scale_percent / 100)
            new_height = int(face_roi.shape[0] * scale_percent / 100)
            resized_face_roi = cv2.resize(face_roi, (new_width, new_height))

            quality = 100  # Calidad de compresión entre 0 y 100
            success = cv2.imwrite(image_path, resized_face_roi, [cv2.IMWRITE_JPEG_QUALITY, quality])

            if success:
                print(f"Imagen guardada exitosamente en {image_path}")
            else:
                print(f"No se pudo guardar la imagen en {image_path}")

            time.sleep(0.5)

        except FileNotFoundError as e:
            print(f"Error: {e}")
        except ValueError as e:
            print(f"Error: {e}")
        except cv2.error as e:
            print(f"Error de OpenCV: {e}")
        except dlib.error as e:
            print(f"Error de dlib: {e}")
        except Exception as e:
            print(f"Se produjo un error inesperado: {e}")

    def stop(self):
        self.thread_active = False
        self.quit()
        self.wait()
