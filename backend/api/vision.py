from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from backend.schemas.vision import (
    VisionHistoryResponse,
    VisionLatestResponse,
    VisionPayload,
)
from backend.services.vision_service import VisionAPIService
from vision.inference.camera_stream import CameraStreamService
from vision.inference.yolo_service import YOLOInferenceService

logger = logging.getLogger("backend.api.vision")

router = APIRouter(prefix="/api/vision", tags=["vision"])
service: VisionAPIService | None = None
inference_service = YOLOInferenceService()
camera_stream_service = CameraStreamService(inference_service)
camera_page_path = Path(__file__).resolve().parents[2] / "dashboard" / "camera.html"


@router.get("/latest", response_model=VisionLatestResponse, summary="Get latest vision detections")
def latest_vision() -> Dict[str, Any]:
    """Return the latest YOLO detections from SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Vision service unavailable")
    return service.latest()


@router.get("/history", response_model=VisionHistoryResponse, summary="Get historical vision detections")
def vision_history(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum detections to return"),
    start_time: Optional[str] = Query(default=None, description="ISO timestamp start filter"),
    end_time: Optional[str] = Query(default=None, description="ISO timestamp end filter"),
) -> Dict[str, Any]:
    """Return historical vision detections stored in SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Vision service unavailable")
    items = service.history(limit=limit, start_time=start_time, end_time=end_time)
    return {"items": items, "count": len(items)}


@router.post("", summary="Submit vision detection")
def submit_vision(payload: VisionPayload) -> Dict[str, Any]:
    """Store vision detection results into SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Vision service unavailable")
    return service.add_detection(payload.model_dump(exclude_none=True))


@router.post("/detect", summary="Run YOLO inference on image")
async def detect_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload an image frame, run YOLO detection, and store results."""
    if service is None:
        raise HTTPException(status_code=503, detail="Vision service unavailable")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")

    try:
        detections = inference_service.detect(image_bytes)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ImportError as error:
        raise HTTPException(status_code=503, detail="Install project requirements to enable vision inference") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.error(f"Inference error: {error}")
        raise HTTPException(status_code=503, detail=f"Inference failed: {error}") from error

    result = service.add_detection({"detections": detections})
    return {**result, "detections": detections}


@router.get("/camera", response_class=FileResponse, summary="Live camera test page")
def camera_page() -> FileResponse:
    return FileResponse(camera_page_path)


@router.get("/camera/devices", summary="List available video camera devices")
def list_cameras() -> List[Dict[str, Any]]:
    return CameraStreamService.list_available_cameras()


@router.get("/camera/stream", summary="Live MJPEG camera video stream")
def camera_video(camera_index: int = 0, yolo: bool = True) -> StreamingResponse:
    """Stream MJPEG frames from rover camera. Fails gracefully with 503 if camera unavailable."""
    try:
        try:
            inference_service.ensure_model_loaded()
        except Exception:
            pass  # Allow raw optical stream even if YOLO model weights missing

        try:
            camera = camera_stream_service.open_camera(camera_index=camera_index)
        except TypeError:
            camera = camera_stream_service.open_camera()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ImportError as error:
        raise HTTPException(status_code=503, detail="Install project requirements to enable camera inference") from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.error(f"Camera stream initialization failed: {error}")
        raise HTTPException(status_code=503, detail="Could not open camera stream") from error

    return StreamingResponse(
        camera_stream_service.stream_frames(camera, run_yolo=yolo),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
