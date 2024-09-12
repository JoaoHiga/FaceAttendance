import os
import time

import cv2
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
        self.face_cascade = cv2.CascadeClassifier('utils/haarcascade_frontalface_default.xml')

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
        if self.current_image is not None:
            image_path = os.path.join(folder_path, str(image_number) + '.png')
            gray = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2GRAY)

            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                x, y, w, h = faces[0]
                face_roi = self.current_image[y:y + h, x:x + w]
                cv2.imwrite(image_path, face_roi)
                time.sleep(0.5)

    def stop(self):
        self.thread_active = False
        self.quit()
        self.wait()
