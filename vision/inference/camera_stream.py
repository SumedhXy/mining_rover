from __future__ import annotations

import os
from typing import Any, Iterator

from vision.inference.yolo_service import YOLOInferenceService


class CameraStreamService:
    def __init__(self, inference_service: YOLOInferenceService, camera_index: int | None = None):
        self.inference_service = inference_service
        self.camera_index = camera_index if camera_index is not None else int(os.getenv("ROVER_CAMERA_INDEX", "0"))

    @staticmethod
    def list_available_cameras(max_tested: int = 4) -> list[dict[str, Any]]:
        import cv2

        cameras = []
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        for idx in range(max_tested):
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        cameras.append({
                            "index": idx,
                            "name": f"USB Video Device {idx}" if idx == 0 else f"Camera Device {idx}",
                            "resolution": f"{int(frame.shape[1])}x{int(frame.shape[0])}",
                            "active": True,
                        })
            except Exception:
                continue
        return cameras

    def open_camera(self, camera_index: int | None = None) -> Any:
        import cv2

        target_index = self.camera_index if camera_index is None else camera_index
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        camera = cv2.VideoCapture(target_index, backend)
        if not camera.isOpened():
            camera.release()
            raise RuntimeError(
                f"Could not open camera {target_index}. Check the USB connection or set ROVER_CAMERA_INDEX."
            )
        # Minimize buffer latency for live real-time preview
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return camera

    def stream_frames(self, camera: Any, run_yolo: bool = True) -> Iterator[bytes]:
        import cv2

        try:
            while True:
                success, frame = camera.read()
                if not success or frame is None:
                    break

                if run_yolo:
                    try:
                        for detection in self.inference_service.detect_frame(frame):
                            self._draw_detection(cv2, frame, detection)
                    except Exception:
                        # Graceful fallback: continue streaming camera feed even if a model frame fails
                        pass

                encoded_success, encoded_image = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                )
                if encoded_success:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_image.tobytes() + b"\r\n"
        finally:
            camera.release()

    @staticmethod
    def _draw_detection(cv2: Any, frame: Any, detection: dict[str, Any]) -> None:
        x_center, y_center, width, height = detection["bbox"]
        x_min = int(x_center - width / 2)
        y_min = int(y_center - height / 2)
        x_max = int(x_center + width / 2)
        y_max = int(y_center + height / 2)
        color = (64, 220, 150)
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)

        label = f"{detection['class_name']} {detection['confidence']:.0%}"
        cv2.putText(frame, label, (x_min, max(y_min - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)