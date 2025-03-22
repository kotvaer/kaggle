import sys
import time
from typing import Optional, Dict

from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QPixmap, QFont, QImage
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFileDialog,
    QHeaderView, QTableWidgetItem, QFormLayout, QSlider,
    QDoubleSpinBox
)
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, MessageBox,
    IndeterminateProgressBar, ScrollArea, PrimaryPushButton,
    StrongBodyLabel, TableWidget, setTheme, Theme, FluentIcon as FIF
)

import torch
from ultralytics import YOLO
import cv2
import numpy as np

# ========================== 检测界面 ==========================
class DetectionInterface(ScrollArea):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DetectionInterface")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        # 组件声明
        self.uploadBtn: PrimaryPushButton
        self.imageLabel: QLabel
        self.progressBar: IndeterminateProgressBar
        self.detection_model = None  # 用于存储加载的 YOLO 模型

        self.initUI()
        self.loadDetectionModel()

    def loadDetectionModel(self):
        path = 'models/best.pt'  # 确保模型文件路径正确
        try:
            self.detection_model = YOLO(path, task='detect')
        except Exception as e:
            MessageBox("错误", f"加载模型失败: {e}", self).exec()

    def initUI(self):
        # 主布局
        layout = QVBoxLayout(self.view)

        # 上传按钮
        self.uploadBtn = PrimaryPushButton("上传焊缝图片", self)
        self.uploadBtn.setIcon(FIF.PHOTO)
        self.uploadBtn.clicked.connect(self.uploadImage)  # type: ignore

        # 图片显示
        self.imageLabel = QLabel(self)
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imageLabel.setStyleSheet("""
            background-color: #f0f0f0;
            border: 2px dashed #ccc;
            border-radius: 8px;
        """)
        self.imageLabel.setMinimumSize(600, 400)

        # 进度条
        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.hide()

        # 布局组装
        layout.addWidget(self.uploadBtn)
        layout.addSpacing(15)
        layout.addWidget(self.imageLabel)
        layout.addWidget(self.progressBar)

    def uploadImage(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.loadImage(path)
            self.runDetection(path)

    def loadImage(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            MessageBox("错误", "无法加载图片文件", self).exec()
            return

        scaled = pixmap.scaled(
            self.imageLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.imageLabel.setPixmap(scaled)

    def runDetection(self, image_path: str):
        if self.detection_model is None:
            MessageBox("错误", "检测模型尚未加载", self).exec()
            return

        self.progressBar.show()
        try:
            results = self.detection_model(image_path)
            res_plotted = results[0].plot()  # 获取带有标注的图片 (NumPy array)

            # 将 OpenCV 图片转换为 QPixmap
            height, width, channel = res_plotted.shape
            bytes_per_line = 3 * width
            q_image = QImage(res_plotted.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            detected_pixmap = QPixmap.fromImage(q_image)

            scaled_pixmap = detected_pixmap.scaled(
                self.imageLabel.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.imageLabel.setPixmap(scaled_pixmap)

        except Exception as e:
            MessageBox("错误", f"检测过程中发生错误: {e}", self).exec()
        finally:
            self.progressBar.hide()

# ========================== 主窗口 ==========================
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能焊缝检测系统")
        self.resize(1200, 800)
        setTheme(Theme.LIGHT)

        # 初始化界面
        self.detectionInterface = DetectionInterface()
        self.settingsInterface = QWidget()
        self.settingsInterface.setObjectName("SettingsInterface")

        # 添加导航
        self.addSubInterface(
            self.detectionInterface,
            FIF.VIDEO,
            "焊缝检测"
        )
        self.addSubInterface(
            self.settingsInterface,
            FIF.SETTING,
            "系统设置",
            position=NavigationItemPosition.BOTTOM
        )

        # 初始化设置
        self.initSettings()

    def initSettings(self):
        layout = QFormLayout(self.settingsInterface)

        # 灵敏度设置
        self.sensitivitySlider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivitySlider.setRange(1, 10)
        self.sensitivitySlider.setValue(5)
        layout.addRow(StrongBodyLabel("检测灵敏度:"), self.sensitivitySlider)

        # 阈值设置
        self.thresholdSpinBox = QDoubleSpinBox()
        self.thresholdSpinBox.setRange(0.1, 10.0)
        self.thresholdSpinBox.setValue(2.5)
        layout.addRow(StrongBodyLabel("报警阈值(mm):"), self.thresholdSpinBox)

        # 保存按钮
        self.saveBtn = PrimaryPushButton("保存设置")
        self.saveBtn.clicked.connect(self.saveSettings)  # type: ignore
        layout.addRow(self.saveBtn)

    def saveSettings(self):
        sens = self.sensitivitySlider.value()
        threshold = self.thresholdSpinBox.value()
        MessageBox(
            "设置已保存",
            f"当前设置：\n灵敏度等级: {sens}\n报警阈值: {threshold}mm",
            self
        ).exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置默认字体
    font = QFont()
    font.setFamilies(["Microsoft YaHei", "PingFang SC"])
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())