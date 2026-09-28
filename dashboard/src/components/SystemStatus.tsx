import React from 'react';
import { RoverSystemInfo, ConnectionStatus, SyncStatusInfo } from '../types/rover';
import { Cpu, HardDrive, Wifi, Server, ShieldCheck } from 'lucide-react';

interface SystemStatusProps {
  system: RoverSystemInfo;
  connectionStatus?: ConnectionStatus;
  syncStatus?: SyncStatusInfo | null;
  onTriggerSync?: () => void;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({
  system,
  connectionStatus = 'ONLINE',
}) => {
  const isDisconnected = connectionStatus === 'DISCONNECTED';
  const effectiveBackend = isDisconnected ? 'Disconnected' : system.backend;
  const effectiveNetwork = isDisconnected ? 'Offline' : system.network;

  const getStatusIndicator = (statusText: string, isOk: boolean) => (
    <div className="flex items-center gap-2">
      <span
        className={`w-2 h-2 rounded-full ${
          isOk ? 'bg-[#35C98A]' : 'bg-[#EF5B5B]'
        }`}
      />
      <span
        className={`font-mono text-xs font-semibold ${
          isOk ? 'text-[#35C98A]' : 'text-[#EF5B5B]'
        }`}
      >
        {statusText}
      </span>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Primary Nodes Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Rover Process Node */}
        <div className="nv-card p-4 rounded-xl border border-white/[0.07] bg-[#111317]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#27C7D9]">
                <Cpu className="w-3.5 h-3.5" />
              </div>
              <span className="text-[11px] font-semibold text-[#A7ADB7] uppercase tracking-wider">ROVER CORE</span>
            </div>
            {getStatusIndicator(system.rover, system.rover === 'Running')}
          </div>
          <p className="text-xs text-[#69717D] font-mono">
            Navigation daemon & CAN bus reader
          </p>
        </div>

        {/* FastAPI Backend */}
        <div className="nv-card p-4 rounded-xl border border-white/[0.07] bg-[#111317]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#27C7D9]">
                <Server className="w-3.5 h-3.5" />
              </div>
              <span className="text-[11px] font-semibold text-[#A7ADB7] uppercase tracking-wider">BACKEND API</span>
            </div>
            {getStatusIndicator(effectiveBackend, effectiveBackend === 'Connected')}
          </div>
          <p className="text-xs text-[#69717D] font-mono">
            FastAPI REST & WebSocket gateway
          </p>
        </div>

        {/* Database */}
        <div className="nv-card p-4 rounded-xl border border-white/[0.07] bg-[#111317]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#27C7D9]">
                <HardDrive className="w-3.5 h-3.5" />
              </div>
              <span className="text-[11px] font-semibold text-[#A7ADB7] uppercase tracking-wider">DATABASE</span>
            </div>
            {getStatusIndicator(system.database, system.database === 'Connected')}
          </div>
          <p className="text-xs text-[#69717D] font-mono">
            Local SQLite telemetry store
          </p>
        </div>

        {/* Network */}
        <div className="nv-card p-4 rounded-xl border border-white/[0.07] bg-[#111317]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#27C7D9]">
                <Wifi className="w-3.5 h-3.5" />
              </div>
              <span className="text-[11px] font-semibold text-[#A7ADB7] uppercase tracking-wider">NETWORK</span>
            </div>
            {getStatusIndicator(effectiveNetwork, effectiveNetwork === 'Online')}
          </div>
          <p className="text-xs text-[#69717D] font-mono">
            Subterranean 802.11s Ad-Hoc Mesh
          </p>
        </div>
      </div>

      {/* Hardware Health & Firmware Specs */}
      <div className="nv-card p-5 rounded-xl border border-white/[0.07] bg-[#111317]">
        <div className="flex items-center gap-3 pb-3.5 border-b border-white/[0.07] mb-4">
          <div className="w-8 h-8 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#27C7D9]">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
              PLATFORM STATUS
            </span>
            <h3 className="text-sm font-semibold text-[#F5F7FA]">
              Hardware & Subsystem Health Telemetry
            </h3>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="bg-[#181B20] p-3 rounded-lg border border-white/[0.06]">
            <span className="text-[#69717D] block mb-1">BATTERY SOC</span>
            <span className="text-base font-bold text-[#F5F7FA] tnum">{system.batteryPct}%</span>
          </div>

          <div className="bg-[#181B20] p-3 rounded-lg border border-white/[0.06]">
            <span className="text-[#69717D] block mb-1">INTERNAL TEMP</span>
            <span className="text-base font-bold text-[#F5F7FA] tnum">{system.internalTempC}°C</span>
          </div>

          <div className="bg-[#181B20] p-3 rounded-lg border border-white/[0.06]">
            <span className="text-[#69717D] block mb-1">FIRMWARE</span>
            <span className="text-base font-bold text-[#27C7D9]">{system.firmwareVersion}</span>
          </div>

          <div className="bg-[#181B20] p-3 rounded-lg border border-white/[0.06]">
            <span className="text-[#69717D] block mb-1">ACTIVE SECTOR</span>
            <span className="text-base font-bold text-[#F5F7FA]">{system.activeSector}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;
