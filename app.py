#!/usr/bin/env python3
"""
Video Processor - macOS Desktop App
Drag and drop videos to process with selected pipeline.
"""

import sys
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QPushButton, QListWidget, QListWidgetItem,
    QProgressBar, QFileDialog, QMessageBox, QFrame, QTextEdit,
    QDialog, QGroupBox, QSpinBox, QLineEdit, QDoubleSpinBox, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

from pipelines import get_available_pipelines

PIPELINE_HELP = """
To create a new pipeline, add a Python file in the 'pipelines' folder.

Example: pipelines/my_pipeline.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

name = "My Pipeline"
description = "What this pipeline does"

def process(input_path, output_dir, progress_callback=None):
    \"\"\"
    Process a video file.

    Args:
        input_path: Path to input video file
        output_dir: Directory to save output file
        progress_callback: Optional callback(percent, message)

    Returns:
        Path to the output file
    \"\"\"
    from pathlib import Path
    import subprocess

    input_path = Path(input_path)
    output_path = Path(output_dir) / f"{input_path.stem}_output.mp4"

    # Report progress
    if progress_callback:
        progress_callback(0, "Starting...")

    # Your ffmpeg or processing command here
    cmd = ["ffmpeg", "-i", str(input_path), str(output_path)]
    subprocess.run(cmd)

    if progress_callback:
        progress_callback(100, "Done!")

    return str(output_path)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After adding the file, restart the app to see your new pipeline.
"""


class PipelineHelpDialog(QDialog):
    """Dialog showing how to create a new pipeline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Pipeline")
        self.setMinimumSize(500, 450)

        layout = QVBoxLayout(self)

        # Help text
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(PIPELINE_HELP.strip())
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ddd;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #444;
                border-radius: 4px;
            }
        """)
        layout.addWidget(help_text)

        # Open folder button
        btn_layout = QHBoxLayout()
        open_folder_btn = QPushButton("Open Pipelines Folder")
        open_folder_btn.clicked.connect(self.open_pipelines_folder)
        btn_layout.addWidget(open_folder_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def open_pipelines_folder(self):
        import subprocess
        pipelines_dir = Path(__file__).parent / "pipelines"
        subprocess.run(["open", str(pipelines_dir)])


class DownloadThread(QThread):
    """Background thread for downloading videos from URLs using yt-dlp."""
    progress = pyqtSignal(int, str)  # percent, message
    finished = pyqtSignal(str)  # downloaded file path
    error = pyqtSignal(str)  # error message

    def __init__(self, url, output_dir):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self._stop_requested = False

    def run(self):
        if not YT_DLP_AVAILABLE:
            self.error.emit("yt-dlp is not installed. Please install it with: pip install yt-dlp")
            return

        final_filepath = None

        def progress_hook(d):
            if self._stop_requested:
                raise Exception("Download cancelled")

            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    percent = int(downloaded * 100 / total)
                    speed = d.get('speed', 0)
                    speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else ""
                    self.progress.emit(percent, f"Downloading... {percent}% {speed_str}")
                else:
                    self.progress.emit(0, "Downloading...")
            elif d['status'] == 'finished':
                self.progress.emit(95, "Processing...")

        def postprocessor_hook(d):
            nonlocal final_filepath
            if d['status'] == 'finished':
                # This is the final file after all postprocessing (merging, etc.)
                final_filepath = d.get('info_dict', {}).get('filepath')
                self.progress.emit(100, "Download complete!")

        ydl_opts = {
            'outtmpl': str(Path(self.output_dir) / '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hook],
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.progress.emit(0, "Extracting video info...")
                info = ydl.extract_info(self.url, download=True)

                # Use filepath from postprocessor hook (most reliable)
                if final_filepath and Path(final_filepath).exists():
                    self.finished.emit(final_filepath)
                    return

                # Fallback: use prepare_filename to get expected path
                expected_path = ydl.prepare_filename(info)
                if Path(expected_path).exists():
                    self.finished.emit(expected_path)
                    return

                # Final fallback: check for common video extensions
                base_path = Path(expected_path).with_suffix('')
                for ext in ['.mp4', '.mkv', '.webm', '.mov']:
                    check_path = base_path.with_suffix(ext)
                    if check_path.exists():
                        self.finished.emit(str(check_path))
                        return

                self.error.emit("Download completed but file not found")

        except Exception as e:
            if "cancelled" not in str(e).lower():
                self.error.emit(str(e))

    def stop(self):
        self._stop_requested = True


class URLDownloadDialog(QDialog):
    """Dialog for downloading videos from URLs."""
    download_complete = pyqtSignal(str)  # Emits the downloaded file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download from URL")
        self.setMinimumWidth(500)
        self.download_thread = None

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video URL here (YouTube, Vimeo, etc.)")
        self.url_input.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Output directory selection
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Save to:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select output directory")
        default_dir = str(Path.home() / "Downloads")
        self.dir_input.setText(default_dir)
        dir_layout.addWidget(self.dir_input)
        self.browse_dir_btn = QPushButton("Browse...")
        self.browse_dir_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_dir_btn)
        layout.addLayout(dir_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.start_download)
        btn_layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_or_close)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def on_url_changed(self, text):
        # Enable download button if URL looks valid
        is_valid = text.startswith(('http://', 'https://')) and len(text) > 10
        self.download_btn.setEnabled(is_valid)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            self.dir_input.text() or str(Path.home())
        )
        if directory:
            self.dir_input.setText(directory)

    def start_download(self):
        url = self.url_input.text().strip()
        output_dir = self.dir_input.text().strip()

        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL")
            return

        if not output_dir or not Path(output_dir).is_dir():
            QMessageBox.warning(self, "Error", "Please select a valid output directory")
            return

        # Disable inputs during download
        self.url_input.setEnabled(False)
        self.dir_input.setEnabled(False)
        self.browse_dir_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Start download thread
        self.download_thread = DownloadThread(url, output_dir)
        self.download_thread.progress.connect(self.on_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def on_download_finished(self, file_path):
        self.download_complete.emit(file_path)
        self.status_label.setText(f"Downloaded: {Path(file_path).name}")
        self.reset_ui()
        self.accept()

    def on_download_error(self, error):
        QMessageBox.critical(self, "Download Error", str(error))
        self.status_label.setText(f"Error: {error}")
        self.reset_ui()

    def reset_ui(self):
        self.url_input.setEnabled(True)
        self.dir_input.setEnabled(True)
        self.browse_dir_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Download")
        self.progress_bar.setVisible(False)

    def cancel_or_close(self):
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
            self.download_thread.wait(2000)
        self.reject()

    def closeEvent(self, event):
        self.cancel_or_close()
        event.accept()


class PipelineOptionsDialog(QDialog):
    """Dialog for configuring pipeline options."""

    def __init__(self, pipeline_name, options_config, current_values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure {pipeline_name}")
        self.setMinimumWidth(350)
        self.options_config = options_config
        self.widgets = {}
        self.result_values = current_values.copy() if current_values else {}

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Form layout for options
        form = QFormLayout()

        for opt in self.options_config:
            key = opt['key']
            label = opt['label']
            opt_type = opt['type']
            default = opt['default']
            current = self.result_values.get(key, default)

            if opt_type == 'float':
                widget = QDoubleSpinBox()
                widget.setRange(opt.get('min', 0), opt.get('max', 100))
                widget.setSingleStep(opt.get('step', 0.1))
                widget.setDecimals(2)
                widget.setValue(float(current))
            elif opt_type == 'int':
                widget = QSpinBox()
                widget.setRange(opt.get('min', 0), opt.get('max', 10000))
                widget.setValue(int(current))
            else:
                widget = QLineEdit()
                widget.setText(str(current))

            if 'description' in opt:
                widget.setToolTip(opt['description'])

            self.widgets[key] = widget
            form.addRow(f"{label}:", widget)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_values)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def reset_defaults(self):
        for opt in self.options_config:
            key = opt['key']
            default = opt['default']
            widget = self.widgets[key]

            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(default))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(default))
            else:
                widget.setText(str(default))

    def accept_values(self):
        for opt in self.options_config:
            key = opt['key']
            widget = self.widgets[key]

            if isinstance(widget, QDoubleSpinBox):
                self.result_values[key] = widget.value()
            elif isinstance(widget, QSpinBox):
                self.result_values[key] = widget.value()
            else:
                self.result_values[key] = widget.text()

        self.accept()

    def get_values(self):
        return self.result_values


def process_task(args):
    """
    Worker function that runs in a separate process.
    Must be module-level to be picklable.

    Args:
        args: Tuple of (file_path, output_dir, pipeline_key, pipeline_name, progress_queue, task_id, options)

    Returns:
        Tuple of (task_id, 'success', file_path, output_path, pipeline_name) or
        (task_id, 'error', file_path, error_message, pipeline_name)
    """
    file_path, output_dir, pipeline_key, pipeline_name, progress_queue, task_id, options = args

    try:
        # Import pipeline dynamically in worker process
        import importlib
        import inspect
        module = importlib.import_module(f'pipelines.{pipeline_key}')
        process_func = module.process

        def progress_callback(percent, message):
            # Send progress update to queue
            progress_queue.put(('progress', task_id, percent, f"[{pipeline_name}] {message}"))

        # Check if process function accepts options parameter
        sig = inspect.signature(process_func)
        if 'options' in sig.parameters:
            output_path = process_func(file_path, output_dir, progress_callback=progress_callback, options=options)
        else:
            output_path = process_func(file_path, output_dir, progress_callback=progress_callback)
        return (task_id, 'success', file_path, output_path, pipeline_name)
    except Exception as e:
        return (task_id, 'error', file_path, str(e), pipeline_name)


class ProcessingThread(QThread):
    """Background thread that coordinates multiprocess video processing."""
    progress = pyqtSignal(int, str)
    finished_file = pyqtSignal(str, str, str)  # input_path, output_path, pipeline_name
    error = pyqtSignal(str, str, str)  # input_path, error_message, pipeline_name
    all_done = pyqtSignal()

    def __init__(self, files, pipelines, worker_count=4, pipeline_options=None):
        """
        Args:
            files: List of file paths to process
            pipelines: List of (key, name, process_func) tuples
            worker_count: Number of parallel worker processes
            pipeline_options: Dict mapping pipeline_key to options dict
        """
        super().__init__()
        self.files = files
        self.pipelines = pipelines
        self.worker_count = worker_count
        self.pipeline_options = pipeline_options or {}
        self._stop_requested = False
        self._executor = None

    def run(self):
        # Create manager for cross-process communication
        manager = multiprocessing.Manager()
        progress_queue = manager.Queue()

        # Build task list: (file_path, output_dir, pipeline_key, pipeline_name, queue, task_id, options)
        tasks = []
        task_id = 0
        for file_path in self.files:
            output_dir = str(Path(file_path).parent)
            for key, name, _ in self.pipelines:  # process_func not used, imported in worker
                options = self.pipeline_options.get(key, {})
                tasks.append((file_path, output_dir, key, name, progress_queue, task_id, options))
                task_id += 1

        total_tasks = len(tasks)
        if total_tasks == 0:
            self.all_done.emit()
            return

        # Track per-task progress for overall calculation
        task_progress = {i: 0 for i in range(total_tasks)}
        completed_count = 0

        self._executor = ProcessPoolExecutor(max_workers=self.worker_count)
        try:
            # Submit all tasks
            futures = {self._executor.submit(process_task, task): task for task in tasks}

            # Poll for progress and completion
            while completed_count < total_tasks and not self._stop_requested:
                # Check progress queue (non-blocking)
                try:
                    while True:
                        msg = progress_queue.get_nowait()
                        if msg[0] == 'progress':
                            _, tid, percent, message = msg
                            task_progress[tid] = percent
                            # Calculate overall progress
                            overall = int(sum(task_progress.values()) / total_tasks)
                            self.progress.emit(overall, message)
                except:
                    pass  # Queue empty

                # Check for completed futures
                for future in list(futures.keys()):
                    if future.done():
                        task = futures.pop(future)
                        try:
                            result = future.result()
                            task_id, status, file_path, output_or_error, pipeline_name = result
                            task_progress[task_id] = 100

                            if status == 'success':
                                self.finished_file.emit(file_path, output_or_error, pipeline_name)
                            else:
                                self.error.emit(file_path, output_or_error, pipeline_name)
                        except Exception as e:
                            # Worker process crashed
                            file_path = task[0]
                            pipeline_name = task[3]
                            self.error.emit(file_path, str(e), pipeline_name)

                        completed_count += 1
                        # Update overall progress
                        overall = int(sum(task_progress.values()) / total_tasks)
                        self.progress.emit(overall, f"Completed {completed_count}/{total_tasks} tasks")

                # Small sleep to avoid busy-waiting
                self.msleep(50)

        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        self.all_done.emit()

    def stop(self):
        self._stop_requested = True
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)


class DropZone(QFrame):
    """Drag and drop zone for video files."""
    files_dropped = pyqtSignal(list)

    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpeg', '.mpg'}

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #666;
                border-radius: 10px;
                background-color: #2d2d2d;
            }
            DropZone:hover {
                border-color: #888;
                background-color: #353535;
            }
        """)

        layout = QVBoxLayout(self)
        label = QLabel("Drop Video Files Here")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 18px;")
        layout.addWidget(label)

        sublabel = QLabel("or click Browse to select files")
        sublabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sublabel.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(sublabel)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px dashed #4a9eff;
                    border-radius: 10px;
                    background-color: #3d3d5c;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #666;
                border-radius: 10px;
                background-color: #2d2d2d;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #666;
                border-radius: 10px;
                background-color: #2d2d2d;
            }
        """)

        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in self.VIDEO_EXTENSIONS:
                files.append(path)

        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()


class VideoProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Pipelines")
        self.setMinimumSize(600, 500)
        self.processing_thread = None

        # Load pipelines
        self.pipelines = get_available_pipelines()

        # Store pipeline options (key -> options dict)
        self.pipeline_options = {}

        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Pipeline selection with checkboxes
        pipeline_header = QHBoxLayout()
        pipeline_header.addWidget(QLabel("Pipelines:"))
        pipeline_header.addStretch()
        help_btn = QPushButton("Read Me")
        help_btn.clicked.connect(self.show_pipeline_help)
        pipeline_header.addWidget(help_btn)
        layout.addLayout(pipeline_header)

        # Pipeline checkboxes with configure buttons
        self.pipeline_checkboxes = {}
        for key, pipeline in self.pipelines.items():
            row = QHBoxLayout()
            cb = QCheckBox(f"{pipeline['name']} - {pipeline['description']}")
            cb.setChecked(True)  # Default to checked
            cb.setProperty("pipeline_key", key)
            self.pipeline_checkboxes[key] = cb
            row.addWidget(cb)

            # Add configure button if pipeline has options
            if pipeline.get('options'):
                config_btn = QPushButton("Configure")
                config_btn.setFixedWidth(80)
                config_btn.setProperty("pipeline_key", key)
                config_btn.clicked.connect(lambda checked, k=key: self.configure_pipeline(k))
                row.addWidget(config_btn)
            else:
                row.addStretch()

            layout.addLayout(row)

        # Settings section
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Workers:"))
        self.worker_count_spinbox = QSpinBox()
        self.worker_count_spinbox.setRange(1, 16)
        self.worker_count_spinbox.setValue(4)
        self.worker_count_spinbox.setToolTip("Number of parallel processing workers")
        self.worker_count_spinbox.setFixedWidth(60)
        settings_layout.addWidget(self.worker_count_spinbox)
        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.add_files)
        layout.addWidget(self.drop_zone)

        # Browse and Download buttons
        browse_layout = QHBoxLayout()
        browse_btn = QPushButton("Browse Files...")
        browse_btn.clicked.connect(self.browse_files)
        browse_layout.addWidget(browse_btn)

        download_url_btn = QPushButton("Download from URL...")
        download_url_btn.clicked.connect(self.download_from_url)
        if not YT_DLP_AVAILABLE:
            download_url_btn.setEnabled(False)
            download_url_btn.setToolTip("yt-dlp not installed. Run: pip install yt-dlp")
        browse_layout.addWidget(download_url_btn)
        layout.addLayout(browse_layout)

        # File list
        layout.addWidget(QLabel("Files to process:"))
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(100)
        layout.addWidget(self.file_list)

        # Clear and remove buttons
        list_btns = QHBoxLayout()
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        list_btns.addWidget(remove_btn)
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_files)
        list_btns.addWidget(clear_btn)
        list_btns.addStretch()
        layout.addLayout(list_btns)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(80)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #aaa; font-family: monospace;")
        layout.addWidget(self.log_area)

        # Process button
        btn_layout = QHBoxLayout()
        self.process_btn = QPushButton("Start Processing")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.clicked.connect(self.toggle_processing)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3a8eef;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        btn_layout.addWidget(self.process_btn)
        layout.addLayout(btn_layout)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ddd;
            }
            QLabel {
                color: #ddd;
            }
            QCheckBox {
                color: #ddd;
                padding: 3px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QListWidget, QPushButton {
                background-color: #2d2d2d;
                color: #ddd;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #4a9eff;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
            }
        """)

    def show_pipeline_help(self):
        dialog = PipelineHelpDialog(self)
        dialog.exec()

    def configure_pipeline(self, pipeline_key):
        """Show options dialog for a pipeline."""
        pipeline = self.pipelines.get(pipeline_key)
        if not pipeline or not pipeline.get('options'):
            return

        current_values = self.pipeline_options.get(pipeline_key, {})
        dialog = PipelineOptionsDialog(
            pipeline['name'],
            pipeline['options'],
            current_values,
            self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pipeline_options[pipeline_key] = dialog.get_values()
            self.log(f"Updated {pipeline['name']} settings")

    def add_files(self, files):
        for f in files:
            if not self.file_exists_in_list(f):
                item = QListWidgetItem(Path(f).name)
                item.setData(Qt.ItemDataRole.UserRole, f)
                item.setToolTip(f)
                self.file_list.addItem(item)
        self.log(f"Added {len(files)} file(s)")

    def file_exists_in_list(self, path):
        for i in range(self.file_list.count()):
            if self.file_list.item(i).data(Qt.ItemDataRole.UserRole) == path:
                return True
        return False

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Videos", "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.m4v *.mpeg *.mpg)"
        )
        if files:
            self.add_files(files)

    def download_from_url(self):
        """Open dialog to download video from URL."""
        dialog = URLDownloadDialog(self)
        dialog.download_complete.connect(self.on_download_complete)
        dialog.exec()

    def on_download_complete(self, file_path):
        """Handle completed download by adding file to the list."""
        self.add_files([file_path])
        self.log(f"Downloaded: {Path(file_path).name}")

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def clear_files(self):
        self.file_list.clear()

    def log(self, message):
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def toggle_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.process_btn.setText("Stopping...")
            self.process_btn.setEnabled(False)
        else:
            self.start_processing()

    def get_selected_pipelines(self):
        """Get list of selected pipelines as (key, name, process_func) tuples."""
        selected = []
        for key, cb in self.pipeline_checkboxes.items():
            if cb.isChecked():
                pipeline = self.pipelines[key]
                selected.append((key, pipeline['name'], pipeline['process']))
        return selected

    def start_processing(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "No Files", "Please add video files to process.")
            return

        selected_pipelines = self.get_selected_pipelines()
        if not selected_pipelines:
            QMessageBox.warning(self, "No Pipeline", "Please select at least one pipeline.")
            return

        files = []
        for i in range(self.file_list.count()):
            files.append(self.file_list.item(i).data(Qt.ItemDataRole.UserRole))

        pipeline_names = ", ".join(p[1] for p in selected_pipelines)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.process_btn.setText("Stop Processing")

        worker_count = self.worker_count_spinbox.value()
        self.log(f"Starting processing with {worker_count} workers: {pipeline_names}")

        self.processing_thread = ProcessingThread(files, selected_pipelines, worker_count, self.pipeline_options)
        self.processing_thread.progress.connect(self.on_progress)
        self.processing_thread.finished_file.connect(self.on_file_finished)
        self.processing_thread.error.connect(self.on_file_error)
        self.processing_thread.all_done.connect(self.on_all_done)
        self.processing_thread.start()

    def on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def on_file_finished(self, input_path, output_path, pipeline_name):
        self.log(f"[{pipeline_name}] {Path(input_path).name} -> {Path(output_path).name}")

    def on_file_error(self, input_path, error, pipeline_name):
        self.log(f"[{pipeline_name}] Error: {Path(input_path).name}: {error}")

    def on_all_done(self):
        self.progress_bar.setVisible(False)
        self.process_btn.setText("Start Processing")
        self.process_btn.setEnabled(True)
        self.status_label.setText("Processing complete!")
        self.log("All files processed.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Video Pipelines")

    # Set app icon
    icon_path = Path(__file__).parent / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = VideoProcessorApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    # Required for multiprocessing to work in frozen/bundled apps on macOS
    multiprocessing.freeze_support()
    main()
