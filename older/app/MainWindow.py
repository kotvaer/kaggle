# from PyQt6.QtWidgets import QWidget
# from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, FluentIcon as FIF
# from app.detection.interface import DetectionInterface
# from app.settings.interface import SettingsInterface
#
#
# class MainWindow(FluentWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("智能焊缝检测系统")
#         self.resize(1200, 800)
#         setTheme(Theme.LIGHT)
#
#         # 初始化子界面
#         self.detection_interface = DetectionInterface()
#         self.settings_interface = SettingsInterface()
#
#         # 添加导航项
#         self.addSubInterface(
#             self.detection_interface,
#             FIF.VIDEO,
#             "焊缝检测"
#         )
#         self.addSubInterface(
#             self.settings_interface,
#             FIF.SETTING,
#             "系统设置",
#             position=NavigationItemPosition.BOTTOM
#         )


from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog
from qfluentwidgets import (PrimaryPushButton, BodyLabel, StrongBodyLabel, ProgressBar,
                            FluentIcon as FIF, MessageBox, InfoBar, InfoBarPosition)

from UI import DetectionThread


class DetectionInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.detection_thread = None

    def initUI(self):
        # 创建主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 操作按钮区域
        btn_layout = QHBoxLayout()
        self.select_btn = PrimaryPushButton("选择图片", self, FIF.PHOTO)
        self.detect_btn = PrimaryPushButton("开始检测", self, FIF.SEARCH)
        self.select_btn.clicked.connect(self.select_image)
        self.detect_btn.clicked.connect(self.start_detection)
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.detect_btn)

        # 进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.hide()

        # 图像显示区域
        img_layout = QHBoxLayout()
        self.original_label = QLabel("原始图片区域")
        self.result_label = QLabel("检测结果区域")
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_label.setStyleSheet("border: 2px dashed #cccccc;")
        self.result_label.setStyleSheet("border: 2px dashed #cccccc;")
        img_layout.addWidget(self.original_label)
        img_layout.addWidget(self.result_label)

        # 结果信息区域
        info_layout = QVBoxLayout()
        self.result_text = StrongBodyLabel("检测结果：等待检测...", self)
        self.confidence_text = BodyLabel("置信度：0.00", self)
        info_layout.addWidget(self.result_text)
        info_layout.addWidget(self.confidence_text)

        # 组合所有布局
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(img_layout)
        main_layout.addLayout(info_layout)

    def select_image(self):
        """选择图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择检测图片", "", "图片文件 (*.jpg *.png)")
        if file_path:
            self.current_image = file_path
            self.show_original_image(file_path)
            self.detect_btn.setEnabled(True)

    def show_original_image(self, path):
        """显示原始图片"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.original_label.width(),
                self.original_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio
            )
            self.original_label.setPixmap(scaled)

    def start_detection(self):
        """启动检测线程"""
        if hasattr(self, 'current_image'):
            self.progress_bar.show()
            self.detect_btn.setEnabled(False)

            self.detection_thread = DetectionThread(self.current_image)
            self.detection_thread.resultReady.connect(self.show_result)
            self.detection_thread.errorOccurred.connect(self.show_error)
            self.detection_thread.start()

    def show_result(self, label: str, conf: float, image_data):
        """显示检测结果"""
        # 更新进度条
        self.progress_bar.hide()
        self.progress_bar.setValue(0)

        # 显示结果图像
        height, width, _ = image_data.shape
        q_img = QImage(
            image_data.data,
            width,
            height,
            QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.result_label.width(),
            self.result_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.result_label.setPixmap(pixmap)

        # 更新文本信息
        self.result_text.setText(f"检测结果：{label}")
        self.confidence_text.setText(f"置信度：{conf:.2f}")
        self.detect_btn.setEnabled(True)

    def show_error(self, msg: str):
        """显示错误信息"""
        self.progress_bar.hide()
        MessageBox("错误", msg, self).exec()
        self.detect_btn.setEnabled(True)