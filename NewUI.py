import sys
import time
from typing import Optional, Dict, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QPixmap, QFont, QImage, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFileDialog,
    QHeaderView, QTableWidgetItem, QFormLayout, QSlider,
    QDoubleSpinBox, QHBoxLayout, QCheckBox
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
import dill

# ========================== 检测界面 ==========================
class DetectionInterface(ScrollArea):
    detectionResultReady = Signal(list)  # 新的信号，用于发送检测结果列表

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DetectionInterface")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        # 组件声明
        self.uploadBtn: PrimaryPushButton
        self.originalImageLabel: QLabel  # 用于显示原图
        self.detectedImageLabel: QLabel  # 用于显示检测后的图片
        self.progressBar: IndeterminateProgressBar
        self.detection_model = None  # 用于存储加载的 YOLO 模型
        self.resultTable: TableWidget  # 用于显示检测结果表格
        self.showDetectedOnlyCheckBox: QCheckBox  # 新增的复选框

        self.show_detected_only = False  # 默认不开启只显示检测结果

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

        # 图片显示区域（水平布局）
        imageLayout = QHBoxLayout()

        # 原图显示标签
        self.originalImageLabel = QLabel(self)
        self.originalImageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.originalImageLabel.setStyleSheet("""
            background-color: #e0e0e0;
            border: 1px solid #ccc;
            border-radius: 4px;
        """)
        self.originalImageLabel.setMinimumSize(600, 400)
        imageLayout.addWidget(self.originalImageLabel)

        # 检测后图片显示标签
        self.detectedImageLabel = QLabel(self)
        self.detectedImageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detectedImageLabel.setStyleSheet("""
            background-color: #f0f0f0;
            border: 2px dashed #ccc;
            border-radius: 8px;
        """)
        self.detectedImageLabel.setMinimumSize(600, 400)
        imageLayout.addWidget(self.detectedImageLabel)

        # 只显示检测结果复选框
        self.showDetectedOnlyCheckBox = QCheckBox("仅显示检测结果", self)
        self.showDetectedOnlyCheckBox.setChecked(False)  # 默认不选中
        self.showDetectedOnlyCheckBox.toggled.connect(self.toggleShowDetectedOnly) # type: ignore

        # 检测结果表格
        self.resultTable = TableWidget(self)
        self.resultTable.setColumnCount(2)
        self.resultTable.setHorizontalHeaderLabels(["缺陷类型", "置信度"])
        self.resultTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 进度条
        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.hide()

        # 布局组装
        layout.addWidget(self.uploadBtn)
        layout.addSpacing(15)
        layout.addWidget(self.showDetectedOnlyCheckBox) # 添加复选框
        layout.addSpacing(10)
        layout.addLayout(imageLayout)  # 添加水平布局
        layout.addSpacing(15)
        layout.addWidget(StrongBodyLabel("检测结果:"))
        layout.addWidget(self.resultTable)
        layout.addWidget(self.progressBar)

    def toggleShowDetectedOnly(self, checked: bool):
        self.show_detected_only = checked
        self.updateImageDisplay()

    def uploadImage(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.loadOriginalImage(path)
            detection_results, detected_image = self.runDetection(path)
            self.displayDetectedImage(detected_image)
            self.displayDetectionResults(detection_results)
            self.updateImageDisplay() # 初始加载后也更新显示

    def loadOriginalImage(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            MessageBox("错误", "无法加载图片文件", self).exec()
            return

        scaled = pixmap.scaled(
            self.originalImageLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.originalImageLabel.setPixmap(scaled)
        if not self.show_detected_only:
            self.originalImageLabel.show()
        self.detectedImageLabel.clear() # 清空检测后的图片

    def displayDetectedImage(self, detected_image: Optional[np.ndarray]):
        if detected_image is not None:
            height, width, channel = detected_image.shape
            bytes_per_line = 3 * width
            q_image = QImage(detected_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            detected_pixmap = QPixmap.fromImage(q_image)

            scaled_pixmap = detected_pixmap.scaled(
                self.detectedImageLabel.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.detectedImageLabel.setPixmap(scaled_pixmap)
            self.detectedImageLabel.show()
        else:
            self.detectedImageLabel.setText("未检测到图片")
            self.detectedImageLabel.setStyleSheet("""
                background-color: #f0f0f0;
                border: 2px dashed #ccc;
                border-radius: 8px;
                color: gray;
            """)
            self.detectedImageLabel.show()

    def updateImageDisplay(self):
        if self.show_detected_only:
            self.originalImageLabel.hide()
            self.detectedImageLabel.show()
        else:
            self.originalImageLabel.show()
            self.detectedImageLabel.show()


    def runDetection(self, image_path: str) -> Tuple[list, Optional[np.ndarray]]:
        results_list = []
        detected_image_np = None

        if self.detection_model is None:
            MessageBox("错误", "检测模型尚未加载", self).exec()
            return results_list, detected_image_np

        self.progressBar.show()
        try:
            results = self.detection_model(image_path)
            res_plotted = results[0].plot()  # 获取带有标注的图片 (NumPy array)
            detected_image_np = res_plotted.copy() # 保存检测后的图片

            # 提取检测结果
            if results and results[0].boxes and len(results[0].boxes.conf) > 0:
                for i in range(len(results[0].boxes.conf)):
                    confidence = results[0].boxes.conf[i].item()
                    class_id = results[0].boxes.cls[i].item()
                    label = results[0].names[class_id]
                    results_list.append({"label": label, "confidence": confidence})

            self.detectionResultReady.emit(results_list) # 发送信号

        except Exception as e:
            MessageBox("错误", f"检测过程中发生错误: {e}", self).exec()
        finally:
            self.progressBar.hide()
            return results_list, detected_image_np

    def displayDetectionResults(self, results: list):
        self.resultTable.clearContents()
        self.resultTable.setRowCount(len(results))

        for row, result in enumerate(results):
            label_item = QTableWidgetItem(result["label"])
            confidence_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            confidence_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.resultTable.setItem(row, 0, label_item)
            self.resultTable.setItem(row, 1, confidence_item)

# ========================== 主窗口 ==========================
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能焊缝检测系统")
        self.resize(1400, 800)
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