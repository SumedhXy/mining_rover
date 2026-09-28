import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { TelemetryPoint } from '../types/rover';
import { TrendingUp } from 'lucide-react';

interface LiveTelemetryChartProps {
  data: TelemetryPoint[];
}

export const LiveTelemetryChart: React.FC<LiveTelemetryChartProps> = ({ data }) => {
  const [timeframe, setTimeframe] = useState<'15m' | '1h' | '6h'>('15m');

  const maxTemp = Math.max(...data.map((d) => d.temperature));
  const maxGas = Math.max(...data.map((d) => d.gasLevel));
  const latestPoint = data[data.length - 1];

  return (
    <div className="nv-card p-5 rounded-xl border border-white/[0.08] bg-[#101216] flex flex-col justify-between">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3.5 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-[#15181D] border border-white/[0.08] flex items-center justify-center text-[#18C7D8]">
            <TrendingUp className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold text-[#A7ADB7] tracking-wider uppercase">
                TELEMETRY DYNAMICS
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#18C7D8] animate-pulse" />
              <span className="text-[10px] font-mono text-[#18C7D8] font-medium">100 Hz FIFO SYNC</span>
            </div>
            <span className="text-xs font-semibold text-[#F4F6F8] tracking-tight">
              Dual-Channel Thermal Gradient & Combustible Gas Index Fluctuations
            </span>
          </div>
        </div>

        {/* Legend & Stats Pills */}
        <div className="flex items-center gap-2.5 text-xs font-mono flex-wrap">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#15181D] border border-white/[0.08]">
            <span className="w-2 h-2 rounded-full bg-[#18C7D8]" />
            <span className="text-[#A7ADB7] text-[11px]">Peak Temp:</span>
            <span className="text-[#F4F6F8] font-bold tnum">{maxTemp}°C</span>
          </div>

          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#15181D] border border-white/[0.08]">
            <span className="w-2 h-2 rounded-full bg-[#E8B84A]" />
            <span className="text-[#A7ADB7] text-[11px]">Peak Gas:</span>
            <span className="text-[#F4F6F8] font-bold tnum">{maxGas}</span>
          </div>

          {/* Timeframe pill selector */}
          <div className="flex items-center bg-[#15181D] p-0.5 rounded border border-white/[0.08]">
            {(['15m', '1h', '6h'] as const).map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-medium transition-colors cursor-pointer ${
                  timeframe === tf
                    ? 'bg-[#1B1F25] text-[#F4F6F8] border border-white/[0.1]'
                    : 'text-[#707783] hover:text-[#F4F6F8]'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Oscilloscope Area Chart */}
      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="hashiTempGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#18C7D8" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#18C7D8" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="hashiGasGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#E8B84A" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#E8B84A" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#707783"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            />
            <YAxis
              stroke="#707783"
              fontSize={10}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-[#101216] border border-white/[0.12] p-3 rounded-lg text-xs font-mono shadow-xl">
                      <div className="flex items-center justify-between gap-4 mb-2 pb-1.5 border-b border-white/[0.08]">
                        <span className="text-[#A7ADB7] font-semibold">{label}</span>
                        <span className="text-[10px] text-[#18C7D8] font-semibold">CAN SYNC</span>
                      </div>
                      <div className="flex items-center justify-between gap-5 text-[#18C7D8]">
                        <span className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#18C7D8]" />
                          Temperature:
                        </span>
                        <span className="font-bold tnum text-[#F4F6F8]">{payload[0]?.value} °C</span>
                      </div>
                      <div className="flex items-center justify-between gap-5 text-[#E8B84A] mt-1.5">
                        <span className="flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#E8B84A]" />
                          Gas Index:
                        </span>
                        <span className="font-bold tnum text-[#F4F6F8]">{payload[1]?.value}</span>
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="temperature"
              stroke="#18C7D8"
              strokeWidth={1.5}
              fillOpacity={1}
              fill="url(#hashiTempGrad)"
            />
            <Area
              type="monotone"
              dataKey="gasLevel"
              stroke="#E8B84A"
              strokeWidth={1.5}
              fillOpacity={1}
              fill="url(#hashiGasGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Chart Footer Readout */}
      <div className="mt-2 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-[#707783]">
        <div className="flex items-center gap-3">
          <span>SAMPLING: 100 Hz RING BUFFER</span>
          <span className="text-white/[0.1]">•</span>
          <span className="text-[#A7ADB7]">LATEST TEMP: {latestPoint?.temperature ?? 34.5}°C</span>
          <span className="text-white/[0.1]">•</span>
          <span className="text-[#E8B84A]">LATEST GAS: {latestPoint?.gasLevel ?? 0.72}</span>
        </div>
        <span className="text-[#18C7D8] font-medium">FastAPI Telemetry Stream Active</span>
      </div>
    </div>
  );
};

export default LiveTelemetryChart;
