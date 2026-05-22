import { Clock, CheckCircle2, XCircle } from "lucide-react";

export const STATUS_CONFIG = {
  in_progress: {
    label: "In Progress",
    icon: Clock,
    cls: "bg-blue-50 text-blue-700 border-blue-200",
  },
  pending: {
    label: "Pending",
    icon: Clock,
    cls: "bg-blue-50 text-blue-700 border-blue-200",
  },
  pending_fulfillment: {
    label: "Pending Fulfillment",
    icon: Clock,
    cls: "bg-amber-50 text-amber-700 border-amber-200",
  },
  approved: {
    label: "Completed",
    icon: CheckCircle2,
    cls: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  fulfilled: {
    label: "Fulfilled",
    icon: CheckCircle2,
    cls: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  rejected: {
    label: "Rejected",
    icon: XCircle,
    cls: "bg-red-50 text-red-700 border-red-200",
  },
  cancelled: {
    label: "Cancelled",
    icon: XCircle,
    cls: "bg-slate-100 text-slate-500 border-slate-300",
  },
};

export function getRequestDisplayStatus(request) {
  if (request?.custodian?.status === "fulfilled") {
    return "fulfilled";
  }

  if (request?.custodian?.status === "pending") {
    return "pending_fulfillment";
  }

  return request?.status || "in_progress";
}

export function getRequestStatusConfig(request) {
  return STATUS_CONFIG[getRequestDisplayStatus(request)] || STATUS_CONFIG.in_progress;
}
