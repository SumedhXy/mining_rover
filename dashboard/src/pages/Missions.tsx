import React, { useState } from 'react';
import { MissionInfo, MissionState } from '../types/rover';
import { ShieldAlert, Clock, AlertTriangle, ChevronRight, MapPin } from 'lucide-react';

interface MissionsPageProps {
  missions: MissionInfo[];
}

export const MissionsPage: React.FC<MissionsPageProps> = ({ missions }) => {
  const [selectedMission, setSelectedMission] = useState<MissionInfo | null>(missions[0] || null);

  const getStatusBadge = (st: MissionState) => {
    switch (st) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-[#18C7D8]/15 text-[#18C7D8] border border-[#18C7D8]/30">
            <span className="w-1.5 h-1.5 rounded-full bg-[#18C7D8] animate-pulse" />
            ACTIVE
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-[#15181D] text-[#A7ADB7] border border-white/[0.08]">
            COMPLETED
          </span>
        );
      case 'ABORTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-[#EF5350]/15 text-[#EF5350] border border-[#EF5350]/30">
            ABORTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium bg-[#15181D] text-[#707783] border border-white/[0.06]">
            {st}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
        <div>
          <span className="text-[11px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
            MISSION DIRECTORY
          </span>
          <h2 className="text-xl sm:text-2xl font-bold text-[#F4F6F8] tracking-tight">
            Survey Missions & Historical Logs
          </h2>
        </div>
        <span className="text-xs font-mono text-[#A7ADB7] px-3 py-1 rounded-md bg-[#101216] border border-white/[0.08]">
          {missions.length} RECORDED MISSIONS
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Missions Table / List (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          {missions.map((m) => {
            const isSelected = selectedMission?.id === m.id;
            return (
              <div
                key={m.id}
                onClick={() => setSelectedMission(m)}
                className={`nv-card p-4.5 rounded-xl cursor-pointer relative overflow-hidden transition-colors ${
                  isSelected
                    ? 'border-[#18C7D8]/50 bg-[#15181D]'
                    : 'border-white/[0.08] bg-[#101216] hover:border-white/[0.12] hover:bg-[#15181D]'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-sm font-bold text-[#F4F6F8] tracking-tight">
                        {m.id}
                      </span>
                      {getStatusBadge(m.status)}
                    </div>
                    <h3 className="text-sm font-semibold text-[#F4F6F8] tracking-tight">
                      {m.title}
                    </h3>
                  </div>

                  <ChevronRight
                    className={`w-5 h-5 transition-transform ${
                      isSelected ? 'text-[#18C7D8] translate-x-1' : 'text-[#707783]'
                    }`}
                  />
                </div>

                <div className="mt-3.5 pt-3 border-t border-white/[0.06] grid grid-cols-3 gap-2 text-xs font-mono text-[#A7ADB7]">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-[#707783]" />
                    <span>{m.durationMinutes} min</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-[#E8B84A]" />
                    <span>{m.hazardsEncountered} hazards</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    <MapPin className="w-3.5 h-3.5 text-[#707783]" />
                    <span className="truncate text-[#F4F6F8]">{m.sector}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Mission Detail Panel (5 cols) */}
        <div className="lg:col-span-5">
          {selectedMission ? (
            <div className="nv-card p-5 rounded-xl border border-white/[0.08] bg-[#101216] sticky top-24">
              <div className="flex items-center justify-between pb-3.5 border-b border-white/[0.06] mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8]">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
                      MISSION DOSSIER
                    </span>
                    <h3 className="font-semibold text-xs text-[#F4F6F8] uppercase tracking-wider">
                      Telemetry File
                    </h3>
                  </div>
                </div>
                {getStatusBadge(selectedMission.status)}
              </div>

              <div className="space-y-4 text-xs font-mono">
                <div>
                  <span className="text-[10px] font-semibold text-[#A7ADB7] uppercase tracking-wider block mb-1">
                    ASSIGNMENT
                  </span>
                  <div className="text-sm font-semibold text-[#F4F6F8] tracking-tight">
                    {selectedMission.id} — {selectedMission.title}
                  </div>
                </div>

                <div className="bg-[#15181D] p-3.5 rounded-lg border border-white/[0.06] text-[#A7ADB7] text-xs leading-relaxed">
                  {selectedMission.description}
                </div>

                <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                  <div className="flex justify-between py-1.5 border-b border-white/[0.04]">
                    <span className="text-[#707783]">Sector</span>
                    <span className="text-[#F4F6F8] font-medium">{selectedMission.sector}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/[0.04]">
                    <span className="text-[#707783]">Deployment</span>
                    <span className="text-[#F4F6F8] font-medium">{selectedMission.startTime}</span>
                  </div>
                  {selectedMission.endTime && (
                    <div className="flex justify-between py-1.5 border-b border-white/[0.04]">
                      <span className="text-[#707783]">Concluded</span>
                      <span className="text-[#F4F6F8] font-medium">{selectedMission.endTime}</span>
                    </div>
                  )}
                  <div className="flex justify-between py-1.5 border-b border-white/[0.04]">
                    <span className="text-[#707783]">Duration</span>
                    <span className="text-[#F4F6F8] font-medium tnum">{selectedMission.durationMinutes} minutes</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#707783]">Hazards Logged</span>
                    <span className="text-[#E8B84A] font-bold tnum">{selectedMission.hazardsEncountered} anomalies</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-white/[0.06] text-[11px] text-[#707783]">
                  Backend API: <code className="text-[#18C7D8]">GET /api/missions/{selectedMission.id}</code>
                </div>
              </div>
            </div>
          ) : (
            <div className="nv-card p-8 rounded-xl border border-white/[0.08] bg-[#101216] text-center text-[#707783] text-xs font-mono">
              Select a mission from the list to view telemetry details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MissionsPage;
