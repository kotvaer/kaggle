from PyQt6.QtWidgets import QWidget, QFormLayout, QSlider, QDoubleSpinBox
from PyQt6.QtCore import Qt
from qfluentwidgets import PrimaryPushButton, StrongBodyLabel, MessageBox


class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsInterface")
        self._initUI()

    def _initUI(self):
        layout = QFormLayout(self)

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
        self.saveBtn.clicked.connect(self._saveSettings)  # type: ignore
        layout.addRow(self.saveBtn)

    def _saveSettings(self):
        sens = self.sensitivitySlider.value()
        threshold = self.thresholdSpinBox.value()
        MessageBox(
            "设置已保存",
            f"当前设置：\n灵敏度等级: {sens}\n报警阈值: {threshold}mm",
            self
        ).exec()