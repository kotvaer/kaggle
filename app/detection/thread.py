# import time
# from PyQt6.QtCore import QThread, pyqtSignal as Signal
#
# class DetectionThread(QThread):
#     progressUpdated = Signal(int)  # type: ignore
#     resultReady = Signal(dict)    # type: ignore
#
#     def __init__(self, image_path: str):
#         super().__init__()
#         self.image_path = image_path
#
#     def run(self):
#         # 模拟处理过程
#         for i in range(5):
#             time.sleep(0.5)
#             self.progressUpdated.emit((i + 1) * 20)
#
#         # 生成虚拟结果
#         self.resultReady.emit({
#             "weld_count": 3,
#             "defects": [
#                 {"position": (100, 150), "length": 12.5, "type": "裂纹"},
#                 {"position": (300, 450), "length": 8.2, "type": "气孔"},
#                 {"position": (500, 200), "length": 5.7, "type": "未熔合"}
#             ]
#         })

import cv2
import torch
from PyQt6.QtCore import QThread, pyqtSignal as Signal
from ultralytics import YOLO
from ultralytics.engine.results import Results


class DetectionThread(QThread):
    resultReady = Signal(str, float, object)  # (标签文本, 置信度, 图像数据)
    errorOccurred = Signal(str)

    def __init__(self, image_path: str, model_path: str = 'models/best.pt'):
        super().__init__()
        self.image_path = image_path
        self.model_path = model_path

    def run(self):
        try:
            # 加载模型
            model = YOLO(self.model_path, task='detect')

            # 执行推理
            results: Results = model.predict(
                source=self.image_path,
                conf=0.5,
                imgsz=640,
                device='cuda' if torch.cuda.is_available() else 'cpu'
            )

            # 提取检测信息
            label_text, confidence = self._parse_detection(results)

            # 生成可视化图像
            plotted_img = results[0].plot()
            rgb_image = cv2.cvtColor(plotted_img, cv2.COLOR_BGR2RGB)

            # 发射结果信号
            self.resultReady.emit(label_text, confidence, rgb_image)

        except Exception as e:
            self.errorOccurred.emit(f"检测错误: {str(e)}")

    def _parse_detection(self, results: Results):
        """解析检测结果中的标签和置信度"""
        if len(results[0].boxes) == 0:
            return "未检测到缺陷", 0.0

        # 获取置信度最高的检测结果
        max_conf_index = results[0].boxes.conf.argmax()
        class_id = int(results[0].boxes.cls[max_conf_index])
        confidence = float(results[0].boxes.conf[max_conf_index])

        # 根据你的实际类别映射修改
        class_mapping = {
            0: "焊接裂纹",
            1: "气孔缺陷",
            2: "未熔合缺陷"
        }

        return class_mapping.get(class_id, "未知缺陷"), round(confidence, 2)