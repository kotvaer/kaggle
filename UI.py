import sys
import time
from typing import Optional, Dict

from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QPixmap, QFont
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


# ========================== 线程类 ==========================
class DetectionThread(QThread):
    progressUpdated = Signal(int)
    resultReady = Signal(dict)

    def __init__(self, image_path: str):
        super().__init__()
        self.image_path = image_path

    def run(self):
        # 模拟处理过程
        for i in range(5):
            time.sleep(0.5)
            self.progressUpdated.emit((i + 1) * 20)

        # 虚拟检测结果
        result = {
            "weld_count": 3,
            "defects": [
                {"position": (100, 150), "length": 12.5, "type": "裂纹"},
                {"position": (300, 450), "length": 8.2, "type": "气孔"},
                {"position": (500, 200), "length": 5.7, "type": "未熔合"}
            ]
        }
        self.resultReady.emit(result)


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
        self.resultTable: TableWidget
        self.progressBar: IndeterminateProgressBar

        self.initUI()

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

        # 结果表格
        self.resultTable = TableWidget(self)
        self.resultTable.setColumnCount(4)
        self.resultTable.setHorizontalHeaderLabels(
            ["位置X", "位置Y", "长度(mm)", "缺陷类型"]
        )
        self.resultTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # 进度条
        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.hide()

        # 布局组装
        layout.addWidget(self.uploadBtn)
        layout.addSpacing(15)
        layout.addWidget(self.imageLabel)
        layout.addSpacing(25)
        layout.addWidget(StrongBodyLabel("检测结果:"))
        layout.addWidget(self.resultTable)
        layout.addWidget(self.progressBar)

    def uploadImage(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.loadImage(path)
            self.startDetection(path)

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

    def startDetection(self, path: str):
        self.progressBar.show()
        self.worker = DetectionThread(path)
        self.worker.progressUpdated.connect(self.updateProgress)  # type: ignore
        self.worker.resultReady.connect(self.showResults)  # type: ignore
        self.worker.start()

    def updateProgress(self, value: int):
        if value >= 100:
            self.progressBar.hide()

    def showResults(self, result: Dict):
        self.resultTable.clearContents()
        defects = result.get("defects", [])
        self.resultTable.setRowCount(len(defects))

        for row, defect in enumerate(defects):
            pos = defect.get("position", (0, 0))
            self.resultTable.setItem(row, 0, QTableWidgetItem(str(pos[0])))
            self.resultTable.setItem(row, 1, QTableWidgetItem(str(pos[1])))
            self.resultTable.setItem(row, 2,
                                     QTableWidgetItem(f"{defect.get('length', 0):.2f}"))
            self.resultTable.setItem(row, 3,
                                     QTableWidgetItem(defect.get("type", "未知")))


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