export type ConnectionStatus = 'ONLINE' | 'OFFLINE' | 'DISCONNECTED';

export type MissionState = 'IDLE' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ABORTED';

export type SeverityLevel = 'NORMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type EventType = 'All' | 'Vision' | 'Sensor' | 'Decision' | 'Mission' | 'System';

export interface SensorItem {
  id: string;
  label: string;
  value: number | string;
  unit: string;
  status?: 'GOOD' | 'WARNING' | 'CRITICAL' | 'NORMAL';
  min?: number;
  max?: number;
  nominalRange?: string;
  source?: string;
}

export interface BoundingBox {
  x: number; // percentage 0-100
  y: number; // percentage 0-100
  width: number; // percentage
  height: number; // percentage
}

export interface VisionDetection {
  id: string;
  label: string;
  confidence: number; // 0.0 - 1.0 or percentage
  bbox: BoundingBox;
  image_path?: string | null;
}

export interface DecisionData {
  hazard: string;
  hazard_type?: string;
  severity: SeverityLevel;
  confidence: number;
  reason: string;
  reasons?: string[];
  sensor_evidence?: Array<{ sensor?: string; value?: number; [key: string]: any }>;
  vision_evidence?: Array<{ class_name?: string; confidence?: number; [key: string]: any }>;
  all_hazards?: Array<{ hazard_type: string; severity: string }>;
  recommended_action?: string;
}

export interface MissionInfo {
  id: string;
  title: string;
  status: MissionState;
  durationMinutes: number;
  hazardsEncountered: number;
  startTime: string;
  endTime?: string;
  sector: string;
  description: string;
  location?: { label?: string; x?: number; y?: number; z?: number } | null;
}

export interface MissionEvent {
  id: string;
  time: string;
  type: 'Vision' | 'Sensor' | 'Decision' | 'Mission' | 'System';
  event: string;
  severity: SeverityLevel;
  metadata?: Record<string, any>;
}

export interface RoverSystemInfo {
  rover: 'Running' | 'Idle' | 'Maintenance' | 'Error';
  backend: 'Connected' | 'Disconnected';
  database: 'Connected' | 'Disconnected';
  network: 'Online' | 'Offline';
  batteryPct: number;
  internalTempC: number;
  firmwareVersion: string;
  activeSector: string;
  ipAddress?: string;
  uptimeSeconds?: number;
  storageAvailableMb?: number;
  cpuTemperatureC?: number;
  cameraStatus?: string;
  sensorStatus?: string;
  databaseStatus?: string;
}

export interface TelemetryPoint {
  time: string;
  temperature: number;
  humidity: number;
  gasLevel: number;
  pressure?: number;
}

export interface SyncStatusInfo {
  network: 'online' | 'offline';
  network_available?: boolean;
  sync_enabled: boolean;
  sync_status: 'IDLE' | 'SYNCING' | 'PAUSED' | 'ERROR' | 'UNAVAILABLE';
  local_database: string;
  pending_count: number;
  pending_records?: number;
  synced_count: number;
  in_flight_count: number;
  total_records: number;
  session_synced: number;
  last_sync_time?: string | null;
  last_successful_sync?: string | null;
  last_error?: string | null;
  last_sync_error?: string | null;
}

export interface ObservationData {
  timestamp: string | null;
  mission?: { mission_code?: string } | null;
  location?: { label?: string; location_type?: string } | null;
  sensors?: {
    temperature_c?: number;
    humidity_percent?: number;
    pressure_hpa?: number;
    mq4?: number;
    mq135?: number;
  } | null;
  vision?: Array<{ class_name?: string; confidence?: number; bbox?: number[] }>;
  decision?: {
    hazard_type?: string;
    severity?: string;
    confidence?: number;
  } | null;
  image_path?: string | null;
  logs?: any[];
}
