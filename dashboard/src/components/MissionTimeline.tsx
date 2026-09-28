import React from 'react';
import { MissionEvent, SeverityLevel } from '../types/rover';
import { FileText } from 'lucide-react';

interface MissionTimelineProps {
  events: MissionEvent[];
  maxEvents?: number;
}

export const MissionTimeline: React.FC<MissionTimelineProps> = ({
  events,
  maxEvents = 10,
}) => {
  const displayEvents = events.slice(-maxEvents).reverse();

  const getSeverityDot = (sev: SeverityLevel) => {
    switch (sev) {
      case 'CRITICAL':
      case 'HIGH':
        return 'bg-[#EF5350]';
      case 'MEDIUM':
        return 'bg-[#E8B84A]';
      case 'LOW':
        return 'bg-[#707783]';
      case 'NORMAL':
      default:
        return 'bg-[#24C88A]';
    }
  };

  return (
    <div className="nv-card p-5 rounded-xl border border-white/[0.08] bg-[#101216]">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.06] mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8]">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
              MISSION TIMELINE
            </span>
            <span className="text-xs font-semibold text-[#F4F6F8]">
              Chronological Activity Log
            </span>
          </div>
        </div>
        <span className="text-[10px] font-mono text-[#A7ADB7] bg-[#15181D] px-2 py-0.5 rounded border border-white/[0.08]">
          FIFO STREAM ({events.length} EVENTS)
        </span>
      </div>

      {/* Events List */}
      {displayEvents.length === 0 ? (
        <div className="py-8 text-center text-[#707783] font-mono text-xs border border-dashed border-white/[0.08] rounded-lg">
          NO MISSION EVENTS LOGGED YET
        </div>
      ) : (
        <div className="space-y-3 max-h-72 overflow-y-auto pr-1.5 relative before:absolute before:inset-0 before:left-2 before:w-px before:bg-white/[0.06]">
          {displayEvents.map((ev) => (
            <div key={ev.id} className="relative flex items-start gap-3 pl-6">
              {/* Timeline dot */}
              <span
                className={`absolute left-[5px] top-1.5 w-2 h-2 rounded-full ${getSeverityDot(
                  ev.severity
                )}`}
              />

              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-xs font-medium text-[#A7ADB7] tnum">
                    {ev.time}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#15181D] text-[#A7ADB7] border border-white/[0.08] uppercase">
                    {ev.type}
                  </span>
                </div>
                <p className="text-xs text-[#F4F6F8] font-sans mt-0.5 break-words">
                  {ev.event}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MissionTimeline;
