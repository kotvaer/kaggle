import flet as ft
import torch
from ultralytics import YOLO
import cv2
import numpy as np
import threading
import time
from typing import List, Tuple, Optional

# Load YOLO model (can be done globally or within the main function)
try:
    detection_model = YOLO('models/best.pt', task='detect')
except Exception as e:
    print(f"Error loading model: {e}")
    detection_model = None

class DetectionResult:
    def __init__(self, label: str, confidence: float):
        self.label = label
        self.confidence = confidence

class VideoDetectionThread(threading.Thread):
    def __init__(self, video_path, conf, max_det, frame_callback, finished_callback):
        super().__init__()
        self.video_path = video_path
        self.conf = conf
        self.max_det = max_det
        self.frame_callback = frame_callback
        self.finished_callback = finished_callback
        self.stop_flag = False

    def run(self):
        if detection_model is None:
            self.finished_callback()
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video at {self.video_path}")
            self.finished_callback()
            return

        while not self.stop_flag and cap.isOpened():
            success, frame = cap.read()
            if success:
                results = detection_model(frame, conf=self.conf, max_det=self.max_det)
                annotated_frame = results[0].plot()
                # Convert frame to bytes for Flet Image control
                _, img_bytes = cv2.imencode('.jpg', annotated_frame)
                self.frame_callback(img_bytes.tobytes())
            else:
                break
            time.sleep(0.03)

        cap.release()
        self.finished_callback()

class CameraDetectionThread(threading.Thread):
    def __init__(self, camera_index, conf, max_det, frame_callback, finished_callback):
        super().__init__()
        self.camera_index = camera_index
        self.conf = conf
        self.max_det = max_det
        self.frame_callback = frame_callback
        self.finished_callback = finished_callback
        self.stop_flag = False

    def run(self):
        if detection_model is None:
            self.finished_callback()
            return

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print(f"Error: Could not open camera at index {self.camera_index}")
            self.finished_callback()
            return

        while not self.stop_flag and cap.isOpened():
            success, frame = cap.read()
            if success:
                results = detection_model(frame, conf=self.conf, max_det=self.max_det)
                annotated_frame = results[0].plot()
                _, img_bytes = cv2.imencode('.jpg', annotated_frame)
                self.frame_callback(img_bytes.tobytes())
            else:
                break
            time.sleep(0.03)

        cap.release()
        self.finished_callback()

def main(page: ft.Page):
    page.title = "智能焊缝检测系统"
    page.window_width = 1200
    page.window_height = 800

    confidence_ref = ft.Ref[ft.TextField]()
    max_det_ref = ft.Ref[ft.TextField]()
    original_image = ft.Ref[ft.Image]()
    detected_image = ft.Ref[ft.Image]()
    result_table = ft.Ref[ft.DataTable]()
    video_display = ft.Ref[ft.Image]()
    camera_display = ft.Ref[ft.Image]()
    progress_bar = ft.Ref[ft.ProgressBar]()
    camera_dropdown = ft.Ref[ft.Dropdown]()

    video_detection_thread = None
    camera_detection_thread = None
    video_path = None

    def load_detection_model():
        # Model loading is done globally for simplicity
        pass

    def update_settings(e):
        page.update()

    def select_video_file(e):
        file_picker.pick_files(allowed_extensions=['mp4', 'avi', 'mov', 'mkv'])

    def start_video_detection(e):
        nonlocal video_detection_thread
        if video_path and detection_model:
            progress_bar.current.visible = True
            page.update()
            conf = float(confidence_ref.current.value) if confidence_ref.current.value else 0.25
            max_det = int(max_det_ref.current.value) if max_det_ref.current.value else 1000

            def frame_callback(img_bytes):
                video_display.current.src_base64 = img_bytes.decode('base64')
                page.update()

            def finished_callback():
                progress_bar.current.visible = False
                page.update()

            video_detection_thread = VideoDetectionThread(video_path, conf, max_det, frame_callback, finished_callback)
            video_detection_thread.start()

    def stop_video_detection(e):
        nonlocal video_detection_thread
        if video_detection_thread and video_detection_thread.is_alive():
            video_detection_thread.stop_flag = True

    def start_camera_detection(e):
        nonlocal camera_detection_thread
        selected_camera = camera_dropdown.current.value
        if selected_camera is not None and detection_model:
            progress_bar.current.visible = True
            page.update()
            conf = float(confidence_ref.current.value) if confidence_ref.current.value else 0.25
            max_det = int(max_det_ref.current.value) if max_det_ref.current.value else 1000

            def frame_callback(img_bytes):
                camera_display.current.src_base64 = img_bytes.decode('base64')
                page.update()

            def finished_callback():
                progress_bar.current.visible = False
                page.update()

            camera_detection_thread = CameraDetectionThread(int(selected_camera), conf, max_det, frame_callback, finished_callback)
            camera_detection_thread.start()

    def stop_camera_detection(e):
        nonlocal camera_detection_thread
        if camera_detection_thread and camera_detection_thread.is_alive():
            camera_detection_thread.stop_flag = True

    def on_file_picked(e: ft.FilePickerResult):
        nonlocal video_path
        if e.files and len(e.files) > 0:
            video_path = e.files[0].path
            page.snack_bar = ft.SnackBar(ft.Text(f"Selected video: {video_path}"))
            page.snack_bar.open = True
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    def upload_image(e):
        file_picker.pick_files(allowed_extensions=['png', 'jpg', 'jpeg', 'bmp'])

    def process_image(path):
        if detection_model is None:
            return [], None
        conf = float(confidence_ref.current.value) if confidence_ref.current.value else 0.25
        max_det = int(max_det_ref.current.value) if max_det_ref.current.value else 1000
        results = detection_model(path, conf=conf, max_det=max_det)
        annotated_frame = results[0].plot()
        _, img_bytes = cv2.imencode('.jpg', annotated_frame)
        detected_image_bytes = img_bytes.tobytes()
        detection_results = []
        if results and results[0].boxes and len(results[0].boxes.conf) > 0:
            for i in range(len(results[0].boxes.conf)):
                confidence = results[0].boxes.conf[i].item()
                class_id = results[0].boxes.cls[i].item()
                label = results[0].names[class_id]
                detection_results.append(DetectionResult(label, confidence))
        return detection_results, detected_image_bytes

    def display_image_result(e: ft.FilePickerResult):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            original_image.current.src = file_path
            results, detected_bytes = process_image(file_path)
            if detected_bytes:
                detected_image.current.src_base64 = detected_bytes.decode('base64')
                detected_image.current.visible = True
            else:
                detected_image.current.visible = False

            rows = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(res.label)), ft.DataCell(ft.Text(f"{res.confidence:.2f}"))])
                for res in results
            ]
            result_table.current.rows = rows
            page.update()

    image_file_picker = ft.FilePicker(on_result=display_image_result)
    page.overlay.append(image_file_picker)

    def show_image_upload_dialog(e):
        image_file_picker.pick_files(allowed_extensions=['png', 'jpg', 'jpeg', 'bmp'])

    def get_available_cameras():
        index = 0
        cameras = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                cameras.append(str(index))
            cap.release()
            index += 1
        return cameras

    available_cameras = get_available_cameras()
    camera_dropdown_items = [ft.dropdown.Option(camera) for camera in available_cameras]
    camera_dropdown_control = ft.Dropdown(
        ref=camera_dropdown,
        label="选择摄像头",
        options=camera_dropdown_items,
        disabled=not available_cameras
    )

    tabs = ft.Tabs(
        expand=True,
        tabs=[
            ft.Tab(
                text="图片检测",
                content=ft.Column([
                    ft.ElevatedButton("上传焊缝图片", on_click=show_image_upload_dialog, icon=ft.icons.PHOTO),
                    ft.Row([
                        ft.Container(ref=original_image, width=500, height=400, bgcolor=ft.colors.GREY_300, alignment=ft.alignment.center),
                        ft.Container(ref=detected_image, width=500, height=400, bgcolor=ft.colors.GREY_400, visible=False, alignment=ft.alignment.center),
                    ]),
                    ft.Text("检测结果:", weight=ft.FontWeight.BOLD),
                    ft.DataTable(
                        ref=result_table,
                        columns=[
                            ft.DataColumn(ft.Text("缺陷类型")),
                            ft.DataColumn(ft.Text("置信度")),
                        ],
                        rows= [],
                    ),
                ])
            ),
            ft.Tab(
                text="视频检测",
                content=ft.Column([
                    ft.ElevatedButton("选择视频文件", on_click=select_video_file, icon=ft.icons.FOLDER),
                    ft.Container(ref=video_display, width=640, height=480, bgcolor=ft.colors.BLACK),
                    ft.Row([
                        ft.ElevatedButton("开始检测", on_click=start_video_detection, disabled=True),
                        ft.ElevatedButton("停止检测", on_click=stop_video_detection),
                    ]),
                    ft.ProgressBar(ref=progress_bar, visible=False),
                ])
            ),
            ft.Tab(
                text="实时检测",
                content=ft.Column([
                    camera_dropdown_control,
                    ft.Container(ref=camera_display, width=640, height=480, bgcolor=ft.colors.BLACK),
                    ft.Row([
                        ft.ElevatedButton("开始检测", on_click=start_camera_detection, disabled=True),
                        ft.ElevatedButton("停止检测", on_click=stop_camera_detection),
                    ]),
                    ft.ProgressBar(ref=progress_bar, visible=False),
                ])
            ),
            ft.Tab(
                text="系统设置",
                content=ft.Column([
                    ft.TextField(ref=confidence_ref, label="置信度阈值", value="0.25", keyboard_type=ft.KeyboardType.NUMBER),
                    ft.TextField(ref=max_det_ref, label="最大检测数量", value="1000", keyboard_type=ft.KeyboardType.NUMBER),
                    ft.ElevatedButton("保存设置", on_click=update_settings),
                ])
            ),
        ]
    )

    page.add(tabs, file_picker)

    # Enable video start button after file is picked
    def update_video_button_state(e):
        tabs.tabs[1].content.controls[2].controls[0].disabled = video_path is None
        page.update()

    file_picker.on_result = lambda e: (on_file_picked(e), update_video_button_state(None))

    # Enable camera start button after camera is selected
    def update_camera_button_state(e):
        tabs.tabs[2].content.controls[2].controls[0].disabled = camera_dropdown.current.value is None
        page.update()

    camera_dropdown.current.on_change = update_camera_button_state

if __name__ == "__main__":
    ft.app(target=main)