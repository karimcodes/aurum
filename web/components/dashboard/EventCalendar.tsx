"use client";

import { useQuery } from "@tanstack/react-query";
import { api, EventCalendarResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Calendar,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Clock,
  Landmark,
  Globe,
  BarChart3,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";

const categoryIcons: Record<string, React.ReactNode> = {
  central_bank: <Landmark size={14} className="text-blue-500" />,
  geopolitical: <Globe size={14} className="text-red-500" />,
  economic: <BarChart3 size={14} className="text-green-500" />,
  market: <TrendingUp size={14} className="text-purple-500" />,
};

const impactColors: Record<string, string> = {
  HIGH: "bg-red-100 text-red-800 border-red-200",
  MEDIUM: "bg-yellow-100 text-yellow-800 border-yellow-200",
  LOW: "bg-gray-100 text-gray-600 border-gray-200",
};

export function EventCalendar() {
  const [expanded, setExpanded] = useState(false);

  const { data: events, isLoading, error } = useQuery({
    queryKey: ["event-calendar"],
    queryFn: api.getEventCalendar,
    refetchInterval: 60 * 60 * 1000, // Refresh every hour
    staleTime: 30 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center gap-2 text-gray-500">
          <Calendar size={18} />
          <span>Loading event calendar...</span>
        </div>
      </div>
    );
  }

  if (error || !events) {
    return (
      <div className="bg-yellow-50 rounded-xl border border-yellow-200 p-4">
        <div className="flex items-center gap-2 text-yellow-700">
          <AlertTriangle size={18} />
          <span>Event calendar unavailable</span>
        </div>
      </div>
    );
  }

  const scoreBg =
    events.event_calendar_score > 7
      ? "bg-red-100 text-red-800"
      : events.event_calendar_score > 4
      ? "bg-yellow-100 text-yellow-800"
      : "bg-gray-100 text-gray-800";

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="text-blue-600" size={20} />
            <span className="font-semibold text-gray-900">Event Calendar</span>
            <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", scoreBg)}>
              {events.event_calendar_score.toFixed(1)} / 10
            </span>
          </div>
          <div className="flex items-center gap-3">
            {events.weekend_events.length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                {events.weekend_events.length} WEEKEND EVENT{events.weekend_events.length > 1 ? "S" : ""}
              </span>
            )}
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </div>

        {/* Summary Row */}
        <div className="mt-3 grid grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Upcoming</span>
            <div className="font-medium">{events.upcoming_events.length} events</div>
          </div>
          <div>
            <span className="text-gray-500">This Weekend</span>
            <div className={cn("font-medium", events.weekend_events.length > 0 ? "text-red-600" : "")}>
              {events.weekend_events.length} events
            </div>
          </div>
          <div>
            <span className="text-gray-500">Friday</span>
            <div className={cn("font-medium", events.friday_events.length > 0 ? "text-orange-600" : "")}>
              {events.friday_events.length} events
            </div>
          </div>
          <div>
            <span className="text-gray-500">Next Major</span>
            <div className="font-medium truncate">
              {events.next_high_impact ? (
                <span title={events.next_high_impact.name}>
                  {events.next_high_impact.days_until}d - {events.next_high_impact.name.split(" ")[0]}
                </span>
              ) : (
                "None"
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-4">
          {/* Interpretation */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-700">{events.interpretation}</p>
          </div>

          {/* Weekend Events Alert */}
          {events.weekend_events.length > 0 && (
            <div className="bg-red-50 rounded-lg p-3 border border-red-200">
              <h4 className="font-medium text-red-800 flex items-center gap-2">
                <AlertTriangle size={16} />
                Weekend Events
              </h4>
              <div className="mt-2 space-y-1">
                {events.weekend_events.map((e, i) => (
                  <div key={i} className="text-sm text-red-700 flex items-center gap-2">
                    <span className={cn("px-1.5 py-0.5 rounded text-xs", impactColors[e.impact])}>
                      {e.impact}
                    </span>
                    <span>{e.name}</span>
                    <span className="text-red-500">({e.date})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Friday Events */}
          {events.friday_events.length > 0 && (
            <div className="bg-orange-50 rounded-lg p-3 border border-orange-200">
              <h4 className="font-medium text-orange-800 flex items-center gap-2">
                <Clock size={16} />
                Friday Events (Affects Positioning)
              </h4>
              <div className="mt-2 space-y-1">
                {events.friday_events.map((e, i) => (
                  <div key={i} className="text-sm text-orange-700 flex items-center gap-2">
                    <span className={cn("px-1.5 py-0.5 rounded text-xs", impactColors[e.impact])}>
                      {e.impact}
                    </span>
                    <span>{e.name}</span>
                    <span className="text-orange-500">({e.date})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upcoming Events List */}
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Upcoming Events (Next 7 Days)</h4>
            <div className="space-y-2">
              {events.upcoming_events.slice(0, 8).map((event, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 text-sm border-l-2 border-gray-300 pl-3 py-1"
                >
                  <span className={cn("px-1.5 py-0.5 rounded text-xs border", impactColors[event.impact])}>
                    {event.impact}
                  </span>
                  {categoryIcons[event.category] || <Calendar size={14} />}
                  <div className="flex-1">
                    <span className="font-medium">{event.name}</span>
                    <span className="text-gray-500 ml-2">
                      {event.date} {event.time && `@ ${event.time}`}
                    </span>
                  </div>
                  <span className="text-gray-400 text-xs">
                    {event.days_until === 0 ? "Today" : event.days_until === 1 ? "Tomorrow" : `${event.days_until}d`}
                  </span>
                </div>
              ))}
              {events.upcoming_events.length === 0 && (
                <p className="text-gray-500 text-sm">No significant events in the next 7 days.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
