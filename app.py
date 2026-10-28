
import sys

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ClipFlowWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ClipFlow - Video Downloader")
        self.resize(850, 580)
        self.setMinimumSize(700, 500)

        self.download_folder = ""

        self.create_interface()
        self.apply_styles()

    def create_interface(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(18)

        # Encabezado
        header = QHBoxLayout()

        logo = QLabel("CF")
        logo.setObjectName("logo")

        title = QLabel("ClipFlow")
        title.setObjectName("app_title")

        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()

        version = QLabel("v0.1.0")
        version.setObjectName("muted")
        header.addWidget(version)

        main_layout.addLayout(header)

        # Título principal
        heading = QLabel("Descarga tus videos")
        heading.setObjectName("heading")

        description = QLabel(
            "Pega un enlace de una plataforma compatible "
            "para comenzar."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)

        main_layout.addWidget(heading)
        main_layout.addWidget(description)

        # Campo de enlace
        url_label = QLabel("Enlace del video")

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Pega aquí la URL del video..."
        )

        self.url_input.setClearButtonEnabled(True)

        self.analyze_button = QPushButton("Analizar enlace")
        self.analyze_button.setObjectName("primary_button")
        self.analyze_button.clicked.connect(self.analyze_url)

        main_layout.addWidget(url_label)
        main_layout.addWidget(self.url_input)
        main_layout.addWidget(self.analyze_button)

        # Formato
        format_label = QLabel("Formato de descarga")

        self.format_combo = QComboBox()
        self.format_combo.addItems(
            [
                "Video con mejor calidad disponible",
                "Solo audio",
            ]
        )

        main_layout.addWidget(format_label)
        main_layout.addWidget(self.format_combo)

        # Carpeta de destino
        folder_label = QLabel("Carpeta de descarga")

        folder_layout = QHBoxLayout()

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(
            "Selecciona una carpeta de destino..."
        )
        self.folder_input.setReadOnly(True)

        browse_button = QPushButton("Elegir carpeta")
        browse_button.clicked.connect(self.choose_folder)

        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)

        main_layout.addWidget(folder_label)
        main_layout.addLayout(folder_layout)

        # Estado
        self.status_label = QLabel(
            "Listo para comenzar."
        )
        self.status_label.setObjectName("status")

        main_layout.addStretch()
        main_layout.addWidget(self.status_label)

        self.setCentralWidget(central_widget)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de descarga",
        )

        if folder:
            self.download_folder = folder
            self.folder_input.setText(folder)

    def analyze_url(self):
        url = self.url_input.text().strip()

        if not url:
            QMessageBox.warning(
                self,
                "Enlace requerido",
                "Pega el enlace de un video antes de continuar.",
            )
            return

        if not url.startswith(("https://", "http://")):
            QMessageBox.warning(
                self,
                "Enlace no válido",
                "El enlace debe comenzar con https:// o http://.",
            )
            return

        QMessageBox.information(
            self,
            "Interfaz en desarrollo",
            "El enlace tiene un formato básico válido.\n\n"
            "En la siguiente etapa conectaremos el motor "
            "de yt-dlp para analizar videos compatibles.",
        )

        self.status_label.setText(
            "Enlace introducido. Descargas aún no habilitadas."
        )

    def apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #172033;
                color: #E8EEF8;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            QLabel#logo {
                background-color: #3984F6;
                color: white;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                min-width: 42px;
                max-width: 42px;
                min-height: 42px;
                max-height: 42px;
                qproperty-alignment: AlignCenter;
            }

            QLabel#app_title {
                font-size: 23px;
                font-weight: bold;
            }

            QLabel#heading {
                font-size: 27px;
                font-weight: bold;
            }

            QLabel#muted {
                color: #A8B6CC;
            }

            QLabel#status {
                color: #9CC2FF;
                padding-top: 10px;
            }

            QLineEdit, QComboBox {
                background-color: #253149;
                color: #FFFFFF;
                border: 1px solid #44536D;
                border-radius: 7px;
                padding: 11px;
                min-height: 20px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3984F6;
            }

            QPushButton {
                background-color: #303E56;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                padding: 11px 16px;
                min-height: 20px;
            }

            QPushButton:hover {
                background-color: #40516D;
            }

            QPushButton#primary_button {
                background-color: #3984F6;
                font-weight: bold;
            }

            QPushButton#primary_button:hover {
                background-color: #5796FF;
            }

            QMessageBox {
                background-color: #172033;
            }
            """
        )


def main():
    app = QApplication(sys.argv)

    window = ClipFlowWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
