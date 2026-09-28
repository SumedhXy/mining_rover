import React, { useState, useEffect } from 'react';
import { ConnectionStatus } from '../types/rover';
import {
  Thermometer,
  Droplets,
  Flame,
  Wind,
  Gauge,
  BatteryCharging,
  Activity,
  Zap,
  Info,
  X,
} from 'lucide-react';

interface SensorCardProps {
  label: string;
  value: number | string;
  unit?: string;
  status?: 'GOOD' | 'WARNING' | 'CRITICAL' | 'NORMAL';
  connectionStatus?: ConnectionStatus;
  min?: number;
  max?: number;
  nominalRange?: string;
}

export const SensorCard: React.FC<SensorCardProps> = ({
  label,
  value,
  unit = '',
  status = 'NORMAL',
  connectionStatus = 'ONLINE',
  min,
  max,
  nominalRange,
}) => {
  const isDisconnected = connectionStatus === 'DISCONNECTED';
  const [showDetail, setShowDetail] = useState<boolean>(false);

  useEffect(() => {
    if (!showDetail) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowDetail(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showDetail]);

  const isGasSensor = label.toUpperCase().includes('MQ-4') || 
                      label.toUpperCase().includes('MQ-135') || 
                      label.toUpperCase().includes('METHANE') || 
                      label.toUpperCase().includes('AIR QUALITY');

  const getSensorSubtitle = (lbl: string) => {
    const l = lbl.toUpperCase();
    if (l.includes('MQ-4') || l.includes('METHANE')) return 'Methane Index';
    if (l.includes('MQ-135') || l.includes('AIR')) return 'Air Quality Index';
    if (l.includes('TEMP')) return 'Ambient Temperature';
    if (l.includes('HUM')) return 'Atmospheric Humidity';
    if (l.includes('PRES')) return 'Barometric Pressure';
    if (l.includes('BAT')) return 'Power Bus Level';
    if (l.includes('VIB') || l.includes('SEISMIC')) return 'Structural Vibration';
    if (l.includes('VOLT')) return 'Main DC Voltage';
    return 'Telemetry Channel';
  };

  const getSensorIcon = (lbl: string) => {
    const l = lbl.toUpperCase();
    if (l.includes('TEMP')) return <Thermometer className="w-4 h-4 text-[#A7ADB7]" />;
    if (l.includes('HUM')) return <Droplets className="w-4 h-4 text-[#A7ADB7]" />;
    if (l.includes('PRES')) return <Gauge className="w-4 h-4 text-[#A7ADB7]" />;
    if (l.includes('MQ-4') || l.includes('METHANE')) return <Flame className="w-4 h-4 text-[#18C7D8]" />;
    if (l.includes('MQ-135') || l.includes('AIR')) return <Wind className="w-4 h-4 text-[#18C7D8]" />;
    if (l.includes('BAT')) return <BatteryCharging className="w-4 h-4 text-[#A7ADB7]" />;
    if (l.includes('VOLT')) return <Zap className="w-4 h-4 text-[#A7ADB7]" />;
    return <Activity className="w-4 h-4 text-[#A7ADB7]" />;
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#EF5350]/15 text-[#EF5350] border border-[#EF5350]/30 uppercase tracking-wider">
            CRITICAL
          </span>
        );
      case 'WARNING':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#E8B84A]/15 text-[#E8B84A] border border-[#E8B84A]/30 uppercase tracking-wider">
            WARNING
          </span>
        );
      case 'GOOD':
      case 'NORMAL':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#24C88A]/10 text-[#24C88A] border border-[#24C88A]/25 uppercase tracking-wider">
            NORMAL
          </span>
        );
    }
  };

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        aria-label={`${label} telemetry: ${value} ${unit}`}
        onClick={() => setShowDetail(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setShowDetail(true);
          }
        }}
        className={`nv-card p-4 rounded-xl cursor-pointer group transition-colors flex flex-col justify-between select-none relative ${
          isGasSensor
            ? 'border-white/[0.10] bg-[#13161C]'
            : 'border-white/[0.07] bg-[#101216]'
        } ${isDisconnected ? 'opacity-60 border-[#EF5350]/30' : ''}`}
      >
        {/* Top Header Strip */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-md border flex items-center justify-center ${
              isGasSensor 
                ? 'bg-[#15181D] border-white/[0.10]' 
                : 'bg-[#15181D] border-white/[0.08]'
            }`}>
              {getSensorIcon(label)}
            </div>
            <div>
              <span className="text-[11px] font-semibold text-[#A7ADB7] block tracking-wider uppercase group-hover:text-[#F4F6F8] transition-colors">
                {label}
              </span>
              <span className="text-[10px] font-mono text-[#707783] block leading-tight">
                {getSensorSubtitle(label)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {getStatusBadge(status)}
            <Info className="w-3.5 h-3.5 text-[#707783] opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>

        {/* Primary Value Display: 32px Large Number + Smaller Unit */}
        <div className="my-2.5 flex items-baseline justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-mono font-bold text-[#F4F6F8] tnum tracking-tight">
              {value}
            </span>
            {unit && (
              <span className="text-xs font-mono text-[#A7ADB7] font-medium uppercase">
                {unit}
              </span>
            )}
          </div>

          {/* Real-time CAN stream pulse */}
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-[#707783]">
            <span className={`w-1.5 h-1.5 rounded-full ${
              status === 'CRITICAL' 
                ? 'bg-[#EF5350] animate-ping' 
                : status === 'WARNING' 
                ? 'bg-[#E8B84A] animate-pulse' 
                : 'bg-[#24C88A]'
            }`} />
            <span className="hidden sm:inline">LIVE</span>
          </div>
        </div>

        {/* Card Footer: Reference Range & Update Age */}
        <div className="pt-2.5 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-[#707783]">
          <span className="text-[#A7ADB7]">
            {nominalRange ? `Limit: ${nominalRange}` : 'Nominal Band'}
          </span>
          <span className="text-[#707783]">
            Updated 1s ago
          </span>
        </div>
      </div>

      {/* Sensor Diagnostic Modal */}
      {showDetail && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={`dialog-title-${label}`}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowDetail(false);
          }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
        >
          <div className="bg-[#111317] border border-white/[0.12] rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <button
              type="button"
              onClick={() => setShowDetail(false)}
              aria-label="Close modal"
              className="absolute top-4 right-4 text-[#A7ADB7] hover:text-[#F5F7FA] transition-colors cursor-pointer p-1 rounded-md hover:bg-[#181B20]"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4 pb-3 border-b border-white/[0.08]">
              <div className="w-8 h-8 rounded-md bg-[#181B20] border border-white/[0.1] flex items-center justify-center">
                {getSensorIcon(label)}
              </div>
              <div>
                <h3 id={`dialog-title-${label}`} className="text-base font-semibold text-[#F5F7FA] tracking-tight">
                  {label}
                </h3>
                <span className="text-xs font-mono text-[#A7ADB7]">
                  {getSensorSubtitle(label)}
                </span>
              </div>
            </div>

            <div className="space-y-4">
              <div className="bg-[#15181D] p-4 rounded-lg border border-white/[0.06]">
                <div className="text-[11px] font-mono text-[#A7ADB7] uppercase mb-1">
                  CURRENT VALUE
                </div>
                <div className="text-3xl font-mono font-bold text-[#F4F6F8] tnum flex items-baseline gap-2">
                  <span>{value}</span>
                  <span className="text-sm text-[#A7ADB7]">{unit}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06]">
                  <span className="text-[#707783] block mb-1">SAFETY STATUS</span>
                  <div>{getStatusBadge(status)}</div>
                </div>
                <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06]">
                  <span className="text-[#707783] block mb-1">SAMPLING RATE</span>
                  <span className="text-[#F4F6F8] font-medium">100 Hz FIFO</span>
                </div>
              </div>

              <div className="bg-[#15181D] p-3 rounded-lg border border-white/[0.06] text-xs font-mono space-y-1.5">
                <div className="flex justify-between text-[#A7ADB7]">
                  <span>Nominal Safe Band:</span>
                  <span className="text-[#F4F6F8] font-medium">{nominalRange || 'Standard Operational Band'}</span>
                </div>
                <div className="flex justify-between text-[#A7ADB7]">
                  <span>Transducer Bus:</span>
                  <span className="text-[#18C7D8]">CAN 2.0B / I2C Arbitration</span>
                </div>
              </div>

              <p className="text-xs text-[#A7ADB7] leading-relaxed">
                Sensor telemetry is acquired via local ESP32 arbitration and processed through SQLite offline storage before local FastAPI streaming.
              </p>

              <button
                type="button"
                onClick={() => setShowDetail(false)}
                className="w-full nv-btn-outline text-xs mt-2"
              >
                Close Diagnostics
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SensorCard;
