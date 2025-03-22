from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QPixmap
from qfluentwidgets import (
    ScrollArea, PrimaryPushButton, StrongBodyLabel,
    TableWidget, IndeterminateProgressBar, MessageBox,
    FluentIcon as FIF
)
from .thread import DetectionThread


class DetectionInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DetectionInterface")
        self._initUI()

    def _initUI(self):
        # 布局组件
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        layout = QVBoxLayout(self.view)

        # 上传按钮
        self.uploadBtn = PrimaryPushButton("上传焊缝图片", self)
        self.uploadBtn.setIcon(FIF.PHOTO)
        self.uploadBtn.clicked.connect(self._handleUpload)  # type: ignore

        # 图片显示
        self.imageLabel = QLabel(self)
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imageLabel.setStyleSheet("""
            background-color: #f0f0f0;
            border: 2px dashed #ccc;
            border-radius: 8px;
        """)
        self.imageLabel.setMinimumSize(600, 400)

        # 结果表格
        self.resultTable = TableWidget(self)
        self._configureTable()

        # 进度条
        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.hide()

        # 组装布局
        layout.addWidget(self.uploadBtn)
        layout.addSpacing(15)
        layout.addWidget(self.imageLabel)
        layout.addSpacing(25)
        layout.addWidget(StrongBodyLabel("检测结果:"))
        layout.addWidget(self.resultTable)
        layout.addWidget(self.progressBar)

    def _configureTable(self):
        self.resultTable.setColumnCount(4)
        self.resultTable.setHorizontalHeaderLabels(
            ["位置X", "位置Y", "长度(mm)", "缺陷类型"]
        )
        header = self.resultTable.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def _handleUpload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._loadImage(path)
            self._startDetection(path)

    def _loadImage(self, path: str):
        if pixmap := QPixmap(path):
            scaled = pixmap.scaled(
                self.imageLabel.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.imageLabel.setPixmap(scaled)
        else:
            MessageBox("错误", "无法加载图片文件", self).exec()

    def _startDetection(self, path: str):
        self.progressBar.show()
        self.worker = DetectionThread(path)
        self.worker.progressUpdated.connect(self._updateProgress)  # type: ignore
        self.worker.resultReady.connect(self._showResults)  # type: ignore
        self.worker.start()

    def _updateProgress(self, value: int):
        if value >= 100:
            self.progressBar.hide()

    def _showResults(self, result: dict):
        self.resultTable.clearContents()
        defects = result.get("defects", [])
        self.resultTable.setRowCount(len(defects))

        for row, defect in enumerate(defects):
            pos = defect.get("position", (0, 0))
            self._setTableRow(row, [
                str(pos[0]),
                str(pos[1]),
                f"{defect.get('length', 0):.2f}",
                defect.get("type", "未知")
            ])

    def _setTableRow(self, row: int, data: list):
        for col, value in enumerate(data):
            self.resultTable.setItem(row, col, QTableWidgetItem(value))