import React from 'react';
import { DecisionData, SeverityLevel, ConnectionStatus } from '../types/rover';
import { CheckCircle2, AlertTriangle, AlertOctagon, ShieldCheck } from 'lucide-react';

interface HazardCardProps {
  decision: DecisionData;
  connectionStatus?: ConnectionStatus;
}

export const HazardCard: React.FC<HazardCardProps> = ({
  decision,
  connectionStatus = 'ONLINE',
}) => {
  const isDisconnected = connectionStatus === 'DISCONNECTED';

  const getSeverityBadge = (sev: SeverityLevel) => {
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="px-2.5 py-1 rounded-[6px] text-xs font-mono font-semibold bg-[#EF5350]/10 text-[#EF5350] border border-[#EF5350]/35 uppercase tracking-wider">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2.5 py-1 rounded-[6px] text-xs font-mono font-semibold bg-[#EF5350]/10 text-[#EF5350] border border-[#EF5350]/35 uppercase tracking-wider">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2.5 py-1 rounded-[6px] text-xs font-mono font-semibold bg-[#E8B84A]/10 text-[#E8B84A] border border-[#E8B84A]/35 uppercase tracking-wider">
            WARNING
          </span>
        );
      case 'LOW':
        return (
          <span className="px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#24C88A]/10 text-[#24C88A] border border-[#24C88A]/25 uppercase tracking-wider">
            LOW RISK
          </span>
        );
      case 'NORMAL':
      default:
        return (
          <span className="px-2.5 py-1 rounded-[6px] text-xs font-mono font-medium bg-[#24C88A]/10 text-[#24C88A] border border-[#24C88A]/25 uppercase tracking-wider">
            SAFE
          </span>
        );
    }
  };

  const getHazardIcon = (sev: SeverityLevel) => {
    switch (sev) {
      case 'CRITICAL':
      case 'HIGH':
        return <AlertOctagon className="w-4 h-4 text-[#EF5350]" />;
      case 'MEDIUM':
        return <AlertTriangle className="w-4 h-4 text-[#E8B84A]" />;
      case 'LOW':
      case 'NORMAL':
      default:
        return <CheckCircle2 className="w-4 h-4 text-[#24C88A]" />;
    }
  };

  const confidencePct = Math.round((decision.confidence ?? 0.85) * 100);
  const isCritical = decision.severity === 'HIGH' || decision.severity === 'CRITICAL';
  const isWarning = decision.severity === 'MEDIUM';

  const reasonsList = decision.reasons && decision.reasons.length > 0
    ? decision.reasons
    : (decision.reason ? [decision.reason] : ['Sensor and optical telemetry within baseline limits']);

  return (
    <div
      className={`nv-card p-6 rounded-[14px] border flex flex-col justify-between transition-colors w-full min-w-0 box-border ${
        isCritical
          ? 'bg-[#141215] border-[#EF5350]/35'
          : isWarning
          ? 'bg-[#151413] border-[#E8B84A]/30'
          : 'bg-[#101216] border-white/[0.07]'
      }`}
    >
      <div>
        {/* Header Bar */}
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.06] mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-8 h-8 rounded-md border flex items-center justify-center shrink-0 ${
              isCritical 
                ? 'bg-[#EF5350]/10 border-[#EF5350]/30' 
                : isWarning 
                ? 'bg-[#E8B84A]/10 border-[#E8B84A]/30' 
                : 'bg-[#15181D] border-white/[0.08]'
            }`}>
              {getHazardIcon(decision.severity)}
            </div>
            <div className="min-w-0 truncate">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold tracking-[0.08em] uppercase text-[#A7ADB7]">
                  DECISION ENGINE
                </span>
                <span className="text-[10px] font-mono text-[#707783]">[ADVISORY]</span>
              </div>
              <span className="text-xs font-semibold text-[#F4F6F8] tracking-tight block truncate">
                Current Hazard Assessment
              </span>
            </div>
          </div>

          <div className="shrink-0 ml-3">{getSeverityBadge(decision.severity)}</div>
        </div>

        {/* Current Assessment Headline */}
        <div className="mb-5 min-w-0">
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#707783] block mb-1">
            CURRENT ASSESSMENT
          </span>
          <h2
            className={`text-3xl sm:text-4xl font-bold tracking-tight uppercase leading-none mb-3 break-words ${
              isCritical
                ? 'text-[#EF5350]'
                : isWarning
                ? 'text-[#E8B84A]'
                : 'text-[#F4F6F8]'
            }`}
          >
            {decision.hazard}
          </h2>

          {/* Compact Inline Confidence Metric */}
          <div className="flex items-center gap-3 text-xs font-sans text-[#A7ADB7]">
            <span className="font-medium text-[#A7ADB7]">Confidence</span>
            <span className="text-sm font-bold font-mono text-[#F4F6F8] tnum">{confidencePct}%</span>
            <div className="w-28 h-1.5 bg-[#15181D] border border-white/[0.06] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  isCritical ? 'bg-[#EF5350]' : isWarning ? 'bg-[#E8B84A]' : 'bg-[#24C88A]'
                }`}
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Supporting Evidence List (Inset Surface) */}
        <div className="bg-white/[0.025] p-4 rounded-[10px] border border-white/[0.06] mb-5 min-w-0">
          <span className="text-[11px] font-semibold text-[#A7ADB7] uppercase tracking-[0.08em] block mb-2.5">
            SUPPORTING EVIDENCE
          </span>
          <ul className="space-y-2">
            {reasonsList.map((reason, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-xs text-[#F4F6F8] leading-relaxed">
                <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                  isCritical ? 'bg-[#EF5350]' : isWarning ? 'bg-[#E8B84A]' : 'bg-[#24C88A]'
                }`} />
                <span className="break-words">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Recommended Tactical Action Strip */}
      <div className={`h-[52px] px-4 rounded-[10px] border flex items-center justify-between text-xs font-sans w-full min-w-0 ${
        isCritical
          ? 'bg-[#EF5350]/12 border-[#EF5350]/30 text-[#EF5350]'
          : isWarning
          ? 'bg-[#E8B84A]/12 border-[#E8B84A]/30 text-[#E8B84A]'
          : 'bg-[#15181D] border-white/[0.06] text-[#A7ADB7]'
      }`}>
        <div className="flex items-center gap-2.5 min-w-0 truncate pr-2">
          <ShieldCheck className="w-4.5 h-4.5 shrink-0 text-[#EF5350]" />
          <span className="font-semibold tracking-wide truncate">
            {decision.recommended_action || (isCritical ? 'HALT ADVANCE & ALERT OPERATIONS' : 'CONTINUE AUTONOMOUS PATROL')}
          </span>
        </div>
        <span className="text-[10px] font-mono text-[#EF5350]/80 tracking-wider uppercase shrink-0 hidden sm:inline">
          SAFETY ADVISORY
        </span>
      </div>
    </div>
  );
};

export default HazardCard;
