# from PyQt6.QtCore import Qt
# from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QTableWidgetItem, QHeaderView
# from PyQt6.QtGui import QPixmap
# from qfluentwidgets import (
#     ScrollArea, PrimaryPushButton, StrongBodyLabel,
#     TableWidget, IndeterminateProgressBar, MessageBox,
#     FluentIcon as FIF
# )
# from .thread import DetectionThread
#
#
# class DetectionInterface(ScrollArea):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setObjectName("DetectionInterface")
#         self._initUI()
#
#     def _initUI(self):
#         # 布局组件
#         self.view = QWidget(self)
#         self.setWidget(self.view)
#         self.setWidgetResizable(True)
#
#         layout = QVBoxLayout(self.view)
#
#         # 上传按钮
#         self.uploadBtn = PrimaryPushButton("上传焊缝图片", self)
#         self.uploadBtn.setIcon(FIF.PHOTO)
#         self.uploadBtn.clicked.connect(self._handleUpload)  # type: ignore
#
#         # 图片显示
#         self.imageLabel = QLabel(self)
#         self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.imageLabel.setStyleSheet("""
#             background-color: #f0f0f0;
#             border: 2px dashed #ccc;
#             border-radius: 8px;
#         """)
#         self.imageLabel.setMinimumSize(600, 400)
#
#         # 结果表格
#         self.resultTable = TableWidget(self)
#         self._configureTable()
#
#         # 进度条
#         self.progressBar = IndeterminateProgressBar(self)
#         self.progressBar.hide()
#
#         # 组装布局
#         layout.addWidget(self.uploadBtn)
#         layout.addSpacing(15)
#         layout.addWidget(self.imageLabel)
#         layout.addSpacing(25)
#         layout.addWidget(StrongBodyLabel("检测结果:"))
#         layout.addWidget(self.resultTable)
#         layout.addWidget(self.progressBar)
#
#     def _configureTable(self):
#         self.resultTable.setColumnCount(4)
#         self.resultTable.setHorizontalHeaderLabels(
#             ["位置X", "位置Y", "长度(mm)", "缺陷类型"]
#         )
#         header = self.resultTable.horizontalHeader()
#         header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
#
#     def _handleUpload(self):
#         path, _ = QFileDialog.getOpenFileName(
#             self, "选择图片", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
#         )
#         if path:
#             self._loadImage(path)
#             self._startDetection(path)
#
#     def _loadImage(self, path: str):
#         if pixmap := QPixmap(path):
#             scaled = pixmap.scaled(
#                 self.imageLabel.size(),
#                 Qt.AspectRatioMode.KeepAspectRatio,
#                 Qt.TransformationMode.SmoothTransformation
#             )
#             self.imageLabel.setPixmap(scaled)
#         else:
#             MessageBox("错误", "无法加载图片文件", self).exec()
#
#     def _startDetection(self, path: str):
#         self.progressBar.show()
#         self.worker = DetectionThread(path)
#         self.worker.progressUpdated.connect(self._updateProgress)  # type: ignore
#         self.worker.resultReady.connect(self._showResults)  # type: ignore
#         self.worker.start()
#
#     def _updateProgress(self, value: int):
#         if value >= 100:
#             self.progressBar.hide()
#
#     def _showResults(self, result: dict):
#         self.resultTable.clearContents()
#         defects = result.get("defects", [])
#         self.resultTable.setRowCount(len(defects))
#
#         for row, defect in enumerate(defects):
#             pos = defect.get("position", (0, 0))
#             self._setTableRow(row, [
#                 str(pos[0]),
#                 str(pos[1]),
#                 f"{defect.get('length', 0):.2f}",
#                 defect.get("type", "未知")
#             ])
#
#     def _setTableRow(self, row: int, data: list):
#         for col, value in enumerate(data):
#             self.resultTable.setItem(row, col, QTableWidgetItem(value))

# thread.py 保持原样，使用现有版本即可

# interface.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QHBoxLayout
from PyQt6.QtGui import QPixmap, QImage
from qfluentwidgets import (
    ScrollArea, PrimaryPushButton, StrongBodyLabel, BodyLabel,
    IndeterminateProgressBar, MessageBox, FluentIcon as FIF
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
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setSpacing(15)

        # 上传按钮
        self.uploadBtn = PrimaryPushButton("上传焊缝图片", self)
        self.uploadBtn.setIcon(FIF.PHOTO)
        self.uploadBtn.clicked.connect(self._handleUpload)  # type: ignore

        # 图片显示区域
        self.imageLayout = QHBoxLayout()
        self.originalLabel = QLabel("原始图像", self)
        self.resultLabel = QLabel("检测结果", self)
        self._configureImageLabels()
        self.imageLayout.addWidget(self.originalLabel)
        self.imageLayout.addWidget(self.resultLabel)

        # 结果信息区域
        self.infoLayout = QVBoxLayout()
        self.resultText = StrongBodyLabel("检测结果：等待上传图片", self)
        self.confidenceText = BodyLabel("置信度：0.00", self)
        self.infoLayout.addWidget(self.resultText)
        self.infoLayout.addWidget(self.confidenceText)

        # 进度条
        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.hide()

        # 组装布局
        layout.addWidget(self.uploadBtn)
        layout.addLayout(self.imageLayout)
        layout.addLayout(self.infoLayout)
        layout.addWidget(self.progressBar)

    def _configureImageLabels(self):
        """配置图像显示标签样式"""
        style = """
            QLabel {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                min-width: 500px;
                min-height: 400px;
            }
        """
        for label in [self.originalLabel, self.resultLabel]:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(style)

    def _handleUpload(self):
        """处理图片上传"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图像文件 (*.png *.jpg *.jpeg)"
        )
        if path:
            self._showOriginalImage(path)
            self._startDetection(path)

    def _showOriginalImage(self, path: str):
        """显示原始图片"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.originalLabel.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.originalLabel.setPixmap(scaled)
        else:
            MessageBox("错误", "无法加载图片文件", self).exec()

    def _startDetection(self, path: str):
        """启动检测线程"""
        self.progressBar.show()
        self.uploadBtn.setEnabled(False)

        self.worker = DetectionThread(path)
        self.worker.resultReady.connect(self._showResults)  # type: ignore
        self.worker.errorOccurred.connect(self._showError)  # type: ignore
        self.worker.start()

    def _showResults(self, label: str, confidence: float, image_data):
        """显示检测结果"""
        # 更新进度状态
        self.progressBar.hide()
        self.uploadBtn.setEnabled(True)

        # 显示文本结果
        self.resultText.setText(f"检测结果：{label}")
        self.confidenceText.setText(f"置信度：{confidence:.2f}")

        # 显示检测图像
        height, width, _ = image_data.shape
        q_img = QImage(
            image_data.data,
            width,
            height,
            QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.resultLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.resultLabel.setPixmap(pixmap)

    def _showError(self, msg: str):
        """显示错误信息"""
        self.progressBar.hide()
        self.uploadBtn.setEnabled(True)
        MessageBox("检测错误", msg, self).exec()