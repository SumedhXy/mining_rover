import React from 'react';
import { SensorItem, ConnectionStatus } from '../types/rover';
import { SensorCard } from './SensorCard';
import { Activity } from 'lucide-react';

interface SensorGridProps {
  sensors: SensorItem[];
  connectionStatus?: ConnectionStatus;
}

export const SensorGrid: React.FC<SensorGridProps> = ({
  sensors,
  connectionStatus = 'ONLINE',
}) => {
  return (
    <div className="space-y-3.5">
      <div className="flex items-center justify-between pb-0.5">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8]">
            <Activity className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="text-[11px] font-semibold text-[#A7ADB7] tracking-wider uppercase">
              ENVIRONMENTAL & POWERTRAIN TELEMETRY
            </span>
            <span className="text-xs text-[#707783] hidden sm:inline ml-2">
              • CAN Bus Sensor Network
            </span>
          </div>
        </div>
        <span className="text-[11px] font-mono text-[#A7ADB7] bg-[#15181D] px-2.5 py-0.5 rounded border border-white/[0.08]">
          {sensors.length} ACTIVE CHANNELS (100 Hz FIFO)
        </span>
      </div>

      {/* Responsive Grid: 4 columns on desktop with balanced rectangular aspect */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {sensors.map((s) => (
          <SensorCard
            key={s.id}
            label={s.label}
            value={s.value}
            unit={s.unit}
            status={s.status}
            min={s.min}
            max={s.max}
            nominalRange={s.nominalRange}
            connectionStatus={connectionStatus}
          />
        ))}
      </div>
    </div>
  );
};

export default SensorGrid;
