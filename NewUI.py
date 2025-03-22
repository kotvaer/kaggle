import sys
import time
from typing import Optional, Dict, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QPixmap, QFont, QImage, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFileDialog,
    QHeaderView, QTableWidgetItem, QFormLayout, QSlider,
    QDoubleSpinBox, QHBoxLayout, QCheckBox, QPushButton, QComboBox,
    QSpinBox
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

# ========================== 视频检测界面 ==========================
class VideoDetectionInterface(ScrollArea):
    processedFrameReady = Signal(QImage)
    detectionFinished = Signal()

    def __init__(self, main_window, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_window = main_window  # 保存 MainWindow 实例
        self.setObjectName("VideoDetectionInterface")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.uploadVideoButton: PrimaryPushButton
        self.videoDisplayLabel: QLabel
        self.startButton: PrimaryPushButton
        self.stopButton: PrimaryPushButton
        self.progressBar: IndeterminateProgressBar

        self.video_path = None
        self.detection_model = None
        self.detection_thread = None

        self.initUI()
        self.loadDetectionModel()

    def loadDetectionModel(self):
        path = 'models/best.pt'  # 确保模型文件路径正确
        try:
            self.detection_model = YOLO(path, task='detect')
        except Exception as e:
            MessageBox("错误", f"加载模型失败: {e}", self).exec()

    def initUI(self):
        layout = QVBoxLayout(self.view)

        self.uploadVideoButton = PrimaryPushButton("选择视频文件", self)
        self.uploadVideoButton.setIcon(FIF.FOLDER)
        self.uploadVideoButton.clicked.connect(self.selectVideoFile) # type: ignore
        layout.addWidget(self.uploadVideoButton)

        self.videoDisplayLabel = QLabel(self)
        self.videoDisplayLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.videoDisplayLabel.setStyleSheet("""
            background-color: #333;
            color: #fff;
            border-radius: 8px;
        """)
        self.videoDisplayLabel.setMinimumSize(640, 480)
        layout.addWidget(self.videoDisplayLabel)

        controlsLayout = QHBoxLayout()
        self.startButton = PrimaryPushButton("开始检测", self)
        self.startButton.clicked.connect(self.startVideoDetection) # type: ignore
        self.startButton.setEnabled(False)
        controlsLayout.addWidget(self.startButton)

        self.stopButton = PrimaryPushButton("停止检测", self)
        self.stopButton.clicked.connect(self.stopVideoDetection) # type: ignore
        self.stopButton.setEnabled(False)
        controlsLayout.addWidget(self.stopButton)
        layout.addLayout(controlsLayout)

        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.hide()
        layout.addWidget(self.progressBar)

    def selectVideoFile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        if path:
            self.video_path = path
            self.startButton.setEnabled(True)
            self.videoDisplayLabel.setText(f"已选择视频: {path.split('/')[-1]}")
            if self.detection_thread and self.detection_thread.isRunning():
                self.stopVideoDetection()

    def startVideoDetection(self):
        if self.video_path and self.detection_model:
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(True)
            self.progressBar.show()
            confidence_threshold = self.main_window.confidenceSpinBox.value()
            max_detections = self.main_window.maxDetSpinBox.value()
            self.detection_thread = VideoDetectionThread(self.video_path, self.detection_model, conf=confidence_threshold, max_det=max_detections)
            self.detection_thread.processedFrameReady.connect(self.updateVideoFrame) # type: ignore
            self.detection_thread.detectionFinished.connect(self.videoDetectionFinished) # type: ignore
            self.detection_thread.start()

    def stopVideoDetection(self):
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.stop_flag = True
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)
            self.progressBar.hide()

    def updateVideoFrame(self, frame: QImage):
        pixmap = QPixmap.fromImage(frame)
        scaled_pixmap = pixmap.scaled(
            self.videoDisplayLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.videoDisplayLabel.setPixmap(scaled_pixmap)

    def videoDetectionFinished(self):
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.progressBar.hide()
        self.videoDisplayLabel.setText("视频检测完成")
        self.detection_thread = None

# ========================== 视频检测线程 ==========================
class VideoDetectionThread(QThread):
    processedFrameReady = Signal(QImage)
    detectionFinished = Signal()

    def __init__(self, video_path, model, conf=0.25, max_det=1000):
        super().__init__()
        self.video_path = video_path
        self.model = model
        self.stop_flag = False
        self.conf = conf
        self.max_det = max_det

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video at {self.video_path}")
            self.detectionFinished.emit()
            return

        while not self.stop_flag and cap.isOpened():
            success, frame = cap.read()
            if success:
                results = self.model(frame, conf=self.conf, max_det=self.max_det)
                annotated_frame = results[0].plot()

                height, width, channel = annotated_frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(annotated_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
                self.processedFrameReady.emit(q_image)
            else:
                break
            time.sleep(0.03) # 控制帧率，避免过快

        cap.release()
        self.detectionFinished.emit()

# ========================== 摄像头检测界面 ==========================
class CameraDetectionInterface(ScrollArea):
    processedFrameReady = Signal(QImage)
    detectionFinished = Signal()

    def __init__(self, main_window, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_window = main_window  # 保存 MainWindow 实例
        self.setObjectName("CameraDetectionInterface")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.cameraComboBox: QComboBox
        self.videoDisplayLabel: QLabel
        self.startButton: PrimaryPushButton
        self.stopButton: PrimaryPushButton

        self.detection_model = None
        self.detection_thread = None
        self.available_cameras = self.get_available_cameras()

        self.initUI()
        self.loadDetectionModel()

    def loadDetectionModel(self):
        path = 'models/best.pt'  # 确保模型文件路径正确
        try:
            self.detection_model = YOLO(path, task='detect')
        except Exception as e:
            MessageBox("错误", f"加载模型失败: {e}", self).exec()

    def get_available_cameras(self):
        index = 0
        cameras = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                cameras.append(index)
            cap.release()
            index += 1
        return cameras

    def initUI(self):
        layout = QVBoxLayout(self.view)

        self.cameraComboBox = QComboBox(self)
        for camera_index in self.available_cameras:
            self.cameraComboBox.addItem(f"摄像头 {camera_index}", camera_index)
        if not self.available_cameras:
            self.cameraComboBox.addItem("未检测到摄像头", -1)
            self.cameraComboBox.setEnabled(False)
        layout.addWidget(self.cameraComboBox)

        self.videoDisplayLabel = QLabel(self)
        self.videoDisplayLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.videoDisplayLabel.setStyleSheet("""
            background-color: #333;
            color: #fff;
            border-radius: 8px;
        """)
        self.videoDisplayLabel.setMinimumSize(640, 480)
        layout.addWidget(self.videoDisplayLabel)

        controlsLayout = QHBoxLayout()
        self.startButton = PrimaryPushButton("开始检测", self)
        self.startButton.clicked.connect(self.startCameraDetection) # type: ignore
        self.startButton.setEnabled(bool(self.available_cameras))
        controlsLayout.addWidget(self.startButton)

        self.stopButton = PrimaryPushButton("停止检测", self)
        self.stopButton.clicked.connect(self.stopCameraDetection) # type: ignore
        self.stopButton.setEnabled(False)
        controlsLayout.addWidget(self.stopButton)
        layout.addLayout(controlsLayout)

    def startCameraDetection(self):
        selected_camera_index = self.cameraComboBox.currentData()
        if selected_camera_index != -1 and self.detection_model:
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(True)
            confidence_threshold = self.main_window.confidenceSpinBox.value()
            max_detections = self.main_window.maxDetSpinBox.value()
            self.detection_thread = CameraDetectionThread(selected_camera_index, self.detection_model, conf=confidence_threshold, max_det=max_detections)
            self.detection_thread.processedFrameReady.connect(self.updateVideoFrame) # type: ignore
            self.detection_thread.detectionFinished.connect(self.cameraDetectionFinished) # type: ignore
            self.detection_thread.start()

    def stopCameraDetection(self):
        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.stop_flag = True
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)

    def updateVideoFrame(self, frame: QImage):
        pixmap = QPixmap.fromImage(frame)
        scaled_pixmap = pixmap.scaled(
            self.videoDisplayLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.videoDisplayLabel.setPixmap(scaled_pixmap)

    def cameraDetectionFinished(self):
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.videoDisplayLabel.setText("摄像头检测已停止")
        self.detection_thread = None

# ========================== 摄像头检测线程 ==========================
class CameraDetectionThread(QThread):
    processedFrameReady = Signal(QImage)
    detectionFinished = Signal()

    def __init__(self, camera_index, model, conf=0.25, max_det=1000):
        super().__init__()
        self.camera_index = camera_index
        self.model = model
        self.stop_flag = False
        self.conf = conf
        self.max_det = max_det

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Error: Could not open camera at index {self.camera_index}")
            self.detectionFinished.emit()
            return

        while not self.stop_flag and cap.isOpened():
            success, frame = cap.read()
            if success:
                results = self.model(frame, conf=self.conf, max_det=self.max_det)
                annotated_frame = results[0].plot()

                height, width, channel = annotated_frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(annotated_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
                self.processedFrameReady.emit(q_image)
            else:
                break
            time.sleep(0.03) # 控制帧率

        cap.release()
        self.detectionFinished.emit()

# ========================== 检测界面 ==========================
class DetectionInterface(ScrollArea):
    detectionResultReady = Signal(list)  # 新的信号，用于发送检测结果列表

    def __init__(self, main_window, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_window = main_window  # 保存 MainWindow 实例
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
        self.originalImageLabel.setMinimumSize(500, 400)
        imageLayout.addWidget(self.originalImageLabel)

        # 检测后图片显示标签
        self.detectedImageLabel = QLabel(self)
        self.detectedImageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detectedImageLabel.setStyleSheet("""
            background-color: #f0f0f0;
            border: 2px dashed #ccc;
            border-radius: 8px;
        """)
        self.detectedImageLabel.setMinimumSize(500, 400)
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
            confidence_threshold = self.main_window.confidenceSpinBox.value() # 从 MainWindow 获取值
            max_detections = self.main_window.maxDetSpinBox.value() # 从 MainWindow 获取值
            detection_results, detected_image = self.runDetection(path, conf=confidence_threshold, max_det=max_detections)
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


    def runDetection(self, image_path: str, conf: float = 0.25, max_det: int = 1000) -> Tuple[list, Optional[np.ndarray]]:
        results_list = []
        detected_image_np = None

        if self.detection_model is None:
            MessageBox("错误", "检测模型尚未加载", self).exec()
            return results_list, detected_image_np

        self.progressBar.show()
        try:
            results = self.detection_model(image_path, conf=conf, max_det=max_det)
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
        self.resize(1200, 800)
        setTheme(Theme.LIGHT)

        # 设置自定义标题栏样式
        self.titleBar.setStyleSheet("""
            QLabel {
                font-size: 20px; /* 增大字体 */
                color: #3498db; /* 设置颜色为蓝色 */
                padding-left: 15px; /* 增加左侧内边距 */
            }
        """)

        # 初始化界面
        self.detectionInterface = DetectionInterface(self) # 将 MainWindow 实例传递给 DetectionInterface
        self.videoDetectionInterface = VideoDetectionInterface(self) # 将 MainWindow 实例传递给 VideoDetectionInterface
        self.cameraDetectionInterface = CameraDetectionInterface(self) # 将 MainWindow 实例传递给 CameraDetectionInterface
        self.settingsInterface = QWidget()
        self.settingsInterface.setObjectName("SettingsInterface")

        # 添加导航
        self.addSubInterface(
            self.detectionInterface,
            FIF.PHOTO,
            "图片检测"
        )
        self.addSubInterface(
            self.videoDetectionInterface,
            FIF.VIDEO,
            "视频检测"
        )
        self.addSubInterface(
            self.cameraDetectionInterface,
            FIF.CAMERA,
            "实时检测"
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

        # 置信度阈值调节
        self.confidenceSpinBox = QDoubleSpinBox(self)
        self.confidenceSpinBox.setRange(0.0, 1.0)
        self.confidenceSpinBox.setSingleStep(0.01)
        self.confidenceSpinBox.setValue(0.25)  # 设置默认值
        layout.addRow(StrongBodyLabel("置信度阈值:"), self.confidenceSpinBox)

        # 最大检测数量调节
        self.maxDetSpinBox = QSpinBox(self)
        self.maxDetSpinBox.setRange(1, 10000)  # 设置一个合理的范围
        self.maxDetSpinBox.setSingleStep(10)
        self.maxDetSpinBox.setValue(1000)  # 设置默认值
        layout.addRow(StrongBodyLabel("最大检测数量:"), self.maxDetSpinBox)

        # 保存按钮
        self.saveBtn = PrimaryPushButton("保存设置")
        self.saveBtn.clicked.connect(self.saveSettings)  # type: ignore
        layout.addRow(self.saveBtn)

    def saveSettings(self):
        conf = self.confidenceSpinBox.value()
        max_det = self.maxDetSpinBox.value()
        MessageBox(
            "设置已保存",
            f"当前设置：\n置信度阈值: {conf}\n最大检测数量: {max_det}",
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