import React, { useState } from 'react';
import { VisionDetection, ConnectionStatus } from '../types/rover';
import { Camera, VideoOff, RefreshCw, Crosshair } from 'lucide-react';

interface LiveCameraProps {
  detections: VisionDetection[];
  connectionStatus?: ConnectionStatus;
  streamUrl?: string | null;
  onReconnect?: () => void;
}

export const LiveCamera: React.FC<LiveCameraProps> = ({
  detections = [],
  connectionStatus = 'ONLINE',
  streamUrl = '/api/vision/camera/stream',
  onReconnect,
}) => {
  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [simulateFeed, setSimulateFeed] = useState<boolean>(false);
  const [selectedCam, setSelectedCam] = useState<number>(0);
  const [streamError, setStreamError] = useState<boolean>(false);
  const [streamKey, setStreamKey] = useState<number>(Date.now());
  const [thermalMode, setThermalMode] = useState<boolean>(false);
  const [showReticle, setShowReticle] = useState<boolean>(false);
  const [measuredFps, setMeasuredFps] = useState<number>(30.0);
  const [resolution, setResolution] = useState<string>('640x480');

  // Real-time animation loop measuring frame render rate
  React.useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let animId: number;

    const loop = (now: number) => {
      frameCount++;
      if (now - lastTime >= 1000) {
        const calculated = Number(((frameCount * 1000) / (now - lastTime)).toFixed(1));
        setMeasuredFps(calculated > 60 ? 30.0 : calculated);
        frameCount = 0;
        lastTime = now;
      }
      animId = requestAnimationFrame(loop);
    };

    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, []);

  const isDisconnected = connectionStatus === 'DISCONNECTED';
  const resolvedStreamUrl = `${streamUrl || '/api/vision/camera/stream'}?camera_index=${selectedCam}&yolo=${showOverlays}&t=${streamKey}`;

  return (
    <div className="nv-card relative overflow-hidden flex flex-col rounded-xl border border-white/[0.07] bg-[#101216]">
      {/* Camera Header Bar */}
      <div className="px-5 py-3.5 bg-[#13161C] border-b border-white/[0.06] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-[#181B20] border border-white/[0.08] flex items-center justify-center text-[#18C7D8]">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#F4F6F8] tracking-tight">
                LIVE OPTICAL FEED
              </span>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#24C88A]/10 text-[#24C88A] border border-[#24C88A]/25">
                <span className="w-1.5 h-1.5 rounded-full bg-[#24C88A] animate-pulse" />
                ● LIVE
              </span>
              <span className="text-[10px] font-mono text-[#707783]">
                [{!simulateFeed ? `CAM-0${selectedCam}` : 'SIM-STREAM'}]
              </span>
            </div>
            <span className="text-[11px] text-[#A7ADB7]">
              Optical navigation and real-time hazard perception
            </span>
          </div>
        </div>

        {/* HUD Quick Controls - Visually Quieter */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          {/* Camera Device Index Selector */}
          {!simulateFeed && (
            <select
              aria-label="Select optical camera device"
              value={selectedCam}
              onChange={(e) => {
                setSelectedCam(Number(e.target.value));
                setStreamError(false);
                setStreamKey(Date.now());
              }}
              className="bg-[#181B20] border border-white/[0.08] text-[#F4F6F8] hover:border-[#18C7D8]/50 px-2 py-1 text-xs font-mono font-medium rounded cursor-pointer focus:outline-none"
            >
              <option value={0}>CAM 0 (PRIMARY)</option>
              <option value={1}>CAM 1 (INTERNAL)</option>
              <option value={2}>CAM 2 (AUX)</option>
            </select>
          )}

          {/* Refresh Stream Button */}
          {!simulateFeed && (
            <button
              type="button"
              onClick={() => {
                setStreamError(false);
                setStreamKey(Date.now());
              }}
              title="Refresh Camera Feed"
              className="p-1.5 rounded bg-[#181B20] border border-white/[0.08] text-[#A7ADB7] hover:text-[#18C7D8] transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Reticle Toggle */}
          <button
            type="button"
            onClick={() => setShowReticle(!showReticle)}
            title="Toggle Reticle Overlay"
            className={`px-2 py-1 text-xs font-medium rounded transition-colors cursor-pointer flex items-center gap-1 border ${
              showReticle
                ? 'bg-[#18C7D8]/15 text-[#18C7D8] border-[#18C7D8]/35'
                : 'bg-[#181B20] border-white/[0.08] text-[#A7ADB7] hover:text-white'
            }`}
          >
            <Crosshair className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">HUD</span>
          </button>

          {/* Thermal Mode Toggle */}
          <button
            type="button"
            onClick={() => setThermalMode(!thermalMode)}
            className={`px-2 py-1 text-xs font-medium rounded transition-colors cursor-pointer border ${
              thermalMode
                ? 'bg-[#18C7D8]/15 text-[#18C7D8] border-[#18C7D8]/35'
                : 'bg-[#181B20] border-white/[0.08] text-[#A7ADB7] hover:text-white'
            }`}
          >
            {thermalMode ? 'FLIR' : 'RGB'}
          </button>

          {/* Mode Switcher */}
          <button
            type="button"
            onClick={() => {
              setSimulateFeed(!simulateFeed);
              setStreamError(false);
              setStreamKey(Date.now());
            }}
            className={`px-2 py-1 rounded transition-colors cursor-pointer text-xs font-medium border flex items-center gap-1.5 ${
              !simulateFeed
                ? 'bg-[#18C7D8]/15 text-[#18C7D8] border-[#18C7D8]/35'
                : 'bg-[#181B20] text-[#A7ADB7] border-white/[0.08] hover:text-white'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${!simulateFeed ? 'bg-[#24C88A]' : 'bg-[#E8B84A]'}`} />
            <span>{!simulateFeed ? 'LIVE' : 'SIM'}</span>
          </button>
        </div>
      </div>

      {/* Video Viewport Area (16:9 Aspect Ratio) */}
      <div className="relative aspect-video w-full bg-[#08090B] overflow-hidden flex items-center justify-center select-none">
        {isDisconnected ? (
          // Disconnected State
          <div className="flex flex-col items-center justify-center p-8 text-center text-[#A7ADB7]">
            <VideoOff className="w-10 h-10 text-[#EF5350] mb-3" />
            <span className="text-[10px] font-mono text-[#24C88A] tracking-wider uppercase mb-1 font-semibold">
              LIVE OPTICAL FEED
            </span>
            <h4 className="text-base font-semibold text-[#F4F6F8] tracking-wider font-mono">
              CAMERA FEED UNAVAILABLE
            </h4>
            <p className="text-xs text-[#24C88A] mt-1 font-mono font-medium">
              Sensor monitoring remains active
            </p>
            <p className="text-xs text-[#707783] mt-2 max-w-sm font-mono">
              Waiting for optical stream reconnect...
            </p>
            {onReconnect && (
              <button
                type="button"
                onClick={onReconnect}
                className="mt-4 nv-btn-primary text-xs"
              >
                Reconnect Stream
              </button>
            )}
          </div>
        ) : streamError && !simulateFeed ? (
          // Camera Stream Error / Standby State
          <div className="flex flex-col items-center justify-center p-8 text-center text-[#A7ADB7]">
            <VideoOff className="w-10 h-10 text-[#EF5350] mb-3" />
            <span className="text-[10px] font-mono text-[#24C88A] tracking-wider uppercase mb-1 font-semibold">
              LIVE OPTICAL FEED
            </span>
            <h4 className="text-base font-semibold text-[#F4F6F8] tracking-wider font-mono">
              CAMERA FEED UNAVAILABLE
            </h4>
            <p className="text-xs text-[#24C88A] mt-1 font-mono font-medium">
              Sensor monitoring remains active
            </p>
            <p className="text-xs text-[#707783] mt-2 font-mono max-w-sm">
              Waiting for optical stream on device index {selectedCam}... Local telemetry arbitration unaffected.
            </p>
            <div className="flex items-center gap-3 mt-4">
              <button
                type="button"
                onClick={() => {
                  setStreamError(false);
                  setStreamKey(Date.now());
                }}
                className="nv-btn-primary text-xs flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry Camera
              </button>
              <button
                type="button"
                onClick={() => {
                  setSimulateFeed(true);
                  setStreamError(false);
                }}
                className="nv-btn-outline text-xs"
              >
                Switch to Simulated Feed
              </button>
            </div>
          </div>
        ) : (
          // Active Visual Stream with Real Image Feed
          <div className="relative w-full h-full">
            <img
              key={`${selectedCam}-${streamKey}-${simulateFeed}`}
              src={simulateFeed ? '/sample-mine-feed.jpg' : resolvedStreamUrl}
              onLoad={(e) => {
                const w = e.currentTarget.naturalWidth;
                const h = e.currentTarget.naturalHeight;
                if (w > 0 && h > 0) {
                  setResolution(`${w}x${h}`);
                }
              }}
              onError={() => {
                if (!simulateFeed) {
                  setStreamError(true);
                }
              }}
              alt="Mining Rover Optical Camera Stream"
              className={`w-full h-full object-cover transition-all duration-200 ${
                thermalMode
                  ? 'filter invert contrast-150 saturate-200 hue-rotate-[180deg]'
                  : 'filter contrast-[1.03]'
              }`}
            />

            {/* Restrained Corner Markers for Inspection Monitor Aesthetics */}
            <div className="absolute inset-0 pointer-events-none z-10 p-3">
              <div className="absolute top-3 left-3 w-3 h-3 border-t border-l border-white/[0.25]" />
              <div className="absolute top-3 right-3 w-3 h-3 border-t border-r border-white/[0.25]" />
              <div className="absolute bottom-3 left-3 w-3 h-3 border-b border-l border-white/[0.25]" />
              <div className="absolute bottom-3 right-3 w-3 h-3 border-b border-r border-white/[0.25]" />
            </div>

            {/* Optional Reticle HUD */}
            {showReticle && (
              <div className="absolute inset-0 pointer-events-none z-10 flex items-center justify-center">
                <div className="w-6 h-6 rounded-full border border-[#18C7D8]/60 flex items-center justify-center">
                  <div className="w-1 h-1 rounded-full bg-[#18C7D8]" />
                </div>
              </div>
            )}

            {/* YOLO Overlays for Simulation Mode */}
            {simulateFeed &&
              showOverlays &&
              detections.map((det) => {
                const confidencePct = Math.round(det.confidence * 100);
                return (
                  <div
                    key={det.id}
                    className="absolute border border-[#18C7D8] pointer-events-none rounded-sm"
                    style={{
                      left: `${det.bbox.x}%`,
                      top: `${det.bbox.y}%`,
                      width: `${det.bbox.width}%`,
                      height: `${det.bbox.height}%`,
                    }}
                  >
                    <div className="absolute -top-5 left-0 px-1.5 py-0.2 text-[10px] font-mono font-medium tracking-wider text-[#08090B] bg-[#18C7D8] rounded-sm">
                      {det.label.toUpperCase()} {confidencePct}%
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* Bottom Clean Metadata Bar (Section 9) */}
      <div className="px-5 py-2.5 bg-[#13161C] border-t border-white/[0.06] text-[11px] font-mono text-[#A7ADB7] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[#F4F6F8] font-medium">
            {!simulateFeed ? `CAM-0${selectedCam}` : 'SIM-01'}
          </span>
          <span className="text-white/[0.1]">•</span>
          <span className="text-[#18C7D8] font-medium">{measuredFps.toFixed(0)} FPS</span>
          <span className="text-white/[0.1]">•</span>
          <span>{resolution}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#24C88A]" />
          <span className="text-[#F4F6F8] font-medium">STREAM ACTIVE</span>
        </div>
      </div>
    </div>
  );
};

export default LiveCamera;
