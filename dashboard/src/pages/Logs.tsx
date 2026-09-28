import React, { useState, useMemo } from 'react';
import { MissionEvent, EventType, SeverityLevel } from '../types/rover';
import { Search, Filter, ArrowUpDown, X } from 'lucide-react';

interface LogsPageProps {
  events: MissionEvent[];
}

export const LogsPage: React.FC<LogsPageProps> = ({ events }) => {
  const [activeFilter, setActiveFilter] = useState<EventType>('All');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const filterOptions: EventType[] = ['All', 'Vision', 'Sensor', 'Decision', 'Mission', 'System'];

  const filteredEvents = useMemo(() => {
    return events
      .filter((ev) => {
        const matchesType = activeFilter === 'All' || ev.type === activeFilter;
        const matchesSearch =
          searchTerm === '' ||
          ev.event.toLowerCase().includes(searchTerm.toLowerCase()) ||
          ev.time.includes(searchTerm);
        return matchesType && matchesSearch;
      })
      .sort((a, b) => {
        return sortAsc
          ? a.time.localeCompare(b.time)
          : b.time.localeCompare(a.time);
      });
  }, [events, activeFilter, searchTerm, sortAsc]);

  const getSeverityBadge = (sev: SeverityLevel) => {
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#EF5350]/15 text-[#EF5350] border border-[#EF5350]/30">
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#EF5350]/15 text-[#EF5350] border border-[#EF5350]/30">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#E8B84A]/15 text-[#E8B84A] border border-[#E8B84A]/30">
            MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-white/[0.08] text-[#A7ADB7] border border-white/[0.1]">
            LOW
          </span>
        );
      case 'NORMAL':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-[#24C88A]/10 text-[#24C88A] border border-[#24C88A]/25">
            NORMAL
          </span>
        );
    }
  };

  const getTypeBadge = (type: string) => {
    const getColor = () => {
      switch (type) {
        case 'Vision': return 'text-[#18C7D8] bg-[#18C7D8]/10 border-[#18C7D8]/30';
        case 'Decision': return 'text-[#E8B84A] bg-[#E8B84A]/10 border-[#E8B84A]/30';
        case 'Sensor': return 'text-[#F4F6F8] bg-white/[0.08] border-white/[0.12]';
        default: return 'text-[#A7ADB7] bg-[#15181D] border-white/[0.08]';
      }
    };

    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium border uppercase ${getColor()}`}>
        {type}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Title & Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
        <div>
          <span className="text-[11px] font-semibold text-[#A7ADB7] tracking-wider uppercase block">
            CHRONOLOGICAL STREAM
          </span>
          <h2 className="text-xl sm:text-2xl font-bold text-[#F4F6F8] tracking-tight">
            Mission Telemetry & Event Audit Logs
          </h2>
        </div>

        {/* Search Field */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#707783]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setSearchTerm('');
            }}
            placeholder="Search events, timestamps..."
            className="w-full pl-9 pr-8 py-2 text-xs bg-[#101216] border border-white/[0.08] rounded-md text-[#F4F6F8] placeholder-[#707783] focus:outline-hidden focus:border-[#18C7D8] font-mono"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#A7ADB7] hover:text-[#F4F6F8] p-0.5"
              aria-label="Clear search"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-semibold text-[#A7ADB7] mr-1 flex items-center gap-1">
            <Filter className="w-3 h-3 text-[#707783]" /> FILTER:
          </span>
          {filterOptions.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setActiveFilter(f)}
              className={`px-3 py-1.5 rounded-md text-xs font-mono transition-colors cursor-pointer ${
                activeFilter === f
                  ? 'bg-[#18C7D8]/20 text-[#18C7D8] border border-[#18C7D8]/40 font-semibold'
                  : 'bg-[#101216] text-[#A7ADB7] hover:text-[#F4F6F8] border border-white/[0.08]'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setSortAsc(!sortAsc)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#101216] text-[#A7ADB7] hover:text-[#F4F6F8] border border-white/[0.08] text-xs font-mono transition-colors cursor-pointer"
        >
          <ArrowUpDown className="w-3 h-3 text-[#707783]" />
          <span>Sort: {sortAsc ? 'Oldest First' : 'Newest First'}</span>
        </button>
      </div>

      {/* Logs Table */}
      <div className="nv-card overflow-hidden rounded-xl border border-white/[0.08] bg-[#101216]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#15181D] border-b border-white/[0.06] text-[#A7ADB7] uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4 w-32">Timestamp</th>
                <th className="py-3 px-4 w-32">Subsystem</th>
                <th className="py-3 px-4">Event Description</th>
                <th className="py-3 px-4 w-32 text-right">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05]">
              {filteredEvents.length > 0 ? (
                filteredEvents.map((ev) => (
                  <tr key={ev.id} className="hover:bg-[#15181D] transition-colors">
                    <td className="py-3 px-4 font-semibold text-[#A7ADB7] tnum">
                      {ev.time}
                    </td>
                    <td className="py-3 px-4">
                      {getTypeBadge(ev.type)}
                    </td>
                    <td className="py-3 px-4 text-[#F4F6F8] font-sans text-xs">
                      {ev.event}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {getSeverityBadge(ev.severity)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-[#A7ADB7] font-mono">
                    <p className="text-sm font-semibold text-[#F4F6F8] mb-1">No matching log entries found</p>
                    <p className="text-xs text-[#707783] mb-3">No events match the search query "{searchTerm}".</p>
                    <button
                      type="button"
                      onClick={() => {
                        setSearchTerm('');
                        setActiveFilter('All');
                      }}
                      className="nv-btn-outline"
                    >
                      Reset All Filters
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="py-3 px-4 bg-[#15181D] border-t border-white/[0.06] text-[11px] font-mono text-[#707783] flex items-center justify-between">
          <span>Displaying {filteredEvents.length} of {events.length} logged events</span>
          <span>FastAPI Route: GET /api/logs</span>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
