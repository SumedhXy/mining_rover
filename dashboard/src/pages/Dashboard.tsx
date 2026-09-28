import React from 'react';
import {
  SensorItem,
  VisionDetection,
  DecisionData,
  MissionInfo,
  MissionEvent,
  TelemetryPoint,
  ConnectionStatus,
  RoverSystemInfo,
  SyncStatusInfo,
} from '../types/rover';
import { LiveCamera } from '../components/LiveCamera';
import { HazardCard } from '../components/HazardCard';
import { SensorGrid } from '../components/SensorGrid';
import { LiveTelemetryChart } from '../components/LiveTelemetryChart';
import { MissionStatus } from '../components/MissionStatus';
import { MissionTimeline } from '../components/MissionTimeline';
import { SystemWidget } from '../components/SystemWidget';

interface DashboardPageProps {
  sensors: SensorItem[];
  detections: VisionDetection[];
  decision: DecisionData;
  currentMission: MissionInfo;
  events: MissionEvent[];
  telemetryHistory: TelemetryPoint[];
  connectionStatus: ConnectionStatus;
  system: RoverSystemInfo;
  syncStatus?: SyncStatusInfo | null;
  onReconnect?: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  sensors,
  detections,
  decision,
  currentMission,
  events,
  telemetryHistory,
  connectionStatus,
  system,
  syncStatus,
  onReconnect,
}) => {
  return (
    <div className="space-y-6 w-full min-w-0 box-border">
      {/* Live Operations Deck: Optical Stream (Left) & Safety Decision Assessment (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start w-full min-w-0">
        {/* Left: Optical Camera Viewport */}
        <div className="lg:col-span-7 flex flex-col w-full min-w-0">
          <LiveCamera
            detections={detections}
            connectionStatus={connectionStatus}
            streamUrl="/api/vision/camera/stream"
            onReconnect={onReconnect}
          />
        </div>

        {/* Right: Decision Engine Assessment & Active Mission Status */}
        <div className="lg:col-span-5 flex flex-col space-y-5 w-full min-w-0">
          <HazardCard
            decision={decision}
            connectionStatus={connectionStatus}
          />

          <MissionStatus mission={currentMission} />
        </div>
      </div>

      {/* Environmental & Powertrain Sensor Grid */}
      <div className="border-t border-white/[0.06] pt-6 w-full min-w-0">
        <SensorGrid
          sensors={sensors}
          connectionStatus={connectionStatus}
        />
      </div>

      {/* Real-time Oscilloscope Telemetry Trend */}
      <div className="border-t border-white/[0.06] pt-6 w-full min-w-0">
        <LiveTelemetryChart data={telemetryHistory} />
      </div>

      {/* Lower Deck: Mission Timeline & Platform Diagnostics */}
      <div className="border-t border-white/[0.06] pt-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start w-full min-w-0">
        {/* Left: Mission Event Stream (FIFO) */}
        <div className="lg:col-span-7 w-full min-w-0">
          <MissionTimeline events={events} maxEvents={12} />
        </div>

        {/* Right: Platform Hardware & Diagnostics */}
        <div className="lg:col-span-5 w-full min-w-0">
          <SystemWidget
            system={system}
            connectionStatus={connectionStatus}
            syncStatus={syncStatus}
          />
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
