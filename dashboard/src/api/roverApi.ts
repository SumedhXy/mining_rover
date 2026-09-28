/**
 * Rover API Client Layer
 * 
 * Integrated HTTP Client connecting the React Console to the FastAPI Backend.
 * Follows an offline-first model:
 * - Direct querying of local FastAPI/SQLite endpoints
 * - Isolated subsystem failures (one endpoint error does not crash other components)
 * - Transparent mapping of environmental sensors, decisions, vision, missions, logs, and sync
 * - Fallback to simulation data only when explicit simulation mode is enabled or backend unreachable
 */

import {
  SensorItem,
  VisionDetection,
  DecisionData,
  MissionInfo,
  MissionEvent,
  RoverSystemInfo,
  EventType,
  TelemetryPoint,
  SeverityLevel,
  SyncStatusInfo,
  ObservationData,
} from '../types/rover';
import {
  mockSensors,
  mockDecision,
  mockVisionDetections,
  mockCurrentMission,
  mockTimelineEvents,
  mockMissionsList,
  mockSystemStatus,
  mockScenariosData,
  mockTelemetryHistory,
  MockScenario,
} from '../data/mockData';

// API Base URL - Uses Vite proxy in development or direct host
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || '';

let currentScenario: MockScenario = 'nominal';
let backendConnected: boolean = false;
let forceSimulationMode: boolean = false;

/**
 * Robust fetch helper with timeout and fallback
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 2500): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const finalUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
    const response = await fetch(finalUrl, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {}),
      },
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const roverApi = {
  /**
   * Set active mock scenario
   */
  setScenario(sc: MockScenario) {
    currentScenario = sc;
  },

  getScenario(): MockScenario {
    return currentScenario;
  },

  /**
   * Toggle between live backend telemetry and simulation mode
   */
  setForceSimulation(enabled: boolean) {
    forceSimulationMode = enabled;
  },

  isForceSimulation(): boolean {
    return forceSimulationMode;
  },

  isBackendOnline(): boolean {
    return backendConnected;
  },

  /**
   * Check if FastAPI backend is healthy and responding (GET /api/health)
   */
  async checkBackendHealth(): Promise<boolean> {
    try {
      const res = await fetchWithTimeout('/api/health', {}, 1800);
      backendConnected = res.ok;
      return res.ok;
    } catch {
      backendConnected = false;
      return false;
    }
  },

  /**
   * GET /api/sensors/latest
   * Fetches real environmental telemetry from FastAPI:
   * - Temperature (°C)
   * - Humidity (%)
   * - Pressure (hPa)
   * - MQ-4 (Methane raw ratio)
   * - MQ-135 (Air Quality raw ratio)
   * - Battery (%) & Vibration (g)
   */
  async getLatestSensors(): Promise<SensorItem[]> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/sensors/latest');
        if (res.ok) {
          backendConnected = true;
          const data = await res.json();
          const readings = Array.isArray(data.readings) ? data.readings : [];
          
          const readingMap: Record<string, { value: number; unit: string }> = {};
          for (const r of readings) {
            if (r.sensor_type && r.value !== undefined) {
              readingMap[r.sensor_type] = { value: Number(r.value), unit: r.unit || '' };
            }
          }

          // Prefer direct Phase 4 properties, then readings list, then defaults
          const tempVal = Number(data.temperature_c ?? readingMap.temperature?.value ?? 24.5);
          const humVal = Number(data.humidity_percent ?? readingMap.humidity?.value ?? 52.0);
          const pressVal = Number(data.pressure_hpa ?? readingMap.pressure?.value ?? 1013.25);
          const mq4Val = Number(data.mq4 ?? readingMap.gas?.value ?? 0.12);
          const mq135Val = Number(data.mq135 ?? readingMap.smoke?.value ?? 0.08);
          const batVal = Number(readingMap.battery?.value ?? 96.0);
          const vibVal = Number(readingMap.vibration?.value ?? 0.12);

          const items: SensorItem[] = [
            {
              id: 'temp',
              label: 'TEMPERATURE',
              value: Number(tempVal.toFixed(1)),
              unit: '°C',
              status: tempVal > 48 ? 'CRITICAL' : tempVal > 35 ? 'WARNING' : 'NORMAL',
              min: 0,
              max: 60,
              nominalRange: '15.0 - 35.0 °C',
              source: data.source || 'esp32_sensor_01',
            },
            {
              id: 'hum',
              label: 'HUMIDITY',
              value: Number(humVal.toFixed(1)),
              unit: '%',
              status: humVal > 85 ? 'WARNING' : humVal < 15 ? 'WARNING' : 'NORMAL',
              min: 0,
              max: 100,
              nominalRange: '30.0 - 75.0 %',
              source: data.source || 'esp32_sensor_01',
            },
            {
              id: 'press',
              label: 'ATMOSPHERIC PRESSURE',
              value: Number(pressVal.toFixed(1)),
              unit: 'hPa',
              status: pressVal < 900 || pressVal > 1100 ? 'WARNING' : 'NORMAL',
              min: 800,
              max: 1200,
              nominalRange: '950.0 - 1050.0 hPa',
              source: data.source || 'esp32_sensor_01',
            },
            {
              id: 'mq4',
              label: 'MQ-4 (METHANE/CH4)',
              value: Number(mq4Val.toFixed(2)),
              unit: 'ratio',
              status: mq4Val >= 0.70 ? 'CRITICAL' : mq4Val >= 0.40 ? 'WARNING' : 'NORMAL',
              min: 0,
              max: 1.0,
              nominalRange: '< 0.40 ratio',
              source: data.source || 'esp32_sensor_01',
            },
            {
              id: 'mq135',
              label: 'MQ-135 (AIR QUALITY/CO)',
              value: Number(mq135Val.toFixed(2)),
              unit: 'ratio',
              status: mq135Val >= 0.70 ? 'CRITICAL' : mq135Val >= 0.40 ? 'WARNING' : 'NORMAL',
              min: 0,
              max: 1.0,
              nominalRange: '< 0.40 ratio',
              source: data.source || 'esp32_sensor_01',
            },
            {
              id: 'bat',
              label: 'BATTERY BUS',
              value: Number(batVal.toFixed(1)),
              unit: '%',
              status: batVal < 20 ? 'CRITICAL' : batVal < 35 ? 'WARNING' : 'NORMAL',
              min: 0,
              max: 100,
              nominalRange: '> 25%',
              source: 'power_bus_01',
            },
            {
              id: 'vib',
              label: 'SEISMIC / VIBRATION',
              value: Number(vibVal.toFixed(3)),
              unit: 'g',
              status: vibVal > 0.8 ? 'CRITICAL' : vibVal > 0.4 ? 'WARNING' : 'NORMAL',
              min: 0,
              max: 2.0,
              nominalRange: '< 0.30 g',
              source: 'chassis_imu_01',
            },
            {
              id: 'volt',
              label: 'MAIN BUS VOLTAGE',
              value: Number((11.4 + (batVal / 100) * 1.2).toFixed(2)),
              unit: 'V',
              status: batVal < 20 ? 'CRITICAL' : batVal < 35 ? 'WARNING' : 'NORMAL',
              min: 10.0,
              max: 13.0,
              nominalRange: '11.8 - 12.6 V',
              source: 'power_bus_01',
            },
          ];

          return items;
        }
      } catch {
        backendConnected = false;
      }
    }

    const data = mockScenariosData[currentScenario]?.sensors || mockSensors;
    return Promise.resolve([...data]);
  },

  /**
   * GET /api/vision/latest
   * Fetches latest YOLO inference detections with bounding boxes normalized to percentages.
   */
  async getLatestVision(): Promise<VisionDetection[]> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/vision/latest');
        if (res.ok) {
          backendConnected = true;
          const data = await res.json();
          const detections = Array.isArray(data.detections) ? data.detections : [];

          return detections.map((det: any, index: number) => {
            const rawBox = Array.isArray(det.bbox) ? det.bbox : [30, 30, 20, 20];
            let x = Number(rawBox[0]) || 0;
            let y = Number(rawBox[1]) || 0;
            let width = Number(rawBox[2]) || 20;
            let height = Number(rawBox[3]) || 20;

            if (x > 100 || y > 100 || width > 100 || height > 100) {
              x = (x / 640) * 100;
              y = (y / 480) * 100;
              width = (width / 640) * 100;
              height = (height / 480) * 100;
            } else if (x <= 1 && y <= 1 && width <= 1 && height <= 1) {
              x *= 100;
              y *= 100;
              width *= 100;
              height *= 100;
            }

            return {
              id: `det-${det.id || index + 1}`,
              label: (det.class_name || det.class || 'OBJECT').toUpperCase(),
              confidence: Number(det.confidence) || 0.85,
              bbox: {
                x: Math.max(0, Math.min(95, Math.round(x))),
                y: Math.max(0, Math.min(95, Math.round(y))),
                width: Math.max(5, Math.min(90, Math.round(width))),
                height: Math.max(5, Math.min(90, Math.round(height))),
              },
              image_path: det.image_path || null,
            };
          });
        }
      } catch {
        backendConnected = false;
      }
    }

    const data = mockScenariosData[currentScenario]?.vision || mockVisionDetections;
    return Promise.resolve([...data]);
  },

  /**
   * GET /api/decisions/latest
   * Fetches latest Decision Engine arbitration state.
   */
  async getLatestDecision(): Promise<DecisionData> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/decisions/latest');
        if (res.ok) {
          backendConnected = true;
          const data = await res.json();
          let sev: SeverityLevel = 'NORMAL';
          const upperSev = String(data.severity || '').toUpperCase();
          if (['NORMAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(upperSev)) {
            sev = upperSev as SeverityLevel;
          }

          let hazardName = String(data.hazard_type || data.hazard || 'NONE').toUpperCase();
          if (hazardName === 'NONE') {
            hazardName = 'NOMINAL / NO HAZARDS';
          }

          const reasonsList: string[] = Array.isArray(data.reasons) && data.reasons.length > 0
            ? data.reasons
            : (data.reason || data.message ? [data.reason || data.message] : ['Environmental telemetry nominal']);

          return {
            hazard: hazardName,
            hazard_type: data.hazard_type || data.hazard || 'none',
            severity: sev,
            confidence: Number(data.confidence) || 0.95,
            reason: reasonsList[0] || 'Sensor arbitration nominal',
            reasons: reasonsList,
            sensor_evidence: Array.isArray(data.sensor_evidence) ? data.sensor_evidence : [],
            vision_evidence: Array.isArray(data.vision_evidence) ? data.vision_evidence : [],
            all_hazards: Array.isArray(data.all_hazards) ? data.all_hazards : [],
            recommended_action: data.recommended_action || (sev in ['HIGH', 'CRITICAL'] ? 'STOP_AND_INSPECT' : 'PROCEED'),
          };
        }
      } catch {
        backendConnected = false;
      }
    }

    const data = mockScenariosData[currentScenario]?.decision || mockDecision;
    return Promise.resolve({ ...data });
  },

  /**
   * GET /api/mission/current
   * Fetches active mission from SQLite.
   */
  async getCurrentMission(): Promise<MissionInfo> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/mission/current');
        if (res.ok) {
          backendConnected = true;
          const data = await res.json();
          if (data && (data.mission || data.mission_code || data.id)) {
            const m = data.mission || data;
            const code = m.mission_code || m.id || 'EXP-2026-001';
            let durationMin = 1;
            if (m.started_at) {
              const startEpoch = new Date(m.started_at).getTime();
              if (!isNaN(startEpoch)) {
                durationMin = Math.max(1, Math.round((Date.now() - startEpoch) / 60000));
              }
            }

            return {
              id: code,
              title: m.title || `Mission ${code}`,
              status: (m.status || 'ACTIVE') as any,
              durationMinutes: durationMin,
              hazardsEncountered: m.hazardsEncountered ?? 0,
              startTime: m.started_at ? m.started_at.split('T')[1]?.slice(0, 8) || m.started_at : '10:00:00',
              sector: m.location?.label || m.sector || 'Sector 4B',
              description: m.notes || m.description || 'Active exploration survey corridor',
              location: m.location || null,
            };
          }
        }
      } catch {
        backendConnected = false;
      }
    }

    return Promise.resolve({ ...mockCurrentMission });
  },

  /**
   * GET /api/missions
   */
  async getMissionHistory(): Promise<MissionInfo[]> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/missions');
        if (res.ok) {
          backendConnected = true;
          const raw = await res.json();
          const missions = Array.isArray(raw) ? raw : (raw?.items || []);
          if (Array.isArray(missions) && missions.length > 0) {
            return missions.map((m: any) => ({
              id: m.mission_code || m.id || 'EXP-2026-001',
              title: m.title || `Mission ${m.mission_code || m.id}`,
              status: m.status || 'COMPLETED',
              durationMinutes: m.durationMinutes || 25,
              hazardsEncountered: m.hazardsEncountered || 0,
              startTime: m.started_at || '10:00:00',
              endTime: m.ended_at,
              sector: m.sector || (m.location?.label) || 'Sector 4B',
              description: m.notes || m.description || '',
            }));
          }
        }
      } catch {
        backendConnected = false;
      }
    }

    return Promise.resolve([...mockMissionsList]);
  },

  /**
   * GET /api/missions/{id}
   */
  async getMissionDetails(id: string): Promise<MissionInfo | null> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout(`/api/missions/${encodeURIComponent(id)}`);
        if (res.ok) {
          const m = await res.json();
          return {
            id: m.mission_code || m.id,
            title: m.title || `Mission ${m.mission_code || m.id}`,
            status: m.status || 'COMPLETED',
            durationMinutes: m.durationMinutes || 20,
            hazardsEncountered: m.hazardsEncountered || 0,
            startTime: m.started_at || '10:00:00',
            endTime: m.ended_at,
            sector: m.location?.label || m.sector || 'General Mine Area',
            description: m.notes || m.description || '',
          };
        }
      } catch {
        // Fall back to local search
      }
    }

    const found = mockMissionsList.find((m) => m.id === id);
    return Promise.resolve(found ? { ...found } : null);
  },

  /**
   * GET /api/logs
   * Real mission activity log stream
   */
  async getMissionLogs(typeFilter: EventType = 'All'): Promise<MissionEvent[]> {
    if (!forceSimulationMode) {
      try {
        const url = typeFilter === 'All' ? '/api/logs' : `/api/logs?type_filter=${encodeURIComponent(typeFilter)}`;
        const res = await fetchWithTimeout(url);
        if (res.ok) {
          backendConnected = true;
          const raw = await res.json();
          const items = Array.isArray(raw) ? raw : (raw?.items || []);
          if (Array.isArray(items) && items.length > 0) {
            return items.map((l: any, idx: number) => {
              let t = '12:00:00';
              if (l.timestamp) {
                t = l.timestamp.includes('T') ? l.timestamp.split('T')[1].slice(0, 8) : l.timestamp.slice(0, 8);
              } else if (l.time) {
                t = l.time;
              }

              let sev: SeverityLevel = 'NORMAL';
              const upperLvl = String(l.level || l.severity || '').toUpperCase();
              if (upperLvl in ['CRITICAL', 'ERROR']) sev = 'HIGH';
              else if (upperLvl === 'WARN' || upperLvl === 'WARNING') sev = 'MEDIUM';
              else if (upperLvl === 'LOW') sev = 'LOW';

              let eventType: any = l.event_type || l.type || 'System';
              if (eventType.includes('MISSION')) eventType = 'Mission';
              else if (eventType.includes('SENSOR') || eventType.includes('GAS')) eventType = 'Sensor';
              else if (eventType.includes('VISION') || eventType.includes('IMAGE')) eventType = 'Vision';
              else if (eventType.includes('DECISION') || eventType.includes('HAZARD')) eventType = 'Decision';
              else eventType = 'System';

              return {
                id: `log-${l.id || idx + 1}`,
                time: t,
                type: eventType,
                event: l.message || l.event || 'System notification',
                severity: sev,
                metadata: l.metadata || {},
              };
            });
          }
        }
      } catch {
        backendConnected = false;
      }
    }

    let logs = [...mockTimelineEvents];
    if (typeFilter !== 'All') {
      logs = logs.filter((l) => l.type === typeFilter);
    }
    return Promise.resolve(logs);
  },

  /**
   * GET /api/system/status
   */
  async getSystemStatus(): Promise<RoverSystemInfo> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/system/status');
        if (res.ok) {
          backendConnected = true;
          const data = await res.json();
          return {
            rover: (data.rover_status === 'RUNNING' ? 'Running' : data.rover || 'Running') as any,
            backend: 'Connected',
            database: (data.database_status === 'OK' || data.database === 'connected') ? 'Connected' : 'Disconnected',
            network: data.network === 'online' ? 'Online' : 'Offline',
            batteryPct: data.battery_pct ?? 86,
            internalTempC: data.cpu_temperature_c ?? data.internal_temp_c ?? 38.2,
            firmwareVersion: data.firmware_version ?? 'v2.4.1',
            activeSector: data.active_sector ?? 'Sector 4B',
            ipAddress: data.ip_address ?? '127.0.0.1:8000',
            uptimeSeconds: data.uptime_seconds ?? 0,
            storageAvailableMb: data.storage_available_mb ?? 2048,
            cpuTemperatureC: data.cpu_temperature_c ?? 48.5,
            cameraStatus: data.camera_status ?? 'OK',
            sensorStatus: data.sensor_status ?? 'OK',
            databaseStatus: data.database_status ?? 'OK',
          };
        }
      } catch {
        backendConnected = false;
      }
    }

    return Promise.resolve({
      ...mockSystemStatus,
      backend: backendConnected ? 'Connected' : 'Disconnected',
    });
  },

  /**
   * GET /api/sensors/history (or /api/telemetry/history)
   */
  async getTelemetryHistory(): Promise<TelemetryPoint[]> {
    if (!forceSimulationMode) {
      try {
        const res = await fetchWithTimeout('/api/sensors/history?limit=30');
        if (res.ok) {
          backendConnected = true;
          const raw = await res.json();
          const rows = Array.isArray(raw) ? raw : (raw?.items || []);
          if (Array.isArray(rows) && rows.length > 0) {
            const timeMap: Map<string, { temp?: number; hum?: number; gas?: number; press?: number }> = new Map();
            const sortedRows = [...rows].reverse();
            for (const r of sortedRows) {
              let t = '12:00:00';
              if (r.timestamp) {
                t = r.timestamp.includes('T') ? r.timestamp.split('T')[1].slice(0, 8) : r.timestamp.slice(0, 8);
              }
              const entry = timeMap.get(t) || {};
              if (r.temperature_c !== undefined) entry.temp = Number(r.temperature_c);
              else if (r.sensor_type === 'temperature') entry.temp = Number(r.value);

              if (r.humidity_percent !== undefined) entry.hum = Number(r.humidity_percent);
              else if (r.sensor_type === 'humidity') entry.hum = Number(r.value);

              if (r.mq4 !== undefined) entry.gas = Number(r.mq4);
              else if (r.sensor_type === 'gas' || r.sensor_type === 'mq4') entry.gas = Number(r.value);

              if (r.pressure_hpa !== undefined) entry.press = Number(r.pressure_hpa);
              else if (r.sensor_type === 'pressure') entry.press = Number(r.value);

              timeMap.set(t, entry);
            }

            const points: TelemetryPoint[] = [];
            timeMap.forEach((val, timeKey) => {
              points.push({
                time: timeKey,
                temperature: Number((val.temp ?? 25.0).toFixed(1)),
                humidity: Number((val.hum ?? 50.0).toFixed(1)),
                gasLevel: Number((val.gas ?? 0.12).toFixed(2)),
                pressure: val.press ? Number(val.press.toFixed(1)) : 1013.2,
              });
            });
            return points.slice(-15);
          }
        }
      } catch {
        backendConnected = false;
      }
    }

    return Promise.resolve([...mockTelemetryHistory]);
  },

  /**
   * GET /api/observations/latest
   */
  async getLatestObservation(): Promise<ObservationData | null> {
    try {
      const res = await fetchWithTimeout('/api/observations/latest');
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Offline fallback
    }
    return null;
  },

  /**
   * POST test scenario telemetry into the live FastAPI backend database
   */
  async injectScenarioToBackend(sc: MockScenario): Promise<boolean> {
    const scData = mockScenariosData[sc];
    if (!scData) return false;

    try {
      const tempSensor = scData.sensors.find((s) => s.id === 'temp')?.value;
      const humSensor = scData.sensors.find((s) => s.id === 'hum')?.value;
      const gasSensor = scData.sensors.find((s) => s.id === 'gas')?.value;

      await fetchWithTimeout('/api/sensors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          temperature: typeof tempSensor === 'number' ? tempSensor : 25.0,
          humidity: typeof humSensor === 'number' ? humSensor : 50.0,
          gas: typeof gasSensor === 'number' ? gasSensor : 0.1,
          smoke: sc === 'fire' ? 0.75 : 0.05,
          temperature_c: typeof tempSensor === 'number' ? tempSensor : 25.0,
          humidity_percent: typeof humSensor === 'number' ? humSensor : 50.0,
          pressure_hpa: 1012.4,
          mq4: typeof gasSensor === 'number' ? gasSensor : 0.1,
          mq135: sc === 'fire' ? 0.75 : 0.05,
          timestamp: new Date().toISOString(),
          source: 'simulator',
          device_id: 'mining_rover_01',
        }),
      });

      if (scData.vision.length > 0) {
        await fetchWithTimeout('/api/vision', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timestamp: new Date().toISOString(),
            detections: scData.vision.map((v) => ({
              class_name: v.label.toLowerCase(),
              confidence: v.confidence,
              bbox: [v.bbox.x, v.bbox.y, v.bbox.width, v.bbox.height],
              source: 'yolo',
              device_id: 'mining_rover_01',
            })),
          }),
        });
      }

      await fetchWithTimeout('/api/decisions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hazard_type: scData.decision.hazard,
          severity: scData.decision.severity,
          confidence: scData.decision.confidence,
          message: scData.decision.reason,
          reasons: [scData.decision.reason],
          recommended_action: sc === 'fire' ? 'EVACUATE' : sc === 'gas' ? 'VENTILATE' : 'MONITOR',
          sources: ['sensor', 'vision'],
          timestamp: new Date().toISOString(),
          device_id: 'mining_rover_01',
        }),
      });

      backendConnected = true;
      return true;
    } catch {
      return false;
    }
  },

  /**
   * GET /api/sync/status
   */
  async getSyncStatus(): Promise<SyncStatusInfo> {
    try {
      const res = await fetchWithTimeout('/api/sync/status');
      if (res.ok) {
        const data = await res.json();
        return {
          network: data.network || (data.network_available ? 'online' : 'offline'),
          network_available: Boolean(data.network_available ?? (data.network === 'online')),
          sync_enabled: Boolean(data.sync_enabled ?? true),
          sync_status: (data.sync_status || 'PAUSED') as any,
          local_database: data.local_database || 'healthy',
          pending_count: data.pending_records ?? data.pending_count ?? 0,
          pending_records: data.pending_records ?? data.pending_count ?? 0,
          synced_count: data.synced_count ?? 0,
          in_flight_count: data.in_flight_count ?? 0,
          total_records: data.total_records ?? 0,
          session_synced: data.session_synced ?? 0,
          last_sync_time: data.last_successful_sync || data.last_sync_time || null,
          last_successful_sync: data.last_successful_sync || data.last_sync_time || null,
          last_error: data.last_sync_error || data.last_error || null,
          last_sync_error: data.last_sync_error || data.last_error || null,
        };
      }
    } catch {
      // Offline-safe fallback
    }

    return {
      network: 'offline',
      network_available: false,
      sync_enabled: true,
      sync_status: 'PAUSED',
      local_database: 'healthy',
      pending_count: 0,
      pending_records: 0,
      synced_count: 0,
      in_flight_count: 0,
      total_records: 0,
      session_synced: 0,
      last_sync_time: null,
      last_successful_sync: null,
      last_error: null,
      last_sync_error: null,
    };
  },

  /**
   * POST /api/sync/trigger
   */
  async triggerSync(): Promise<any> {
    try {
      const res = await fetchWithTimeout('/api/sync/trigger', { method: 'POST' });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Error
    }
    return { status: 'failed', reason: 'network_or_backend_unreachable' };
  },
};

export default roverApi;
