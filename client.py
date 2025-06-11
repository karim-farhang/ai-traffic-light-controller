import sys
import random
import cv2
from ultralytics import YOLO
import torch
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt, pyqtSignal

# Open the file in read mode for class names
with open("coco.txt", "r") as my_file:
    class_list = my_file.read().split("\n")

# Generate random colors for the class list
detection_colors = []
for i in range(len(class_list)):
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    detection_colors.append((b, g, r))

# Check if CUDA is available and set the device
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Load a pretrained YOLOv8n model and move it to the appropriate device
model = YOLO("weights/yolov8n.pt", "v8").to(device)

# Define the rectangle coordinates (hardcoded for demonstration)
rectangles = [
    [(207, 150), (301, 156), (309, 2), (213, 0)],  # Rectangle 1 coordinates
    [(396, 153), (382, 256), (639, 250), (638, 165)],  # Rectangle 2 coordinates
    [(292, 325), (384, 340), (380, 477), (286, 476)],  # Rectangle 3 coordinates
    [(208, 243), (200, 329), (1, 321), (3, 234)],  # Rectangle 4 coordinates
]


class VideoCaptureWidget(QWidget):
    text_changed_signal = pyqtSignal(int, str)

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

            # Connect the text changed signal to a custom slot
            self.text_changed_signal.connect(self.on_text_changed)

        self.layout.addLayout(side_layout, 2)

        # Timer to update the video feed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update frame every 30 ms

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # Iterate through each rectangle and process them independently
        for rect_index, rect in enumerate(rectangles):
            # Define the bounding box of the rectangle for cropping
            x_min = min(point[0] for point in rect)
            y_min = min(point[1] for point in rect)
            x_max = max(point[0] for point in rect)
            y_max = max(point[1] for point in rect)

            # Crop the region of interest (ROI)
            cropped_frame = frame[y_min:y_max, x_min:x_max]

            # Predict on cropped frame
            detect_params_rect = model.predict(source=[cropped_frame], conf=0.25, save=False, device=device)

            # Check if objects were detected
            if detect_params_rect and len(detect_params_rect[0].boxes) > 0:
                # Count the number of objects in the rectangle
                object_count = len(detect_params_rect[0].boxes)

                # Update the corresponding rectangle object count variable
                if rect_index == 0:
                    self.rect1_object_count = object_count
                elif rect_index == 1:
                    self.rect2_object_count = object_count
                elif rect_index == 2:
                    self.rect3_object_count = object_count
                elif rect_index == 3:
                    self.rect4_object_count = object_count

                # Update the count label
                new_text = f"Rect {rect_index + 1}: total object {object_count:02}"
                if self.count_labels[rect_index].text() != new_text:
                    self.count_labels[rect_index].setText(new_text)
                    self.text_changed_signal.emit(rect_index, new_text)

            # Convert cropped frame to QImage and display it dynamically
            cropped_frame = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = cropped_frame.shape
            bytes_per_line = ch * w
            qimg = QImage(cropped_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.rect_labels[rect_index].setPixmap(QPixmap.fromImage(qimg).scaled(
                self.rect_labels[rect_index].width(), self.rect_labels[rect_index].height(),
                Qt.AspectRatioMode.KeepAspectRatio))

            # Draw the rectangle by connecting each point
            cv2.line(frame, rect[0], rect[1], (0, 255, 255), 2)
            cv2.line(frame, rect[1], rect[2], (0, 255, 255), 2)
            cv2.line(frame, rect[2], rect[3], (0, 255, 255), 2)
            cv2.line(frame, rect[3], rect[0], (0, 255, 255), 2)

        # Resize the frame for the main video feed
        qimg = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio))

    def on_text_changed(self, index, new_text):
        object_counts = [
            self.rect1_object_count,
            self.rect2_object_count,
            self.rect3_object_count,
            self.rect4_object_count,
        ]

        max_count = max(object_counts)
        min_count = min(object_counts)
        mid_count = sorted(object_counts)[2]  # The second largest (middle) value

        for i, count_label in enumerate(self.count_labels):
            if object_counts[i] == max_count:
                count_label.setStyleSheet("color: red;")
            elif object_counts[i] == mid_count:
                count_label.setStyleSheet("color: yellow;")
            else:
                count_label.setStyleSheet("color: green;")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = VideoCaptureWidget()

    # Set the window size to match the screen size
    screen = app.primaryScreen()
    rect = screen.availableGeometry()
    window.setGeometry(rect)

    window.setWindowTitle('Object Detection with PyQt6')
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
