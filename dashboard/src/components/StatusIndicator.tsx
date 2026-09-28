import React from 'react';
import { ConnectionStatus } from '../types/rover';
import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';

interface StatusIndicatorProps {
  status: ConnectionStatus;
  interactive?: boolean;
  onStatusChange?: (newStatus: ConnectionStatus) => void;
  size?: 'sm' | 'md';
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  interactive = false,
  onStatusChange,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case 'ONLINE':
        return (
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-[2px] bg-[#76b900]/10 border border-[#76b900]/40 text-[#76b900]">
            <span className="w-2 h-2 rounded-[1px] bg-[#76b900]" />
            <Wifi className="w-3.5 h-3.5" />
            <span className="font-mono text-xs font-bold tracking-wider">ONLINE</span>
          </div>
        );
      case 'OFFLINE':
        return (
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-[2px] bg-[#df6500]/15 border border-[#df6500]/40 text-[#df6500]">
            <span className="w-2 h-2 rounded-[1px] bg-[#df6500]" />
            <WifiOff className="w-3.5 h-3.5" />
            <span className="font-mono text-xs font-bold tracking-wider">OFFLINE</span>
          </div>
        );
      case 'DISCONNECTED':
      default:
        return (
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-[2px] bg-[#e52020]/15 border border-[#e52020]/40 text-[#e52020]">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="font-mono text-xs font-bold tracking-wider">BACKEND DISCONNECTED</span>
          </div>
        );
    }
  };

  if (!interactive || !onStatusChange) {
    return getStatusBadge();
  }

  return (
    <div className="flex items-center gap-2">
      {getStatusBadge()}

      {/* NVIDIA Style 2px Radius Segmented Strip */}
      <div className="inline-flex items-center bg-[#141414] border border-[#2c2c2c] rounded-[2px] p-0.5 text-[11px] font-mono">
        <button
          type="button"
          onClick={() => onStatusChange('ONLINE')}
          title="Simulate Online state"
          className={`px-2.5 py-1 rounded-[1px] font-bold transition-colors cursor-pointer ${
            status === 'ONLINE'
              ? 'bg-[#76b900] text-[#000000]'
              : 'text-[#898989] hover:text-[#ffffff]'
          }`}
        >
          ONLINE
        </button>
        <button
          type="button"
          onClick={() => onStatusChange('OFFLINE')}
          title="Simulate Offline state"
          className={`px-2.5 py-1 rounded-[1px] font-bold transition-colors cursor-pointer ${
            status === 'OFFLINE'
              ? 'bg-[#df6500] text-[#000000]'
              : 'text-[#898989] hover:text-[#ffffff]'
          }`}
        >
          OFFLINE
        </button>
        <button
          type="button"
          onClick={() => onStatusChange('DISCONNECTED')}
          title="Simulate Backend Disconnected state"
          className={`px-2.5 py-1 rounded-[1px] font-bold transition-colors cursor-pointer ${
            status === 'DISCONNECTED'
              ? 'bg-[#e52020] text-[#ffffff]'
              : 'text-[#898989] hover:text-[#ffffff]'
          }`}
        >
          DISCONNECT
        </button>
      </div>
    </div>
  );
};

export default StatusIndicator;
