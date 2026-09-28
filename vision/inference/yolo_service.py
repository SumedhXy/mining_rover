from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


class YOLOInferenceService:
    def __init__(self, model_path: Path | None = None):
        project_root = Path(__file__).resolve().parents[2]
        self.model_path = model_path or project_root / "vision" / "weights" / "best.pt"
        self._model: Any | None = None

    def detect(self, image_bytes: bytes) -> list[dict[str, Any]]:
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                image = image.convert("RGB")
        except UnidentifiedImageError as error:
            raise ValueError("Uploaded file is not a valid image") from error

        return self._predict(image)

    def detect_frame(self, frame: Any) -> list[dict[str, Any]]:
        return self._predict(frame)

    def ensure_model_loaded(self) -> None:
        self._load_model()

    def _predict(self, image: Any) -> list[dict[str, Any]]:
        model = self._load_model()
        detections = []
        for result in model.predict(image, verbose=False):
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                detections.append(
                    {
                        "class_name": result.names[class_id],
                        "confidence": float(box.conf[0].item()),
                        "bbox": [float(value) for value in box.xywh[0].tolist()],
                        "source": "yolo",
                    }
                )
        return detections

    def _load_model(self) -> Any:
        if self._model is None:
            if not self.model_path.is_file():
                raise FileNotFoundError(f"YOLO checkpoint not found: {self.model_path}")
            from ultralytics import YOLO

            self._model = YOLO(str(self.model_path))
        return self._model