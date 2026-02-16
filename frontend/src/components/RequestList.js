import React from "react";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, FileText, Clock, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const STATUS_CONFIG = {
  in_progress: { label: "In Progress", icon: Clock, cls: "bg-blue-50 text-blue-700 border-blue-200" },
  approved: { label: "Approved", icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  rejected: { label: "Rejected", icon: XCircle, cls: "bg-red-50 text-red-700 border-red-200" },
  cancelled: { label: "Cancelled", icon: XCircle, cls: "bg-slate-100 text-slate-500 border-slate-300" },
};

const PRIORITY_CONFIG = {
  low: { cls: "text-slate-400" },
  normal: { cls: "text-slate-500" },
  high: { cls: "text-amber-500" },
  urgent: { cls: "text-red-500" },
};

export default function RequestList({
  requests, selectedRequest, onSelect, searchQuery, onSearchChange, loading
}) {
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
            className="pl-9 h-9 text-sm bg-white border-slate-200"
          />
        </div>
      </div>

      {/* Request items */}
      <ScrollArea className="flex-1 min-h-0 overflow-y-auto">
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-pulse-slow text-sm text-slate-400">Loading requests...</div>
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
              const priorityCfg = PRIORITY_CONFIG[req.priority] || PRIORITY_CONFIG.normal;
              const timeAgo = req.created_at ? formatDistanceToNow(new Date(req.created_at), { addSuffix: true }) : "";

              return (
                <div
                  key={req.id}
                  data-testid={`request-item-${req.id}`}
                  className={`request-item px-4 py-3 border-b border-slate-100 ${isActive ? "active" : ""}`}
                  onClick={() => onSelect(req)}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-slate-400">{req.request_number}</span>
                        {req.priority === "urgent" && <AlertTriangle className="w-3 h-3 text-red-500" />}
                        {req.priority === "high" && <AlertTriangle className="w-3 h-3 text-amber-500" />}
                      </div>
                      <h4 className="text-sm font-medium text-slate-800 truncate mt-0.5">{req.title}</h4>
                    </div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium flex-shrink-0 ${statusCfg.cls}`}>
                      {statusCfg.label}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400 mt-1.5">
                    <span className="truncate">{req.form_template_name}</span>
                    <span className="flex-shrink-0 ml-2">{timeAgo}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-slate-400 min-w-0">
                    <span className="truncate">By {req.requester_name}</span>
                    {req.total_approval_steps > 0 && (
                      <span className="font-mono text-[10px]">
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
