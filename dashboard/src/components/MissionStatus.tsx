import React from 'react';
import { MissionInfo, MissionState } from '../types/rover';
import { Compass, Clock, AlertTriangle, MapPin } from 'lucide-react';

interface MissionStatusProps {
  mission: MissionInfo;
}

export const MissionStatus: React.FC<MissionStatusProps> = ({ mission }) => {
  const getStatusBadge = (st: MissionState) => {
    switch (st) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#18C7D8]/10 text-[#18C7D8] border border-[#18C7D8]/35">
            <span className="w-1.5 h-1.5 rounded-full bg-[#18C7D8] animate-pulse" />
            ACTIVE
          </span>
        );
      case 'PAUSED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#E8B84A]/10 text-[#E8B84A] border border-[#E8B84A]/35">
            PAUSED
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#15181D] text-[#A7ADB7] border border-white/[0.08]">
            COMPLETED
          </span>
        );
      case 'ABORTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#EF5350]/10 text-[#EF5350] border border-[#EF5350]/35">
            ABORTED
          </span>
        );
      case 'IDLE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#15181D] text-[#707783] border border-white/[0.06]">
            STANDBY
          </span>
        );
    }
  };

  return (
    <div className="nv-card p-6 rounded-[14px] border border-white/[0.07] bg-[#101216] w-full min-w-0 box-border">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/[0.06] mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8] shrink-0">
            <Compass className="w-4 h-4" />
          </div>
          <div className="min-w-0 truncate">
            <span className="text-[11px] font-semibold text-[#A7ADB7] tracking-[0.08em] uppercase block">
              MISSION DIRECTIVE
            </span>
            <span className="text-xs font-semibold text-[#F4F6F8] block truncate">
              Operational Overview
            </span>
          </div>
        </div>
        <div className="shrink-0 ml-3">{getStatusBadge(mission.status)}</div>
      </div>

      {/* Primary Mission Title & Designation */}
      <div className="mb-5 min-w-0">
        <h3 className="text-xl sm:text-2xl font-bold text-[#F4F6F8] tracking-tight leading-snug mb-1.5 break-words max-w-full">
          {mission.title || 'Underground Exploration'}
        </h3>
        <div className="flex items-center gap-2 text-xs font-mono text-[#A7ADB7]">
          <span className="text-[#18C7D8] font-semibold">{mission.id}</span>
          <span className="text-[#707783]">•</span>
          <span>{mission.durationMinutes} min elapsed</span>
        </div>
      </div>

      {/* Grid: 2 Equal-width Metric Cards */}
      <div className="grid grid-cols-2 gap-3 mb-4 min-w-0">
        <div className="bg-[#15181D] p-4 rounded-[10px] border border-white/[0.06]">
          <div className="flex items-center gap-1.5 text-[#707783] mb-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#A7ADB7]">ELAPSED</span>
          </div>
          <span className="font-mono text-2xl font-bold text-[#F4F6F8] tnum block">
            {mission.durationMinutes} min
          </span>
        </div>

        <div className="bg-[#15181D] p-4 rounded-[10px] border border-white/[0.06]">
          <div className="flex items-center gap-1.5 text-[#707783] mb-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-[#E8B84A]" />
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#A7ADB7]">HAZARDS</span>
          </div>
          <span className="font-mono text-2xl font-bold text-[#E8B84A] tnum block">
            {mission.hazardsEncountered} events
          </span>
        </div>
      </div>

      {/* Sector Location Strip */}
      <div className="flex items-center justify-between text-xs font-mono text-[#707783] pt-3 border-t border-white/[0.06] min-w-0">
        <div className="flex items-center gap-2 min-w-0 truncate pr-2">
          <MapPin className="w-3.5 h-3.5 text-[#18C7D8] shrink-0" />
          <span className="truncate text-[#F4F6F8]">{mission.sector}</span>
        </div>
        <span className="text-[#707783] text-[10px] shrink-0">
          STARTED: {mission.startTime || '10:42:00'}
        </span>
      </div>
    </div>
  );
};

export default MissionStatus;
