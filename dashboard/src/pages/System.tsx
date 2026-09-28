import React from 'react';
import { RoverSystemInfo, ConnectionStatus, SyncStatusInfo } from '../types/rover';
import { SystemStatus } from '../components/SystemStatus';
import { Terminal } from 'lucide-react';

interface SystemPageProps {
  system: RoverSystemInfo;
  connectionStatus: ConnectionStatus;
  syncStatus?: SyncStatusInfo | null;
  onTriggerSync?: () => void;
}

export const SystemPage: React.FC<SystemPageProps> = ({
  system,
  connectionStatus,
  syncStatus = null,
  onTriggerSync,
}) => {
  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-white/[0.07]">
        <span className="text-[11px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
          HARDWARE & DAEMON ARCHITECTURE
        </span>
        <h2 className="text-xl sm:text-2xl font-bold text-[#F5F7FA] tracking-tight">
          Rover Core Nodes & Backend Gateway Blueprint
        </h2>
      </div>

      {/* Main Status Cards */}
      <SystemStatus
        system={system}
        connectionStatus={connectionStatus}
        syncStatus={syncStatus}
        onTriggerSync={onTriggerSync}
      />

      {/* Integration Architectural Blueprint (FastAPI Ready) */}
      <div className="nv-card p-6 rounded-xl border border-white/[0.07] bg-[#111317]">
        <div className="flex items-center gap-3 pb-4 border-b border-white/[0.07] mb-5">
          <div className="w-8 h-8 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#27C7D9]">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
              FASTAPI SPECIFICATION
            </span>
            <h3 className="font-semibold text-sm text-[#F5F7FA] uppercase tracking-tight">
              Backend REST & Telemetry Architecture
            </h3>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs font-mono">
          <div className="bg-[#181B20] p-4.5 rounded-lg border border-white/[0.06]">
            <h4 className="text-sm font-semibold text-[#F5F7FA] mb-3 flex items-center gap-2 font-sans">
              <span className="w-2 h-2 rounded-full bg-[#27C7D9]" />
              REST API Routes Contract
            </h4>
            <div className="space-y-2.5 text-[#A7ADB7]">
              <div className="flex justify-between py-1 border-b border-white/[0.04]">
                <span className="text-[#27C7D9] font-semibold">GET /api/sensors/latest</span>
                <span className="text-[#69717D]">CAN Bus FIFO Stream</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/[0.04]">
                <span className="text-[#27C7D9] font-semibold">GET /api/vision/latest</span>
                <span className="text-[#69717D]">YOLO Bounding Coordinates</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/[0.04]">
                <span className="text-[#27C7D9] font-semibold">GET /api/decisions/latest</span>
                <span className="text-[#69717D]">Sensor Fusion Arbitration</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/[0.04]">
                <span className="text-[#27C7D9] font-semibold">GET /api/mission/current</span>
                <span className="text-[#69717D]">Active Sector Parameters</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/[0.04]">
                <span className="text-[#27C7D9] font-semibold">GET /api/missions</span>
                <span className="text-[#69717D]">Historical Patrol Records</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#27C7D9] font-semibold">GET /api/logs</span>
                <span className="text-[#69717D]">Chronological Telemetry Feed</span>
              </div>
            </div>
          </div>

          <div className="bg-[#181B20] p-4.5 rounded-lg border border-white/[0.06]">
            <h4 className="text-sm font-semibold text-[#F5F7FA] mb-3 flex items-center gap-2 font-sans">
              <span className="w-2 h-2 rounded-full bg-[#27C7D9]" />
              Separation of Concerns Checklist
            </h4>
            <ul className="space-y-2.5 text-[#A7ADB7]">
              <li className="flex items-start gap-2.5">
                <span className="text-[#35C98A] font-bold mt-0.5">✓</span>
                <span><strong>Pure Display Surface:</strong> Frontend isolates all rendering. Zero database queries or local model inferences run in browser.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-[#35C98A] font-bold mt-0.5">✓</span>
                <span><strong>Offline-First Pipeline:</strong> Local SQLite telemetry store ensures full display capability without cloud connectivity.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <span className="text-[#35C98A] font-bold mt-0.5">✓</span>
                <span><strong>Advisory Safety Engine:</strong> Decision engine evaluates hazards without direct actuator or motor coupling.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemPage;
