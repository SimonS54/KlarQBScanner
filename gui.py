import sys
import pytesseract
import pyautogui
import threading
import time
import pyperclip
import keyboard
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QColor
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
import pygetwindow as gw
import winsound
from fuzzywuzzy import fuzz

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust the path if necessary

class OCRWorker(threading.Thread):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                screenshot = pyautogui.screenshot()
                screenshot = screenshot.convert('L')  # Convert to grayscale
                text = pytesseract.image_to_string(screenshot)

                error = self.extract_info(text, "Error =")
                qb_link = self.extract_info(text, "QB =")
                qb_id = self.extract_info(text, "QB ID =")
                product = self.extract_product(text)

                if all([error, qb_link, qb_id, product]):
                    browser_link = self.get_current_browser_url()
                    message = f"/qbissue product: {product} ticket_link: {browser_link} qb_link: {qb_link} issue: {error} qb_id: {qb_id}"
                    self.callback(message)  # Send result back to main thread
                    break  # Stop the loop once all information is found
                time.sleep(0.5)  # Adjust the delay as needed for performance
            except Exception as e:
                print(f"Error during OCR processing: {e}")

    def stop(self):
        self.running = False

    def extract_info(self, text, label):
        lines = text.split('\n')
        for line in lines:
            if label in line:
                return line.split(label)[1].strip()
        return None

    def extract_product(self, text):
        products = {
            "R6 Full": ["r6 full", "rainbow six full", "rainbow full"],
            "R6 Lite": ["r6 lite", "rainbow six lite", "rainbow lite", "lite"],
            "XDefiant": ["xdefiant", "xd", "defiant"]
        }

        text = text.lower()
        best_match = ("r6_full", 0)  # Default to "r6_full"

        for product, aliases in products.items():
            for alias in aliases:
                match_ratio = fuzz.partial_ratio(alias, text)
                if match_ratio > best_match[1]:
                    best_match = (product, match_ratio)

        # Set a minimum threshold to avoid false positives
        if best_match[1] > 70:  # Adjust the threshold as necessary
            return best_match[0]
        else:
            return "r6_full"  # Default if no suitable product found

    def get_current_browser_url(self):
        try:
            windows = gw.getAllTitles()
            print("Available Windows:")
            for w in windows:
                print(w)

            window = None
            for w in gw.getWindowsWithTitle('Opera'):
                if 'Opera' in w.title:
                    window = w
                    break

            if window is None:
                raise Exception("Opera window not found")

            window.activate()
            pyautogui.hotkey('ctrl', 'l')
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.05)  # Reduced delay

            url = pyperclip.paste()
            return url
        except Exception as e:
            print(f"Error retrieving browser URL: {e}")
            return "https://forum.klar.gg/admin/?app=nexus&module=support&controller=request&id=26074"

class CustomTitleBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CustomTitleBar, self).__init__(parent)
        self.parent = parent
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QtGui.QPalette.Window)
        self.initUI()

    def initUI(self):
        self.setFixedHeight(40)
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        self.setLayout(layout)

        self.titleLabel = QtWidgets.QLabel("QuickBuild Auto Scanner")
        self.titleLabel.setStyleSheet("color: white; font: bold 14px;")
        layout.addWidget(self.titleLabel)

        layout.addStretch()

        self.minimizeButton = QtWidgets.QPushButton("-")
        self.minimizeButton.setFixedSize(40, 40)
        self.minimizeButton.setStyleSheet(
            "QPushButton { background-color: transparent; border-image: url(minimize.png); color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #4a4a4a; }"
        )
        self.minimizeButton.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.minimizeButton)

        self.closeButton = QtWidgets.QPushButton("X")
        self.closeButton.setFixedSize(40, 40)
        self.closeButton.setStyleSheet(
            "QPushButton { background-color: transparent; border-image: url(close.png); color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #ff5555; }"
        )
        self.closeButton.clicked.connect(self.parent.close)
        layout.addWidget(self.closeButton)

        self.old_pos = None

        palette = self.palette()
        palette.setColor(QPalette.Background, QColor('#181c34'))
        self.setPalette(palette)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPos() - self.old_pos
            self.parent.move(self.parent.pos() + delta)
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker = None
        self.start_sound = 'start.wav'
        self.stop_sound = 'stop.wav'

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setGeometry(100, 100, 400, 300)

        self.titleBar = CustomTitleBar(self)
        centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(centralWidget)

        layout = QtWidgets.QVBoxLayout(centralWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.titleBar)

        content = QtWidgets.QWidget()
        contentLayout = QtWidgets.QVBoxLayout(content)
        layout.addWidget(content)

        palette = self.palette()
        palette.setColor(QPalette.Background, QColor('#181c34'))
        self.setPalette(palette)

        appIcon = QtGui.QIcon('icon.ico')
        self.setWindowIcon(appIcon)

        image_path = 'image.png'
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaled(100, 100, QtCore.Qt.KeepAspectRatio)

        self.logoLabel = QtWidgets.QLabel()
        self.logoLabel.setPixmap(pixmap)
        contentLayout.addWidget(self.logoLabel, alignment=QtCore.Qt.AlignCenter)

        self.usernameLabel = QtWidgets.QLabel("Hotkey:")
        self.usernameLabel.setStyleSheet("color: white;")
        contentLayout.addWidget(self.usernameLabel, alignment=QtCore.Qt.AlignCenter)

        self.hotkeyField = QtWidgets.QLineEdit()
        contentLayout.addWidget(self.hotkeyField, alignment=QtCore.Qt.AlignCenter)

        self.setButton = QtWidgets.QPushButton("Set!")
        self.setButton.clicked.connect(self.set_hotkey)
        contentLayout.addWidget(self.setButton, alignment=QtCore.Qt.AlignCenter)

        self.create_tray_icon()
        self.show()

    def set_hotkey(self):
        self.hotkey = self.hotkeyField.text()
        if self.hotkey:
            keyboard.add_hotkey(self.hotkey, self.toggle_scan)
            QtWidgets.QMessageBox.information(self, "Hotkey Set", f'Hotkey "{self.hotkey}" has been set!')

    def toggle_scan(self):
        if self.worker and self.worker.running:
            self.worker.stop()
            self.worker = None
            self.play_stop_sound()
        else:
            self.worker = OCRWorker(self.handle_result)
            self.worker.start()
            self.play_start_sound()

    def handle_result(self, message):
        print(message)
        pyperclip.copy(message)

    def create_tray_icon(self):
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setIcon(QIcon('image.png'))
        self.trayIcon.setToolTip("QuickBuild Auto Scanner")

        showAction = QAction("Show", self)
        showAction.triggered.connect(self.showNormal)

        quitAction = QAction("Quit", self)
        quitAction.triggered.connect(self.close)

        trayMenu = QMenu()
        trayMenu.addAction(showAction)
        trayMenu.addAction(quitAction)

        self.trayIcon.setContextMenu(trayMenu)
        self.trayIcon.show()

    def play_start_sound(self):
        winsound.Beep(500, 200)

    def play_stop_sound(self):
        winsound.Beep(300, 200)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = App()
    sys.exit(app.exec_())
