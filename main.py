import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from app import MainWindow


def run():
    app = QApplication(sys.argv)

    # 配置全局字体
    font = QFont()
    font.setFamilies(["Microsoft YaHei", "PingFang SC"])
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()