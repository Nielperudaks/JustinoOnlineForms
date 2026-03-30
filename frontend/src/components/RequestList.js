import React from "react";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, FileText, Clock, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { differenceInHours, formatDistanceToNow } from "date-fns";

const STATUS_CONFIG = {
  in_progress: { label: "In Progress", icon: Clock, cls: "bg-blue-50 text-blue-700 border-blue-200" },
  approved: { label: "Approved", icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  rejected: { label: "Rejected", icon: XCircle, cls: "bg-red-50 text-red-700 border-red-200" },
  cancelled: { label: "Cancelled", icon: XCircle, cls: "bg-slate-100 text-slate-500 border-slate-300" },
};

function getRequestAgeIndicator(request) {
  if (request.status !== "in_progress" || !request.created_at) {
    return null;
  }

  const ageInHours = differenceInHours(new Date(), new Date(request.created_at));

  if (ageInHours > 24 * 5) {
    return {
      label: "5 days+",
      iconClassName: "text-red-500",
      badgeClassName: "bg-red-50 text-red-700 border-red-200",
    };
  }

  if (ageInHours > 24 * 3) {
    return {
      label: "3 days+",
      iconClassName: "text-amber-500",
      badgeClassName: "bg-amber-50 text-amber-700 border-amber-200",
    };
  }

  return null;
}

export default function RequestList({
  requests, selectedRequest, onSelect, searchQuery, onSearchChange, loading
}) {
  const showInitialLoading = loading && requests.length === 0;

  return (
    <div className="h-full flex flex-col min-h-0 min-w-0" data-testid="request-list">
      {/* Search bar */}
      <div className="p-3 border-b border-slate-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            data-testid="search-requests"
            placeholder="Search requests..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9 h-9 text-sm max-[390px]:text-[13px] bg-white border-slate-200"
          />
        </div>
        <div className="mt-2 h-0.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full bg-blue-500 transition-all duration-300 ${
              loading ? "w-full opacity-100 animate-pulse" : "w-0 opacity-0"
            }`}
          />
        </div>
      </div>

      {/* Request items */}
      <ScrollArea className="flex-1 min-h-0 overflow-y-auto">
        {showInitialLoading ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm"
              >
                <div className="h-3 w-20 rounded bg-slate-100 animate-pulse" />
                <div className="mt-3 h-4 w-3/4 rounded bg-slate-100 animate-pulse" />
                <div className="mt-4 flex items-center justify-between gap-3">
                  <div className="h-3 w-24 rounded bg-slate-100 animate-pulse" />
                  <div className="h-3 w-16 rounded bg-slate-100 animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : requests.length === 0 ? (
          <div className="p-8 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <div className="text-sm font-medium text-slate-500">No requests found</div>
            <div className="text-xs text-slate-400 mt-1">Create a new request to get started</div>
          </div>
        ) : (
          <div>
            {requests.map((req, idx) => {
              const statusCfg = STATUS_CONFIG[req.status] || STATUS_CONFIG.in_progress;
              const StatusIcon = statusCfg.icon;
              const isActive = selectedRequest?.id === req.id;
              const ageIndicator = getRequestAgeIndicator(req);
              const timeAgo = req.created_at ? formatDistanceToNow(new Date(req.created_at), { addSuffix: true }) : "";

              return (
                <div
                  key={req.id}
                  data-testid={`request-item-${req.id}`}
                  className={`request-item px-4 py-3 max-[390px]:px-3 max-[390px]:py-2.5 border-b border-slate-100 ${isActive ? "active" : ""}`}
                  onClick={() => onSelect(req)}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] max-[390px]:text-[9px] text-slate-400">{req.request_number}</span>
                        {ageIndicator && (
                          <AlertTriangle className={`w-3 h-3 ${ageIndicator.iconClassName}`} />
                        )}
                      </div>
                      <h4 className="text-sm max-[390px]:text-[13px] font-medium text-slate-800 truncate mt-0.5">
                        {req.form_template_name || req.title}
                      </h4>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {ageIndicator && (
                        <span
                          className={`text-[10px] max-[390px]:text-[9px] px-1.5 py-0.5 rounded border font-medium ${ageIndicator.badgeClassName}`}
                        >
                          {ageIndicator.label}
                        </span>
                      )}
                      <span className={`text-[10px] max-[390px]:text-[9px] px-1.5 py-0.5 rounded border font-medium ${statusCfg.cls}`}>
                        {statusCfg.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs max-[390px]:text-[11px] text-slate-400 mt-1.5">
                    <span className="truncate">By {req.requester_name}</span>
                    <span className="flex-shrink-0 ml-2">{timeAgo}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs max-[390px]:text-[11px] text-slate-400 min-w-0">
                    {req.total_approval_steps > 0 && (
                      <span className="font-mono text-[10px] max-[390px]:text-[9px]">
                        Step {req.current_approval_step}/{req.total_approval_steps}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
