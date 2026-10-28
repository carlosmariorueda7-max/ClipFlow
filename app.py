
import sys
import shutil
from pathlib import Path

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
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class WorkerSignals(QObject):
    result = Signal(dict)
    error = Signal(str)
    progress = Signal(int, str)
    finished = Signal()


class VideoAnalyzer(QRunnable):
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
                info = ydl.extract_info(
                    self.url,
                    download=False,
                )

            if not info:
                raise ValueError("No se obtuvo información.")

            data = {
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

            self.signals.result.emit(data)

        except Exception as exc:
            self.signals.error.emit(str(exc))

        finally:
            self.signals.finished.emit()


class VideoDownloader(QRunnable):
    """Descarga contenido en segundo plano."""

    def __init__(self, url, folder, audio_only):
        super().__init__()

        self.url = url
        self.folder = folder
        self.audio_only = audio_only
        self.signals = WorkerSignals()
        self.setAutoDelete(False)  # evita que Qt borre el worker antes de emitir señales

    def run(self):
        try:
            has_ffmpeg = shutil.which("ffmpeg") is not None

            if self.audio_only:
                selected_format = "bestaudio/best"
            elif has_ffmpeg:
                # Mejor calidad: une video y audio con ffmpeg
                selected_format = "bv*+ba/b"
            else:
                # Sin ffmpeg: un solo archivo que ya trae video y audio
                selected_format = "b[ext=mp4]/b"

            options = {
                "format": selected_format,
                "outtmpl": str(Path(self.folder) / "%(title)s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "no_color": True,  # errores sin códigos ANSI
                "socket_timeout": 30,
                "progress_hooks": [self.update_progress],
            }

            if has_ffmpeg and not self.audio_only:
                options["merge_output_format"] = "mp4"

            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([self.url])

            self.signals.progress.emit(100, "Descarga completada.")
            self.signals.result.emit({"success": True})

        except Exception as exc:
            self.signals.error.emit(str(exc))

        finally:
            self.signals.finished.emit()

    def update_progress(self, data):
        if data["status"] == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate")

            if total:
                percent = max(0, min(int(downloaded * 100 / total), 100))
                self.signals.progress.emit(percent, f"Descargando... {percent}%")
            else:
                self.signals.progress.emit(0, "Descargando... calculando tamaño.")

        elif data["status"] == "finished":
            self.signals.progress.emit(100, "Archivo descargado. Finalizando...")


class ClipFlowWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ClipFlow - Video Downloader")
        self.resize(850, 700)
        self.setMinimumSize(700, 600)

        self.download_folder = ""
        self.thread_pool = QThreadPool()
        self.current_worker = None

        self.create_interface()
        self.apply_styles()

    def create_interface(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(14)

        # Encabezado
        header = QHBoxLayout()

        logo = QLabel("CF")
        logo.setObjectName("logo")

        title = QLabel("ClipFlow")
        title.setObjectName("app_title")

        version = QLabel("v0.3.0")
        version.setObjectName("muted")

        header.addWidget(logo)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(version)

        main_layout.addLayout(header)

        heading = QLabel("Descarga tus videos")
        heading.setObjectName("heading")

        description = QLabel(
            "Analiza un enlace y descarga contenido "
            "de plataformas compatibles."
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
        self.analyze_button.clicked.connect(self.analyze_url)

        main_layout.addWidget(self.url_input)
        main_layout.addWidget(self.analyze_button)

        # Formato
        main_layout.addWidget(QLabel("Formato de descarga"))

        self.format_combo = QComboBox()
        self.format_combo.addItems(
            [
                "Video",
                "Solo audio (sin conversión)",
            ]
        )

        main_layout.addWidget(self.format_combo)

        # Carpeta
        main_layout.addWidget(QLabel("Carpeta de descarga"))

        folder_layout = QHBoxLayout()

        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        self.folder_input.setPlaceholderText(
            "Selecciona dónde guardar los archivos..."
        )

        browse_button = QPushButton("Elegir carpeta")
        browse_button.clicked.connect(self.choose_folder)

        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(browse_button)

        main_layout.addLayout(folder_layout)

        # Botón de descarga
        self.download_button = QPushButton("Descargar")
        self.download_button.setObjectName("primary_button")
        self.download_button.clicked.connect(self.start_download)

        main_layout.addWidget(self.download_button)

        # Información del video
        self.result_label = QLabel(
            "La información del video aparecerá aquí."
        )
        self.result_label.setObjectName("result")
        self.result_label.setWordWrap(True)

        main_layout.addWidget(self.result_label)

        # Progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        main_layout.addWidget(self.progress_bar)

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

        if not url.startswith(("https://", "http://")):
            QMessageBox.warning(
                self,
                "Enlace no válido",
                "Introduce una URL que comience con https:// o http://.",
            )
            return

        self.analyze_button.setEnabled(False)
        self.status_label.setText("Analizando enlace...")
        self.result_label.setText("Consultando información...")

        worker = VideoAnalyzer(url)
        self.current_worker = worker

        worker.signals.result.connect(self.show_result)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.analysis_finished)

        self.thread_pool.start(worker)

    def show_result(self, data):
        duration = data["duration"]

        if duration is None:
            duration_text = "No disponible"
        else:
            duration = int(duration)
            hours, remainder = divmod(duration, 3600)
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
            f"Autor: {data['uploader']}\n"
            f"Duración: {duration_text}\n"
            f"Formatos detectados: {data['formats']}"
        )

        self.status_label.setText("Análisis completado.")

    def start_download(self):
        url = self.url_input.text().strip()

        if not url.startswith(("https://", "http://")):
            QMessageBox.warning(
                self,
                "Enlace no válido",
                "Introduce un enlace válido antes de descargar.",
            )
            return

        if not self.download_folder:
            QMessageBox.warning(
                self,
                "Carpeta requerida",
                "Selecciona una carpeta para guardar el archivo.",
            )
            return

        audio_only = self.format_combo.currentIndex() == 1

        self.download_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preparando descarga...")

        worker = VideoDownloader(
            url,
            self.download_folder,
            audio_only,
        )
        self.current_worker = worker

        worker.signals.progress.connect(self.update_progress)
        worker.signals.result.connect(self.download_finished)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.restore_controls)

        self.thread_pool.start(worker)

    def update_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def download_finished(self, result):
        self.progress_bar.setValue(100)
        self.status_label.setText("Descarga completada.")

        QMessageBox.information(
            self,
            "Descarga completada",
            "El proceso de descarga terminó. "
            "Revisa la carpeta seleccionada.",
        )

    def show_error(self, message):
        self.status_label.setText("Ocurrió un error.")

        QMessageBox.warning(
            self,
            "No se pudo completar la operación",
            message[:1200],
        )

    def analysis_finished(self):
        self.analyze_button.setEnabled(True)

    def restore_controls(self):
        self.download_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.format_combo.setEnabled(True)

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
                color: white;
                border: 1px solid #44536D;
                border-radius: 7px;
                padding: 10px;
                min-height: 20px;
            }

            QProgressBar {
                background-color: #253149;
                border: 1px solid #44536D;
                border-radius: 6px;
                text-align: center;
                min-height: 22px;
            }

            QProgressBar::chunk {
                background-color: #3984F6;
                border-radius: 5px;
            }

            QPushButton {
                background-color: #303E56;
                color: white;
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
