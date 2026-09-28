from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from database.database import SQLiteDatabase


class DecisionAPIService:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def add_decision(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        decision_id = payload.get("decision_id") or str(uuid.uuid4())[:12]
        hazard_type = payload.get("hazard_type") or payload.get("hazard") or "none"
        severity = payload.get("severity", "LOW")
        confidence = float(payload.get("confidence", 0.0) or 0.0)
        reasons = payload.get("reasons", [])
        if not reasons and payload.get("message"):
            reasons = [payload["message"]]
        elif not reasons and payload.get("reason"):
            reasons = [payload["reason"]]

        reasons_json = json.dumps(reasons) if reasons else None
        sensor_ev_json = json.dumps(payload.get("sensor_evidence", [])) if payload.get("sensor_evidence") else None
        vision_ev_json = json.dumps(payload.get("vision_evidence", [])) if payload.get("vision_evidence") else None

        self.database.insert_hazard_event(
            decision_id=decision_id,
            timestamp=timestamp,
            device_id=payload.get("device_id", "mining_rover_01"),
            hazard_type=hazard_type,
            severity=severity,
            confidence=confidence,
            reasons_json=reasons_json,
            sensor_evidence_json=sensor_ev_json,
            vision_evidence_json=vision_ev_json,
            source=",".join(payload.get("sources", ["decision_engine"])),
            message=reasons[0] if reasons else payload.get("message") or "Decision evaluated",
            recommended_action=payload.get("recommended_action") or "MONITOR",
        )
        return {"status": "accepted", "timestamp": timestamp, "decision_id": decision_id}

    def _parse_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        reasons = []
        if row.get("reasons_json"):
            try:
                parsed = json.loads(row["reasons_json"])
                reasons = parsed if isinstance(parsed, list) else [str(parsed)]
            except Exception:
                reasons = [row["reasons_json"]]
        elif row.get("message"):
            reasons = [row["message"]]

        sensor_ev = []
        if row.get("sensor_evidence_json"):
            try:
                parsed = json.loads(row["sensor_evidence_json"])
                sensor_ev = parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                pass

        vision_ev = []
        if row.get("vision_evidence_json"):
            try:
                parsed = json.loads(row["vision_evidence_json"])
                vision_ev = parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                pass

        h_type = row.get("hazard_type") or row.get("hazard") or "none"
        primary_reason = reasons[0] if reasons else row.get("message") or "Nominal"

        return {
            "decision_id": row.get("decision_id"),
            "timestamp": row.get("timestamp"),
            "hazard_type": h_type,
            "hazard": h_type,  # UI dashboard backwards compatibility alias
            "severity": row.get("severity", "LOW"),
            "confidence": float(row.get("confidence", 0.0) or 0.0),
            "reasons": reasons,
            "reason": primary_reason,  # UI dashboard backwards compatibility alias
            "sensor_evidence": sensor_ev,
            "vision_evidence": vision_ev,
            "all_hazards": [{"hazard_type": h_type, "severity": row.get("severity", "LOW")}],
            "recommended_action": row.get("recommended_action", "MONITOR"),
            "sources": [s.strip() for s in (row.get("sources") or row.get("source") or "").split(",") if s.strip()],
        }

    def latest(self) -> Dict[str, Any]:
        rows = self.database.get_recent_hazards(limit=1)
        if not rows:
            return {
                "decision_id": None,
                "timestamp": None,
                "hazard_type": "none",
                "hazard": "none",
                "severity": "LOW",
                "confidence": 0.0,
                "reasons": ["No decision available"],
                "reason": "No decision available",
                "sensor_evidence": [],
                "vision_evidence": [],
                "all_hazards": [],
                "recommended_action": "MONITOR",
                "sources": [],
            }
        return self._parse_row(rows[0])

    def history(
        self,
        limit: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        severity: Optional[str] = None,
        hazard_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self.database.connect()
        try:
            query = "SELECT * FROM hazard_events WHERE 1=1"
            params: List[Any] = []
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            if severity:
                query += " AND UPPER(severity) = ?"
                params.append(severity.upper())
            if hazard_type:
                query += " AND (UPPER(hazard_type) = ? OR UPPER(hazard) = ?)"
                params.append(hazard_type.upper())
                params.append(hazard_type.upper())

            query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._parse_row(dict(r)) for r in rows]
        finally:
            conn.close()
