import React, { useState, useEffect } from 'react';
import { ConnectionStatus, SyncStatusInfo } from '../types/rover';
import { MockScenario } from '../data/mockData';
import { Activity, ShieldAlert, FileText, Cpu, Sliders, UploadCloud, Cloud, CloudOff } from 'lucide-react';

interface HeaderProps {
  currentTab: 'dashboard' | 'missions' | 'logs' | 'system';
  onTabChange: (tab: 'dashboard' | 'missions' | 'logs' | 'system') => void;
  connectionStatus: ConnectionStatus;
  onConnectionChange: (st: ConnectionStatus) => void;
  missionId: string;
  activeScenario: MockScenario;
  onScenarioChange: (sc: MockScenario) => void;
  backendOnline?: boolean;
  isLiveMode?: boolean;
  onToggleLiveMode?: () => void;
  onPushToBackend?: () => void;
  isPushing?: boolean;
  syncStatus?: SyncStatusInfo | null;
  onTriggerSync?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  connectionStatus,
  missionId,
  activeScenario,
  onScenarioChange,
  backendOnline = false,
  isLiveMode = true,
  onToggleLiveMode,
  onPushToBackend,
  isPushing = false,
  syncStatus = null,
  onTriggerSync,
}) => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [showSimBar, setShowSimBar] = useState<boolean>(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toTimeString().split(' ')[0]);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Keyboard shortcut listener for tabs (1 = Dashboard, 2 = Missions, 3 = Logs, 4 = System)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === '1') onTabChange('dashboard');
      if (e.key === '2') onTabChange('missions');
      if (e.key === '3') onTabChange('logs');
      if (e.key === '4') onTabChange('system');
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onTabChange]);

  const navItems = [
    { id: 'dashboard', label: 'Overview', keyHint: '1', icon: Activity },
    { id: 'missions', label: 'Missions', keyHint: '2', icon: ShieldAlert },
    { id: 'logs', label: 'Logs', keyHint: '3', icon: FileText },
    { id: 'system', label: 'System', keyHint: '4', icon: Cpu },
  ] as const;

  const isRoverOnline = backendOnline && connectionStatus !== 'DISCONNECTED';

  return (
    <header className="border-b border-white/[0.06] bg-[#08090B] sticky top-0 z-30">
      {/* Primary Top Bar */}
      <div className="max-w-[1536px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between py-3 md:h-16 gap-3">
          {/* Brand & Identification */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8] font-mono font-bold text-xs select-none shadow-sm">
              MR
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold tracking-wider uppercase text-[#A7ADB7]">
                  MINING ROVER
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#15181D] text-[#F4F6F8] border border-white/[0.08] font-mono font-medium">
                  {missionId}
                </span>
              </div>
              <h1 className="text-sm font-semibold tracking-tight text-[#F4F6F8]">
                Command Operations Console
              </h1>
            </div>
          </div>

          {/* Navigation - Restrained Tab Bar with Subtle Cyan Underline */}
          <nav
            role="tablist"
            aria-label="Console Views"
            className="flex items-center gap-1"
          >
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  role="tab"
                  aria-selected={isActive}
                  type="button"
                  onClick={() => onTabChange(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium transition-colors cursor-pointer rounded-md relative ${
                    isActive
                      ? 'text-[#F4F6F8] bg-[#15181D]'
                      : 'text-[#A7ADB7] hover:text-[#F4F6F8] hover:bg-[#101216]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#18C7D8]' : 'text-[#707783]'}`} />
                  <span>{item.label}</span>
                  <span className={`text-[10px] font-mono ${isActive ? 'text-[#18C7D8]' : 'text-[#707783]'}`}>
                    [{item.keyHint}]
                  </span>
                  {isActive && (
                    <span className="absolute bottom-0 inset-x-2 h-[2px] bg-[#18C7D8] rounded-full" />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Status Indicators */}
          <div className="flex items-center gap-2.5 sm:gap-3 self-end md:self-auto text-xs">
            {/* Live Clock with Tabular Numbers */}
            <div className="text-right hidden sm:block">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-[#707783] block leading-tight">
                SYS TIME
              </span>
              <span className="font-mono text-xs font-medium text-[#F4F6F8] tnum">
                {currentTime || '00:00:00'}
              </span>
            </div>

            <div className="h-4 w-px bg-white/[0.08] hidden sm:block" />

            {/* Rover Local Backend Reachability */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] font-medium border select-none transition-colors ${
                isRoverOnline
                  ? 'bg-[#24C88A]/10 border-[#24C88A]/25 text-[#24C88A]'
                  : 'bg-[#EF5350]/10 border-[#EF5350]/25 text-[#EF5350]'
              }`}
              title={isRoverOnline ? 'Rover Local API: Connected (:8000)' : 'Rover Local API: Unreachable'}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isRoverOnline ? 'bg-[#24C88A]' : 'bg-[#EF5350]'
                }`}
              />
              <span>ROVER: {isRoverOnline ? 'ONLINE' : 'OFFLINE'}</span>
            </div>

            {/* Remote Synchronization / Internet Reachability */}
            <div
              onClick={onTriggerSync}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-mono text-[11px] font-medium border transition-all cursor-pointer select-none ${
                syncStatus?.network === 'online'
                  ? syncStatus.pending_count > 0
                    ? 'bg-[#E8B84A]/10 border-[#E8B84A]/25 text-[#E8B84A] hover:bg-[#E8B84A]/20'
                    : 'bg-[#24C88A]/10 border-[#24C88A]/25 text-[#24C88A] hover:bg-[#24C88A]/20'
                  : 'bg-[#15181D] border-white/[0.08] text-[#A7ADB7] hover:text-[#F4F6F8]'
              }`}
              title={`Cloud Synchronization: ${syncStatus?.network === 'online' ? 'CONNECTED' : 'OFFLINE (Local Store Active)'} • ${syncStatus?.pending_count ?? 0} records queued for sync`}
            >
              {syncStatus?.network === 'online' ? (
                <Cloud className="w-3.5 h-3.5 text-[#24C88A]" />
              ) : (
                <CloudOff className="w-3.5 h-3.5 text-[#707783]" />
              )}
              <span>
                SYNC: {syncStatus?.network === 'online'
                  ? syncStatus.pending_count > 0
                    ? `SYNCING (${syncStatus.pending_count})`
                    : 'ONLINE'
                  : `OFFLINE (${syncStatus?.pending_count ?? 0})`}
              </span>
            </div>

            {/* Simulation Controls Toggle */}
            <button
              type="button"
              onClick={() => setShowSimBar(!showSimBar)}
              title="Toggle Simulation & Development Controls"
              aria-label="Toggle simulation toolbar"
              className={`p-1.5 border text-xs flex items-center transition-colors cursor-pointer rounded-md ${
                showSimBar
                  ? 'bg-[#18C7D8]/15 text-[#18C7D8] border-[#18C7D8]/35'
                  : 'bg-[#15181D] border-white/[0.08] text-[#A7ADB7] hover:text-[#F4F6F8]'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Dev & Simulation Telemetry Toolbar */}
      {showSimBar && (
        <div className="bg-[#101216] border-t border-white/[0.06] px-4 sm:px-6 py-2">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded font-mono font-medium text-[11px] border ${
                backendOnline 
                  ? 'bg-[#24C88A]/10 border-[#24C88A]/25 text-[#24C88A]' 
                  : 'bg-[#EF5350]/10 border-[#EF5350]/25 text-[#EF5350]'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${backendOnline ? 'bg-[#24C88A]' : 'bg-[#EF5350]'}`} />
                <span>FASTAPI: {backendOnline ? 'CONNECTED (:8000)' : 'UNREACHABLE'}</span>
              </div>

              {onToggleLiveMode && (
                <button
                  type="button"
                  onClick={onToggleLiveMode}
                  className={`px-2.5 py-1 text-[11px] font-mono font-semibold border rounded transition-colors cursor-pointer ${
                    isLiveMode
                      ? 'bg-[#18C7D8] text-[#08090B] border-[#18C7D8] font-bold'
                      : 'bg-[#15181D] text-[#A7ADB7] border-white/[0.08] hover:text-white'
                  }`}
                  title="Toggle between live backend polling and simulated scenarios"
                >
                  {isLiveMode ? '● LIVE MODE' : 'SIMULATION MODE'}
                </button>
              )}

              <span className="text-[#707783] text-xs hidden sm:inline">|</span>
              <span className="text-[#A7ADB7] text-[11px] hidden lg:inline font-mono">
                {isLiveMode ? 'Streaming live CAN bus & YOLO telemetry:' : 'Select test scenario:'}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              {(
                [
                  { id: 'fire', label: 'Fire Scenario' },
                  { id: 'gas', label: 'Gas Leak' },
                  { id: 'rockfall', label: 'Rockfall' },
                  { id: 'nominal', label: 'Nominal' },
                ] as const
              ).map((sc) => (
                <button
                  key={sc.id}
                  type="button"
                  onClick={() => onScenarioChange(sc.id)}
                  className={`px-2.5 py-1 text-xs font-medium font-mono transition-colors cursor-pointer rounded ${
                    activeScenario === sc.id
                      ? 'bg-[#18C7D8]/20 text-[#18C7D8] border border-[#18C7D8]/40'
                      : 'bg-[#15181D] hover:bg-[#1B1F25] text-[#A7ADB7] hover:text-white border border-white/[0.08]'
                  }`}
                >
                  {sc.label}
                </button>
              ))}

              {onPushToBackend && backendOnline && (
                <button
                  type="button"
                  onClick={onPushToBackend}
                  disabled={isPushing}
                  className="ml-1 px-3 py-1 text-xs font-semibold font-mono bg-[#18C7D8]/15 hover:bg-[#18C7D8]/25 text-[#18C7D8] border border-[#18C7D8]/35 rounded transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
                  title="Inject current scenario telemetry into SQLite backend database"
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>{isPushing ? 'SAVING...' : 'SYNC TO DB'}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
