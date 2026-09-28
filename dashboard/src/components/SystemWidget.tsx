import React from 'react';
import { RoverSystemInfo, ConnectionStatus, SyncStatusInfo } from '../types/rover';
import { Cpu, Camera, Activity, Database, ShieldCheck } from 'lucide-react';

interface SystemWidgetProps {
  system: RoverSystemInfo;
  connectionStatus?: ConnectionStatus;
  syncStatus?: SyncStatusInfo | null;
}

export const SystemWidget: React.FC<SystemWidgetProps> = ({
  system,
  connectionStatus = 'ONLINE',
  syncStatus = null,
}) => {
  const isDisconnected = connectionStatus === 'DISCONNECTED';
  const effectiveRover = isDisconnected ? 'OFFLINE' : (system.rover?.toUpperCase() || 'RUNNING');
  const effectiveCamera = isDisconnected ? 'UNAVAILABLE' : (system.cameraStatus?.toUpperCase() || 'OPERATIONAL');
  const effectiveSensor = isDisconnected ? 'OFFLINE' : (system.sensorStatus?.toUpperCase() || 'NOMINAL');
  const effectiveDatabase = isDisconnected ? 'OFFLINE' : (system.databaseStatus?.toUpperCase() || 'CONNECTED');
  const cpuTemp = system.cpuTemperatureC ?? system.internalTempC ?? 42.5;
  const storageMb = system.storageAvailableMb ?? 3140;

  const getStatusBadge = (status: string, okValues: string[]) => {
    const isOk = okValues.includes(status);
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${
          isOk
            ? 'bg-[#24C88A]/10 border-[#24C88A]/30 text-[#24C88A]'
            : 'bg-[#EF5350]/10 border-[#EF5350]/30 text-[#EF5350]'
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isOk ? 'bg-[#24C88A]' : 'bg-[#EF5350]'
          }`}
        />
        {status}
      </span>
    );
  };

  return (
    <div className="nv-card p-5 rounded-xl border border-white/[0.08] bg-[#101216] flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.06] mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8]">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
              SYSTEM HEALTH
            </span>
            <span className="text-xs font-semibold text-[#F4F6F8]">Engineering Diagnostics</span>
          </div>
        </div>
        <span className="text-[10px] font-mono text-[#24C88A] bg-[#24C88A]/10 px-2 py-0.5 rounded border border-[#24C88A]/30 font-medium">
          ● PLATFORM NOMINAL
        </span>
      </div>

      {/* 2x2 Grid of Engineering Diagnostics */}
      <div className="grid grid-cols-2 gap-2.5 mb-3.5">
        {/* Rover Core */}
        <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-[#A7ADB7]" />
            <span className="text-xs font-mono text-[#F4F6F8]">Rover Core</span>
          </div>
          {getStatusBadge(effectiveRover, ['RUNNING', 'NOMINAL'])}
        </div>

        {/* Optical Camera */}
        <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Camera className="w-3.5 h-3.5 text-[#A7ADB7]" />
            <span className="text-xs font-mono text-[#F4F6F8]">Camera Feed</span>
          </div>
          {getStatusBadge(effectiveCamera, ['OPERATIONAL', 'STANDBY'])}
        </div>

        {/* Sensor Arbitration */}
        <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-[#A7ADB7]" />
            <span className="text-xs font-mono text-[#F4F6F8]">Sensors</span>
          </div>
          {getStatusBadge(effectiveSensor, ['NOMINAL', 'OPERATIONAL'])}
        </div>

        {/* Local SQLite Database */}
        <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-3.5 h-3.5 text-[#A7ADB7]" />
            <span className="text-xs font-mono text-[#F4F6F8]">SQLite DB</span>
          </div>
          {getStatusBadge(effectiveDatabase, ['CONNECTED', 'LOCAL-ONLY'])}
        </div>
      </div>

      {/* Diagnostics Readout Strip: Storage, CPU Temp, Sync Mode */}
      <div className="pt-3 border-t border-white/[0.06] grid grid-cols-3 gap-2 text-center font-mono">
        <div className="bg-[#15181D] p-2.5 rounded-lg border border-white/[0.06]">
          <span className="text-[9px] text-[#707783] block uppercase font-medium">STORAGE AVAIL</span>
          <span className="text-xs font-bold text-[#F4F6F8] tnum">
            {(storageMb / 1024).toFixed(1)} GB
          </span>
        </div>

        <div className="bg-[#15181D] p-2.5 rounded-lg border border-white/[0.06]">
          <span className="text-[9px] text-[#707783] block uppercase font-medium">CPU TEMP</span>
          <span className={`text-xs font-bold tnum ${
            cpuTemp > 70 ? 'text-[#EF5350]' : cpuTemp > 55 ? 'text-[#E8B84A]' : 'text-[#24C88A]'
          }`}>
            {cpuTemp.toFixed(1)} °C
          </span>
        </div>

        <div className="bg-[#15181D] p-2.5 rounded-lg border border-white/[0.06]">
          <span className="text-[9px] text-[#707783] block uppercase font-medium">DATA SYNC</span>
          <span className="text-xs font-bold text-[#A7ADB7]">
            {syncStatus?.network === 'online' ? 'REMOTE' : 'OFFLINE-1ST'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SystemWidget;
