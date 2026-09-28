import React, { useState, useEffect, useCallback } from 'react';
import {
  ConnectionStatus,
  SensorItem,
  VisionDetection,
  DecisionData,
  MissionInfo,
  MissionEvent,
  RoverSystemInfo,
  TelemetryPoint,
  SyncStatusInfo,
} from './types/rover';
import { roverApi } from './api/roverApi';
import { MockScenario } from './data/mockData';
import { Header } from './components/Header';
import { DashboardPage } from './pages/Dashboard';
import { MissionsPage } from './pages/Missions';
import { LogsPage } from './pages/Logs';
import { SystemPage } from './pages/System';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'dashboard' | 'missions' | 'logs' | 'system'>('dashboard');
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('ONLINE');
  const [activeScenario, setActiveScenario] = useState<MockScenario>('fire');
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [isLiveMode, setIsLiveMode] = useState<boolean>(true);
  const [isPushing, setIsPushing] = useState<boolean>(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatusInfo | null>(null);

  // Real-time state slices
  const [sensors, setSensors] = useState<SensorItem[]>([]);
  const [detections, setDetections] = useState<VisionDetection[]>([]);
  const [decision, setDecision] = useState<DecisionData>({
    hazard: 'INITIALIZING',
    severity: 'NORMAL',
    confidence: 1.0,
    reason: 'Awaiting sensor arbitration pipeline',
  });
  const [currentMission, setCurrentMission] = useState<MissionInfo>({
    id: 'Mission #001',
    title: 'Loading...',
    status: 'ACTIVE',
    durationMinutes: 0,
    hazardsEncountered: 0,
    startTime: '14:10:00',
    sector: 'Sector 4B',
    description: '',
  });
  const [missionsList, setMissionsList] = useState<MissionInfo[]>([]);
  const [events, setEvents] = useState<MissionEvent[]>([]);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [systemInfo, setSystemInfo] = useState<RoverSystemInfo>({
    rover: 'Running',
    backend: 'Connected',
    database: 'Connected',
    network: 'Online',
    batteryPct: 86,
    internalTempC: 38.2,
    firmwareVersion: 'v2.4.1',
    activeSector: 'Sector 4B',
  });

  // Load data according to active mode and scenario
  const loadConsoleData = useCallback(async (live: boolean, sc: MockScenario) => {
    roverApi.setForceSimulation(!live);
    roverApi.setScenario(sc);

    const [s, v, d, m, ml, ev, th, sys, sync] = await Promise.all([
      roverApi.getLatestSensors(),
      roverApi.getLatestVision(),
      roverApi.getLatestDecision(),
      roverApi.getCurrentMission(),
      roverApi.getMissionHistory(),
      roverApi.getMissionLogs('All'),
      roverApi.getTelemetryHistory(),
      roverApi.getSystemStatus(),
      roverApi.getSyncStatus(),
    ]);

    setSensors(s);
    setDetections(v);
    setDecision(d);
    setCurrentMission(m);
    setMissionsList(ml);
    setEvents(ev);
    setTelemetryHistory(th);
    setSystemInfo(sys);
    setSyncStatus(sync);
    setBackendOnline(roverApi.isBackendOnline());
  }, []);

  // Periodic polling for real-time telemetry updates
  useEffect(() => {
    let isMounted = true;

    const poll = async () => {
      if (connectionStatus === 'DISCONNECTED') return;
      try {
        const isHealthy = await roverApi.checkBackendHealth();
        if (isMounted) {
          setBackendOnline(isHealthy);
        }
        await loadConsoleData(isLiveMode, activeScenario);
      } catch (e) {
        console.warn('Backend polling error:', e);
      }
    };

    poll();
    const interval = setInterval(poll, 1500);

    return () => {

      isMounted = false;
      clearInterval(interval);
    };
  }, [connectionStatus, isLiveMode, activeScenario, loadConsoleData]);

  const handleScenarioChange = (newSc: MockScenario) => {
    setActiveScenario(newSc);
    // When clicking a scenario, default to that scenario's telemetry
    setIsLiveMode(false);
    loadConsoleData(false, newSc);
  };

  const handleToggleLiveMode = () => {
    const nextMode = !isLiveMode;
    setIsLiveMode(nextMode);
    loadConsoleData(nextMode, activeScenario);
  };

  const handlePushToBackend = async () => {
    setIsPushing(true);
    try {
      const ok = await roverApi.injectScenarioToBackend(activeScenario);
      if (ok) {
        setBackendOnline(true);
        // Switch to live mode to observe the newly injected data from the backend
        setIsLiveMode(true);
        await loadConsoleData(true, activeScenario);
      }
    } finally {
      setIsPushing(false);
    }
  };

  const handleTriggerSync = async () => {
    try {
      await roverApi.triggerSync();
      const updatedSync = await roverApi.getSyncStatus();
      setSyncStatus(updatedSync);
    } catch (e) {
      console.warn('Sync trigger error:', e);
    }
  };

  return (
    <div
      className="min-h-screen bg-[#0a0c10] text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-black"
    >
      {/* Precision Industrial Mission Header */}
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        connectionStatus={connectionStatus}
        onConnectionChange={setConnectionStatus}
        missionId={currentMission.id}
        activeScenario={activeScenario}
        onScenarioChange={handleScenarioChange}
        backendOnline={backendOnline}
        isLiveMode={isLiveMode}
        onToggleLiveMode={handleToggleLiveMode}
        onPushToBackend={handlePushToBackend}
        isPushing={isPushing}
        syncStatus={syncStatus}
        onTriggerSync={handleTriggerSync}
      />

      {/* Main Viewport Container */}
      <main className="flex-1 max-w-[1536px] w-full min-w-0 mx-auto px-4 sm:px-6 lg:px-8 py-6 box-border">
        {currentTab === 'dashboard' && (
          <DashboardPage
            sensors={sensors}
            detections={detections}
            decision={decision}
            currentMission={currentMission}
            events={events}
            telemetryHistory={telemetryHistory}
            connectionStatus={connectionStatus}
            system={systemInfo}
            syncStatus={syncStatus}
            onReconnect={() => setConnectionStatus('ONLINE')}
          />
        )}

        {currentTab === 'missions' && (
          <MissionsPage missions={missionsList} />
        )}

        {currentTab === 'logs' && (
          <LogsPage events={events} />
        )}

        {currentTab === 'system' && (
          <SystemPage
            system={systemInfo}
            connectionStatus={connectionStatus}
            syncStatus={syncStatus}
            onTriggerSync={handleTriggerSync}
          />
        )}
      </main>

      {/* Industrial Mission Control Footer */}
      <footer className="border-t border-white/[0.06] bg-[#08090B] py-4 text-xs font-mono text-[#707783]">
        <div className="max-w-[1536px] w-full min-w-0 mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 box-border">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-white font-semibold">MINING ROVER MISSION CONTROL CONSOLE</span>
            <span className="text-slate-600">•</span>
            <span>FIRMWARE {systemInfo.firmwareVersion}</span>
            <span className="text-slate-600">•</span>
            <span className="text-emerald-400 font-semibold">LOCAL-FIRST TELEMETRY</span>
          </div>

          <div className="text-slate-400 font-medium">
            FastAPI Local Architecture • SQLite Store • CAN 2.0B
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
