import sys
import random
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import asyncio
import socket
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt, pyqtSignal

FinalMax = None


class VideoCaptureWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize counters for objects in each rectangle
        self.rect1_object_count = 0
        self.rect2_object_count = 0
        self.rect3_object_count = 0
        self.rect4_object_count = 0

        self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            print("Cannot open the camera")
            exit()

        # Main layout
        self.layout = QHBoxLayout(self)

        # QLabel for the main video feed
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.video_label, 3)

        # Layout for the cropped rectangles and object counts
        side_layout = QGridLayout()

        # QLabels for cropped rectangles and object counts
        self.rect_labels = []
        self.count_labels = []
        for i in range(4):
            rect_label = QLabel(self)
            rect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label = QLabel(f"Rect {i + 1}: total object 00", self)
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rect_labels.append(rect_label)
            self.count_labels.append(count_label)
            side_layout.addWidget(count_label, i % 2, 2 * (i // 2) + 1)
            side_layout.addWidget(rect_label, i % 2, 2 * (i // 2))

        self.layout.addLayout(side_layout, 2)

        # Timer to update the video feed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update frame every 30 ms

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        image_height, image_width = frame.shape[:2]

        # Define the four rectangles for cropping
        horizontal_rect_height = int(image_height * 30.5 / 100)
        horizontal_rect_width = int(image_width * 35 / 100)

        vertical_rect_width = int(image_width * 30.5 / 100)
        vertical_rect_height = int(image_height * 35 / 100)

        padding = int(min(image_width, image_height) * 0.01)

        rect4 = frame[vertical_rect_height:vertical_rect_height + horizontal_rect_height,
                0:horizontal_rect_width + padding * 5]
        rect1 = frame[0:vertical_rect_height,
                horizontal_rect_width + padding * 5:vertical_rect_height + horizontal_rect_width]
        rect2 = frame[vertical_rect_height + padding * 2:vertical_rect_height + horizontal_rect_height,
                horizontal_rect_width + vertical_rect_height:horizontal_rect_width + horizontal_rect_width + vertical_rect_height + padding * 5]
        rect3 = frame[
                vertical_rect_height + horizontal_rect_height:vertical_rect_height + horizontal_rect_height + horizontal_rect_height + padding * 6,
                horizontal_rect_width + padding * 5:vertical_rect_height + horizontal_rect_width]

        # List to hold the cropped frames and their corresponding object counts
        frames = [rect1, rect2, rect3, rect4]
        counts = []

        for i, rect in enumerate(frames):
            # Predict on the cropped rectangle
            detect_params = model.predict(source=[rect], conf=0.45, save=False)
            DP = detect_params[0].cpu().numpy()
            object_count = 0

            if len(DP) != 0:
                for j in range(len(detect_params[0].boxes)):
                    boxes = detect_params[0].boxes
                    box = boxes[j]
                    clsID = int(box.cls.cpu().numpy()[0])
                    bb = box.xyxy.cpu().numpy()[0]

                    # Check if the detected object is a car
                    if class_list[clsID] == "car":
                        object_count += 1
                        cv2.rectangle(
                            rect,
                            (int(bb[0]), int(bb[1])),
                            (int(bb[2]), int(bb[3])),
                            detection_colors[clsID],
                            2,
                        )

            # Resize the rectangle for display
            resized_rect = cv2.resize(rect, (480, 360))
            # Add the object count label to the cropped frame
            frame_name = f"Frame {i + 1}"
            cv2.putText(resized_rect, frame_name, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(resized_rect, f"Cars: {object_count}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255),
                        2)
            frames[i] = resized_rect  # Replace with the resized and labeled frame
            counts.append(object_count)

            # Convert the resized frame to QImage and display it in the corresponding label
            qimg = QImage(resized_rect.data, resized_rect.shape[1], resized_rect.shape[0], QImage.Format.Format_RGB888)
            self.rect_labels[i].setPixmap(QPixmap.fromImage(qimg).scaled(
                self.rect_labels[i].width(), self.rect_labels[i].height(), Qt.AspectRatioMode.KeepAspectRatio))

        # Display the original frame in the main video label
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(frame_rgb.data, frame_rgb.shape[1], frame_rgb.shape[0], QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio))

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


async def send_command(client_socket, command):
    client_socket.send(command.encode('utf-8'))
    print(f"Sent command: {command}")


async def control_lights(client_socket):
    global FinalMax
    try:
        while True:
            selected_light = FinalMax
            if selected_light == None:
                for i in range(1, 5):
                    command = f"light{i}_green_on"
                    await send_command(client_socket, command)
                    await asyncio.sleep(0.1)
            else:
                command = f"light{selected_light}_green_on"
                await send_command(client_socket, command)
                await asyncio.sleep(0.1)
                command = f"light{selected_light}_red_off"
                await send_command(client_socket, command)
                await asyncio.sleep(0.1)
                command = f"light{selected_light}_yellow_off"
                await send_command(client_socket, command)
                await asyncio.sleep(0.1)

                for i in range(1, 5):
                    if i != selected_light:
                        yellow_command = f"light{i}_yellow_on"
                        await send_command(client_socket, yellow_command)
                        await asyncio.sleep(0.1)
                await asyncio.sleep(2)

                for i in range(1, 5):
                    if i != selected_light:
                        red_command = f"light{i}_red_on"
                        await send_command(client_socket, red_command)
                        await asyncio.sleep(0.1)
                await asyncio.sleep(5)
    except KeyboardInterrupt:
        print("\nClient is shutting down...")


async def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = '192.168.1.203'  # Replace with your Raspberry Pi's IP address
    port = 9999

    await asyncio.get_event_loop().run_in_executor(None, client_socket.connect, (host, port))
    print(f"Connected to server at {host}:{port}")

    try:
        await control_lights(client_socket)
    finally:
        client_socket.close()


def run_async_loop():
    asyncio.run(start_client())


def main():
    global model, class_list, detection_colors

    # Load the YOLOv8 model
    model = YOLO("weights/yolov8n.pt", "v8")

    # Load class names
    with open("coco.txt", "r") as my_file:
        class_list = my_file.read().split("\n")

    # Generate random colors for the class list
    detection_colors = []
    for i in range(len(class_list)):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        detection_colors.append((b, g, r))

    # Initialize PyQt Application
    app = QApplication(sys.argv)
    window = VideoCaptureWidget()

    # Set the window size to match the screen size
    screen = app.primaryScreen()
    rect = screen.availableGeometry()
    window.setGeometry(rect)

    window.setWindowTitle('Object Detection with PyQt6')
    window.show()

    # Start the async client in a separate thread
    async_thread = threading.Thread(target=run_async_loop)
    async_thread.start()

    # Execute the PyQt application
    sys.exit(app.exec())

    # Join the async thread after the PyQt application exits
    async_thread.join()


if __name__ == '__main__':
    main()
