import {
  SensorItem,
  VisionDetection,
  DecisionData,
  MissionInfo,
  MissionEvent,
  RoverSystemInfo,
  TelemetryPoint,
} from '../types/rover';

export type MockScenario = 'fire' | 'gas' | 'rockfall' | 'nominal';

export interface ScenarioDefinition {
  name: string;
  description: string;
  sensors: SensorItem[];
  decision: DecisionData;
  vision: VisionDetection[];
}

export const mockScenariosData: Record<MockScenario, ScenarioDefinition> = {
  fire: {
    name: 'Fire & Thermal Anomaly',
    description: 'High thermal signature detected with optical flame and smoke signatures in shaft 4B.',
    sensors: [
      { id: 'temp', label: 'TEMPERATURE', value: 34.5, unit: '°C', status: 'WARNING', min: 10, max: 50, nominalRange: '18 - 26 °C' },
      { id: 'hum', label: 'HUMIDITY', value: 61, unit: '%', status: 'NORMAL', min: 20, max: 95, nominalRange: '45 - 75 %' },
      { id: 'gas', label: 'GAS LEVEL', value: 0.72, unit: '', status: 'WARNING', min: 0, max: 1.0, nominalRange: '< 0.30' },
      { id: 'air', label: 'AIR QUALITY', value: 'GOOD', unit: '', status: 'GOOD', nominalRange: 'GOOD / MODERATE' },
      { id: 'pres', label: 'PRESSURE', value: 1013.2, unit: 'hPa', status: 'NORMAL', min: 950, max: 1050, nominalRange: '1005 - 1025 hPa' },
      { id: 'bat', label: 'BATTERY', value: 86, unit: '%', status: 'NORMAL', min: 0, max: 100, nominalRange: '> 20%' },
    ],
    decision: {
      hazard: 'FIRE DETECTED',
      severity: 'HIGH',
      confidence: 0.91,
      reason: 'Fire + elevated temperature in transport tunnel section',
    },
    vision: [
      {
        id: 'det-1',
        label: 'FIRE',
        confidence: 0.91,
        bbox: { x: 38, y: 32, width: 22, height: 26 },
      },
      {
        id: 'det-2',
        label: 'SMOKE',
        confidence: 0.84,
        bbox: { x: 32, y: 16, width: 34, height: 24 },
      },
    ],
  },
  gas: {
    name: 'Toxic / Flammable Gas Surge',
    description: 'Electrochemical and NDIR sensors indicate rapid increase in combustible hydrocarbons.',
    sensors: [
      { id: 'temp', label: 'TEMPERATURE', value: 24.2, unit: '°C', status: 'NORMAL', min: 10, max: 50, nominalRange: '18 - 26 °C' },
      { id: 'hum', label: 'HUMIDITY', value: 58, unit: '%', status: 'NORMAL', min: 20, max: 95, nominalRange: '45 - 75 %' },
      { id: 'gas', label: 'GAS LEVEL', value: 0.88, unit: '', status: 'CRITICAL', min: 0, max: 1.0, nominalRange: '< 0.30' },
      { id: 'air', label: 'AIR QUALITY', value: 'HAZARDOUS', unit: '', status: 'CRITICAL', nominalRange: 'GOOD / MODERATE' },
      { id: 'pres', label: 'PRESSURE', value: 1011.0, unit: 'hPa', status: 'NORMAL', min: 950, max: 1050, nominalRange: '1005 - 1025 hPa' },
      { id: 'bat', label: 'BATTERY', value: 82, unit: '%', status: 'NORMAL', min: 0, max: 100, nominalRange: '> 20%' },
    ],
    decision: {
      hazard: 'TOXIC GAS LEAK',
      severity: 'HIGH',
      confidence: 0.95,
      reason: 'Combustible gas threshold exceeded (0.88 index vs 0.30 safe limit)',
    },
    vision: [],
  },
  rockfall: {
    name: 'Physical Obstruction / Rockfall',
    description: 'Obstacle detected blocking active track corridor ahead of the front chassis.',
    sensors: [
      { id: 'temp', label: 'TEMPERATURE', value: 22.1, unit: '°C', status: 'NORMAL', min: 10, max: 50, nominalRange: '18 - 26 °C' },
      { id: 'hum', label: 'HUMIDITY', value: 65, unit: '%', status: 'NORMAL', min: 20, max: 95, nominalRange: '45 - 75 %' },
      { id: 'gas', label: 'GAS LEVEL', value: 0.14, unit: '', status: 'NORMAL', min: 0, max: 1.0, nominalRange: '< 0.30' },
      { id: 'air', label: 'AIR QUALITY', value: 'GOOD', unit: '', status: 'GOOD', nominalRange: 'GOOD / MODERATE' },
      { id: 'pres', label: 'PRESSURE', value: 1014.5, unit: 'hPa', status: 'NORMAL', min: 950, max: 1050, nominalRange: '1005 - 1025 hPa' },
      { id: 'bat', label: 'BATTERY', value: 79, unit: '%', status: 'NORMAL', min: 0, max: 100, nominalRange: '> 20%' },
    ],
    decision: {
      hazard: 'ROCKFALL OBSTACLE',
      severity: 'MEDIUM',
      confidence: 0.89,
      reason: 'Physical rock obstruction identified in primary heading line',
    },
    vision: [
      {
        id: 'det-rock-1',
        label: 'ROCK',
        confidence: 0.89,
        bbox: { x: 36, y: 44, width: 28, height: 25 },
      },
    ],
  },
  nominal: {
    name: 'All Systems Nominal',
    description: 'Environmental parameters within baseline safety limits. Zero hazards detected.',
    sensors: [
      { id: 'temp', label: 'TEMPERATURE', value: 21.8, unit: '°C', status: 'NORMAL', min: 10, max: 50, nominalRange: '18 - 26 °C' },
      { id: 'hum', label: 'HUMIDITY', value: 55, unit: '%', status: 'NORMAL', min: 20, max: 95, nominalRange: '45 - 75 %' },
      { id: 'gas', label: 'GAS LEVEL', value: 0.08, unit: '', status: 'NORMAL', min: 0, max: 1.0, nominalRange: '< 0.30' },
      { id: 'air', label: 'AIR QUALITY', value: 'GOOD', unit: '', status: 'GOOD', nominalRange: 'GOOD / MODERATE' },
      { id: 'pres', label: 'PRESSURE', value: 1013.2, unit: 'hPa', status: 'NORMAL', min: 950, max: 1050, nominalRange: '1005 - 1025 hPa' },
      { id: 'bat', label: 'BATTERY', value: 92, unit: '%', status: 'NORMAL', min: 0, max: 100, nominalRange: '> 20%' },
    ],
    decision: {
      hazard: 'NO HAZARDS DETECTED',
      severity: 'NORMAL',
      confidence: 0.98,
      reason: 'All sensor metrics and vision FOV within standard mine baseline',
    },
    vision: [],
  },
};

export const mockSensors = mockScenariosData.fire.sensors;
export const mockDecision = mockScenariosData.fire.decision;
export const mockVisionDetections = mockScenariosData.fire.vision;

export const mockCurrentMission: MissionInfo = {
  id: 'Mission #001',
  title: 'Shaft 4B Thermal & Gas Inspection',
  status: 'ACTIVE',
  durationMinutes: 22,
  hazardsEncountered: 3,
  startTime: '14:10:00',
  sector: 'Sector 4B — Sub-Level 2',
  description: 'Autonomous exploration route verifying ventilation dampers and detecting thermal anomalies along transport rail lines.',
};

export const mockTimelineEvents: MissionEvent[] = [
  { id: 'ev-1', time: '14:10:32', type: 'Mission', event: 'Mission started', severity: 'NORMAL' },
  { id: 'ev-2', time: '14:12:18', type: 'Vision', event: 'Rock detected', severity: 'LOW' },
  { id: 'ev-3', time: '14:12:21', type: 'Decision', event: 'Hazard level → LOW', severity: 'LOW' },
  { id: 'ev-4', time: '14:15:32', type: 'Vision', event: 'Smoke detected', severity: 'MEDIUM' },
  { id: 'ev-5', time: '14:15:34', type: 'Decision', event: 'Hazard level → MEDIUM', severity: 'MEDIUM' },
  { id: 'ev-6', time: '14:20:05', type: 'Vision', event: 'Fire detected (Confidence 91%)', severity: 'HIGH' },
  { id: 'ev-7', time: '14:20:12', type: 'Decision', event: 'Hazard level → HIGH', severity: 'HIGH' },
  { id: 'ev-8', time: '14:21:00', type: 'Sensor', event: 'Gas level elevated to 0.72', severity: 'MEDIUM' },
];

export const mockMissionsList: MissionInfo[] = [
  {
    id: 'Mission #001',
    title: 'Sub-Level 2 Thermal Patrol',
    status: 'ACTIVE',
    durationMinutes: 22,
    hazardsEncountered: 3,
    startTime: '14:10:00',
    sector: 'Sector 4B',
    description: 'Active survey along conveyor heading 12. Monitoring thermal signatures.',
  },
  {
    id: 'Mission #002',
    title: 'Eastern Drift Methane Sweep',
    status: 'COMPLETED',
    durationMinutes: 47,
    hazardsEncountered: 4,
    startTime: '12:30:00',
    endTime: '13:17:00',
    sector: 'East Gallery 1',
    description: 'Ventilation shaft verification. Detected 4 minor gas pocket spikes, all cleared.',
  },
  {
    id: 'Mission #003',
    title: 'Haulage Tunnel Rock Stability Check',
    status: 'COMPLETED',
    durationMinutes: 31,
    hazardsEncountered: 2,
    startTime: '10:15:00',
    endTime: '10:46:00',
    sector: 'Haulage Route A',
    description: 'Stereo camera and range scanner check of roof bolt stabilization plates.',
  },
  {
    id: 'Mission #004',
    title: 'Drainage Sump Water Depth Survey',
    status: 'ABORTED',
    durationMinutes: 14,
    hazardsEncountered: 1,
    startTime: '08:45:00',
    endTime: '08:59:00',
    sector: 'Sump Station 3',
    description: 'Mission aborted early due to standing water level exceeding 200mm safety clearance.',
  },
];

export const mockSystemStatus: RoverSystemInfo = {
  rover: 'Running',
  backend: 'Connected',
  database: 'Connected',
  network: 'Online',
  batteryPct: 86,
  internalTempC: 38.2,
  firmwareVersion: 'v2.4.1',
  activeSector: 'Sector 4B',
  ipAddress: '192.168.10.42',
  uptimeSeconds: 7920,
};

export const mockTelemetryHistory: TelemetryPoint[] = [
  { time: '14:10', temperature: 24.1, humidity: 55, gasLevel: 0.12 },
  { time: '14:12', temperature: 24.5, humidity: 56, gasLevel: 0.14 },
  { time: '14:14', temperature: 25.2, humidity: 57, gasLevel: 0.15 },
  { time: '14:16', temperature: 27.8, humidity: 59, gasLevel: 0.35 },
  { time: '14:18', temperature: 31.4, humidity: 60, gasLevel: 0.58 },
  { time: '14:20', temperature: 34.5, humidity: 61, gasLevel: 0.72 },
  { time: '14:22', temperature: 34.8, humidity: 62, gasLevel: 0.74 },
];
