
import sys

import yt_dlp

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
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


class WorkerSignals(QObject):
    # Señales para comunicar el resultado del hilo a la interfaz.
    result = Signal(dict)
    error = Signal(str)
    finished = Signal()


class VideoAnalyzer(QRunnable):
    """Analiza un enlace sin bloquear la interfaz gráfica."""

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = WorkerSignals()

    def run(self):
        try:
            options = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "socket_timeout": 20,
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(self.url, download=False)

            if not info:
                raise ValueError(
                    "No se pudo obtener información del enlace."
                )

            video_data = {
                "title": info.get("title") or "Título desconocido",
                "duration": info.get("duration"),
                "platform": (
                    info.get("extractor_key")
                    or info.get("extractor")
                    or "Desconocida"
                ),
                "uploader": info.get("uploader") or "No disponible",
                "formats": len(info.get("formats") or []),
            }

            self.signals.result.emit(video_data)

        except Exception as exc:
            self.signals.error.emit(str(exc))

        finally:
            self.signals.finished.emit()


class ClipFlowWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ClipFlow - Video Downloader")
        self.resize(850, 650)
        self.setMinimumSize(700, 550)

        self.download_folder = ""
        self.thread_pool = QThreadPool()
        self.current_worker = None

        self.create_interface()
        self.apply_styles()

    def create_interface(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(15)

        # Encabezado
        header = QHBoxLayout()

        logo = QLabel("CF")
        logo.setObjectName("logo")

        title = QLabel("ClipFlow")
        title.setObjectName("app_title")

        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()

        version = QLabel("v0.2.0")
        version.setObjectName("muted")
        header.addWidget(version)

        main_layout.addLayout(header)

        # Presentación
        heading = QLabel("Descarga tus videos")
        heading.setObjectName("heading")

        description = QLabel(
            "Pega un enlace compatible para consultar "
            "la información del contenido."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)

        main_layout.addWidget(heading)
        main_layout.addWidget(description)

        # URL
        main_layout.addWidget(QLabel("Enlace del video"))

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Pega aquí la URL del video..."
        )
        self.url_input.setClearButtonEnabled(True)

        self.analyze_button = QPushButton("Analizar enlace")
        self.analyze_button.setObjectName("primary_button")
        self.analyze_button.clicked.connect(self.analyze_url)

        main_layout.addWidget(self.url_input)
        main_layout.addWidget(self.analyze_button)

        # Formato (la descarga se implementará después)
        main_layout.addWidget(QLabel("Formato de descarga"))

        self.format_combo = QComboBox()
        self.format_combo.addItems(
            [
                "Video con mejor calidad disponible",
                "Solo audio",
            ]
        )
        self.format_combo.setEnabled(False)

        main_layout.addWidget(self.format_combo)

        # Carpeta de destino
        main_layout.addWidget(QLabel("Carpeta de descarga"))

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

        main_layout.addLayout(folder_layout)

        # Información del contenido
        self.result_label = QLabel(
            "La información del contenido aparecerá aquí."
        )
        self.result_label.setObjectName("result")
        self.result_label.setWordWrap(True)

        main_layout.addWidget(self.result_label)

        # Estado
        self.status_label = QLabel("Listo para comenzar.")
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

        self.analyze_button.setEnabled(False)
        self.result_label.setText("Analizando el enlace...")
        self.status_label.setText(
            "Consultando información. Espera un momento..."
        )

        worker = VideoAnalyzer(url)
        self.current_worker = worker

        worker.signals.result.connect(self.show_result)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.analysis_finished)

        self.thread_pool.start(worker)

    def show_result(self, data):
        seconds = data["duration"]

        if seconds is None:
            duration_text = "No disponible"
        else:
            seconds = int(seconds)
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours:
                duration_text = (
                    f"{hours:02}:{minutes:02}:{seconds:02}"
                )
            else:
                duration_text = f"{minutes:02}:{seconds:02}"

        self.result_label.setText(
            f"Título: {data['title']}\n"
            f"Plataforma: {data['platform']}\n"
            f"Canal o autor: {data['uploader']}\n"
            f"Duración: {duration_text}\n"
            f"Formatos detectados: {data['formats']}"
        )

        self.status_label.setText(
            "Análisis completado. Descargas aún no habilitadas."
        )

    def show_error(self, message):
        self.result_label.setText(
            "No fue posible obtener la información."
        )
        self.status_label.setText(
            "El análisis falló. Revisa el enlace y tu conexión."
        )

        print(f"Error de yt-dlp: {message}")

    def analysis_finished(self):
        self.analyze_button.setEnabled(True)
        self.current_worker = None

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

            QLabel#result {
                background-color: #202C42;
                border: 1px solid #34445F;
                border-radius: 8px;
                padding: 14px;
            }

            QLabel#status {
                color: #9CC2FF;
                padding-top: 8px;
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

            QComboBox:disabled {
                color: #8290A6;
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

            QPushButton:disabled {
                background-color: #30394A;
                color: #8A96A8;
            }

            QPushButton#primary_button {
                background-color: #3984F6;
                font-weight: bold;
            }

            QPushButton#primary_button:hover {
                background-color: #5796FF;
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
