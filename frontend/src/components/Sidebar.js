import React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  LayoutDashboard,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  ClipboardCheck,
  ChevronRight,
  X,
} from "lucide-react";

const FILTER_ITEMS = [
  { key: "all", label: "All Requests", icon: LayoutDashboard },
  { key: "my_requests", label: "My Requests", icon: FileText },
  { key: "my_approvals", label: "Pending My Approval", icon: ClipboardCheck },
  { key: "pending", label: "In Progress", icon: Clock },
  { key: "approved", label: "Approved", icon: CheckCircle2 },
  { key: "rejected", label: "Rejected", icon: XCircle },
  { key: "cancelled", label: "Cancelled", icon: XCircle },
];

export default function Sidebar({
  user, departments, selectedDept, setSelectedDept,
  activeFilter, setActiveFilter, stats, onClose
}) {
  return (
    <div className="h-full bg-slate-900 flex flex-col" data-testid="sidebar">
      {/* Header */}
      <div className="p-4 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="text-white text-sm font-bold tracking-tight">Justino Online Forms</div>
            <div className="text-slate-500 text-[10px] uppercase tracking-widest font-medium">Paperless System</div>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="lg:hidden text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* User info */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="text-slate-200 text-sm font-medium truncate">{user?.name}</div>
        <div className="text-slate-500 text-xs truncate">{user?.email}</div>
        <div className="mt-1.5 inline-flex px-2 py-0.5 bg-blue-600/20 text-blue-400 text-[10px] font-semibold uppercase tracking-wider rounded">
          {user?.role?.replace("_", " ")}
        </div>
      </div>

      <ScrollArea className="flex-1">
        {/* Filters */}
        <div className="p-3">
          <div className="text-slate-500 text-[10px] uppercase tracking-widest font-semibold px-3 mb-2">
            Filters
          </div>
          {FILTER_ITEMS.map((item) => {
            const Icon = item.icon;
            const count =
              item.key === "my_approvals"
                ? stats?.my_pending_approvals
                : item.key === "pending"
                  ? stats?.pending_requests
                  : item.key === "approved"
                    ? stats?.approved_requests
                    : item.key === "rejected"
                      ? stats?.rejected_requests
                      : item.key === "cancelled"
                        ? stats?.cancelled_requests
                        : item.key === "all"
                          ? stats?.total_requests
                          : null;
            return (
              <button
                key={item.key}
                data-testid={`filter-${item.key}`}
                className={`sidebar-item w-full ${activeFilter === item.key && !selectedDept ? "active" : ""}`}
                onClick={() => { setActiveFilter(item.key); setSelectedDept(null); }}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="flex-1 text-left truncate">{item.label}</span>
                {count != null && count > 0 && (
                  <span className="text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Departments */}
        <div className="p-3 pt-0">
          <div className="text-slate-500 text-[10px] uppercase tracking-widest font-semibold px-3 mb-2 mt-2">
            Departments
          </div>
          {departments.map((dept) => (
            <button
              key={dept.id}
              data-testid={`dept-${dept.code}`}
              className={`sidebar-item w-full ${selectedDept === dept.id ? "active" : ""}`}
              onClick={() => { setSelectedDept(dept.id); setActiveFilter("all"); }}
            >
              <div className="w-2 h-2 rounded-full bg-slate-600 flex-shrink-0" />
              <span className="flex-1 text-left truncate">{dept.name}</span>
              <ChevronRight className="w-3 h-3 text-slate-600" />
            </button>
          ))}
        </div>
      </ScrollArea>

      {/* Stats footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-800/50 rounded-md p-2.5 text-center">
            <div className="text-lg font-bold text-white">{stats?.total_requests || 0}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Total</div>
          </div>
          <div className="bg-slate-800/50 rounded-md p-2.5 text-center">
            <div className="text-lg font-bold text-blue-400">{stats?.my_pending_approvals || 0}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">To Approve</div>
          </div>
        </div>
      </div>
    </div>
  );
}
