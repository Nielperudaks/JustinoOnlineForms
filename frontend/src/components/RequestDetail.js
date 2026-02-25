import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  User,
  Calendar,
  ArrowRight,
  MessageSquare,
  AlertTriangle,
  Building,
  Download,
  File,
  FormInput,
  FileArchive,
} from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { format } from "date-fns";

const STATUS_CONFIG = {
  in_progress: {
    label: "In Progress",
    icon: Clock,
    cls: "bg-blue-50 text-blue-700 border-blue-200",
  },
  approved: {
    label: "Approved",
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

const PRIORITY_COLORS = {
  low: "bg-slate-100 text-slate-600",
  normal: "bg-slate-100 text-slate-600",
  high: "bg-amber-50 text-amber-700 border-amber-200",
  urgent: "bg-red-50 text-red-700 border-red-200",
};

function ApprovalChain({ approvals }) {
  if (!approvals?.length) return null;
  return (
    <div className="space-y-3" data-testid="approval-chain">
      <h4 className="text-sm font-semibold text-slate-800">Approval Chain</h4>
      <div className="flex items-center gap-1 flex-wrap">
        {approvals.map((a, i) => {
          const isApproved = a.status === "approved";
          const isRejected = a.status === "rejected";
          const isPending = a.status === "pending";
          const isCancelled = a.status === "cancelled";
          const isWaiting = a.status === "waiting";
          return (
            <React.Fragment key={i}>
              <div
                data-testid={`approval-step-${a.step}`}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all ${
                  isApproved
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                    : isRejected
                      ? "bg-red-50 border-red-200 text-red-700"
                      : isPending
                        ? "bg-blue-50 border-blue-200 text-blue-700 animate-pulse-slow"
                        : isCancelled
                          ? "bg-slate-50 border-slate-200 text-slate-400"
                          : "bg-slate-50 border-slate-200 text-slate-400"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    isApproved
                      ? "bg-emerald-500 text-white"
                      : isRejected
                        ? "bg-red-500 text-white"
                        : isPending
                          ? "bg-blue-500 text-white"
                          : isCancelled
                            ? "bg-slate-300 text-white"
                            : "bg-slate-300 text-white"
                  }`}
                >
                  {isApproved ? (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  ) : isRejected ? (
                    <XCircle className="w-3.5 h-3.5" />
                  ) : isCancelled ? (
                    <XCircle className="w-3.5 h-3.5" />
                  ) : isPending ? (
                    <Clock className="w-3.5 h-3.5" />
                  ) : (
                    a.step
                  )}
                </div>
                <div>
                  <div className="font-medium text-xs">
                    {a.approver_name || "Approver"}
                  </div>
                  <div className="text-[10px] opacity-70 capitalize">
                    {a.status}
                  </div>
                </div>
              </div>
              {i < approvals.length - 1 && (
                <ArrowRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Comments from approvers */}
      {approvals
        .filter((a) => a.comments)
        .map((a, i) => (
          <div
            key={i}
            className="flex items-start gap-2 p-3 bg-slate-50 rounded-lg text-sm"
          >
            <MessageSquare className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-medium text-slate-700">
                {a.approver_name}:
              </span>
              <span className="text-slate-600 ml-1">{a.comments}</span>
            </div>
          </div>
        ))}
    </div>
  );
}

export default function RequestDetail({
  request,
  currentUser,
  onAction,
  onCancel,
  departments,
}) {
  const [comments, setComments] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);

  if (!request) {
    return (
      <div
        className="h-full flex items-center justify-center p-8"
        data-testid="request-detail-empty"
      >
        <div className="text-center">
          <FileText className="w-16 h-16 text-slate-200 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-400">
            Select a request
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            Choose a request from the list to view details
          </p>
        </div>
      </div>
    );
  }

  const statusCfg = STATUS_CONFIG[request.status] || STATUS_CONFIG.in_progress;
  const StatusIcon = statusCfg.icon;
  const dept = departments?.find((d) => d.id === request.department_id);
  const requesterDept = departments?.find(
    (d) => d.id === request.requester_department_id,
  );

  const canApprove =
    request.status === "in_progress" &&
    request.approvals?.some(
      (a) => a.approver_id === currentUser?.id && a.status === "pending",
    );

  const canCancel =
    request.status === "in_progress" &&
    currentUser?.id === request.requester_id;

  const handleAction = async (action) => {
    setActionLoading(true);
    await onAction(request.id, action, comments);
    setComments("");
    setActionLoading(false);
  };

  const handleCancel = async () => {
    if (!onCancel) return;
    // Simple confirm to avoid accidental cancellations
    // eslint-disable-next-line no-restricted-globals
    const confirmed = window.confirm(
      "Are you sure you want to cancel this request? Approvers will no longer be able to act on it.",
    );
    if (!confirmed) return;

    setCancelLoading(true);
    try {
      await onCancel(request.id);
    } finally {
      setCancelLoading(false);
    }
  };

  const formattedDate = request.created_at
    ? format(new Date(request.created_at), "MMM d, yyyy 'at' h:mm a")
    : "";

  return (
    <div className="h-full overflow-y-auto" data-testid="request-detail">
      <div className="max-w-3xl mx-auto p-6 lg:p-10 animate-fade-in">
        {/* Header */}
        <div className="">
          <div className="flex items-center gap-3 mb-3 flex-wrap">
            <span className="font-mono text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded">
              {request.request_number}
            </span>
            <Badge className={`${statusCfg.cls} border text-xs`}>
              <StatusIcon className="w-3 h-3 mr-1" />
              {statusCfg.label}
            </Badge>
            {request.priority && request.priority !== "normal" && (
              <Badge
                className={`${PRIORITY_COLORS[request.priority]} border text-xs capitalize`}
              >
                {request.priority === "urgent" && (
                  <AlertTriangle className="w-3 h-3 mr-1" />
                )}
                {request.priority}
              </Badge>
            )}
          </div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
            {request.title}
          </h2>
          <div className="flex items-center gap-4 mt-3 text-sm text-slate-500 flex-wrap">
            <span className="flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" />
              {request.requester_name}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              {formattedDate}
            </span>

            {requesterDept && (
              <span
                className="flex items-center gap-1.5"
                title="Requestor's department"
              >
                <Building className="w-3.5 h-3.5" />
                {requesterDept.name}
              </span>
            )}
          </div>
          <div className="flex mt-2 text-xs text-slate-400">
            {request && (
              <span className="flex items-center gap-1.5">
                <File className="w-3.5 h-3.5" />
                {request.form_template_name} 
              </span>
            )}
            {/* {request.form_template_name}{" "} */}
            {dept && (
              <span className="flex ml-1 items-center gap-1.5">
                {/* <Building className="w-3.5 h-3.5" /> */}
                - {dept.name}
              </span>
            )}
          </div>
        </div>

        <Separator className="my-6" />

        {/* Form Data */}

        <div className="mb-6">
          <h4 className="text-sm font-semibold text-slate-800 mb-3">
            Request Details
          </h4>
          <div className="flex flex-wrap -mx-2 gap-y-4">
            {Object.entries(request.form_data || {}).map(([key, value]) => {
              const label = key.replace(/_/g, " ");
              if (
                value &&
                typeof value === "object" &&
                "headers" in value &&
                "rows" in value
              ) {
                return (
                  <div key={key} className="w-full px-2">
                    <div className="rounded-lg border border-slate-200 overflow-hidden">
                      {value.title && (
                        <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-sm font-medium text-slate-700">
                          {value.title}
                        </div>
                      )}
                      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold px-3 pt-2">
                        {label}
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow className="bg-slate-100">
                            {(value.headers || []).map((h, i) => (
                              <TableHead key={i} className="text-xs font-medium">
                                {h}
                              </TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(value.rows || []).map((row, ri) => (
                            <TableRow key={ri}>
                              {(row || []).map((cell, ci) => (
                                <TableCell key={ci} className="text-sm py-2">
                                  {String(cell ?? "") || "-"}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                );
              }
              if (
                value &&
                typeof value === "object" &&
                "filename" in value &&
                "base64" in value
              ) {
                const handleDownload = () => {
                  const mimeType = value.mimeType || "application/octet-stream";
                  const byteChars = atob(value.base64);
                  const byteNumbers = new Array(byteChars.length);
                  for (let i = 0; i < byteChars.length; i++) {
                    byteNumbers[i] = byteChars.charCodeAt(i);
                  }
                  const byteArray = new Uint8Array(byteNumbers);
                  const blob = new Blob([byteArray], { type: mimeType });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = value.filename || "attachment";
                  a.click();
                  URL.revokeObjectURL(url);
                };
                return (
                  <div key={key} className="w-full px-2">
                    <Card className="overflow-hidden">
                      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold px-4 pt-3">
                        {label}
                      </div>
                      <CardContent className="p-4">
                        <button
                          onClick={handleDownload}
                          className="flex items-center gap-3 w-full p-3 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/30 transition-colors text-left"
                        >
                          <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                            <File className="w-5 h-5 text-slate-500" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-slate-800 truncate">
                              {value.filename}
                            </div>
                            <div className="text-xs text-slate-500">
                              Click to download
                            </div>
                          </div>
                          <Download className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        </button>
                      </CardContent>
                    </Card>
                  </div>
                );
              }
              return (
                <div key={key} className="w-full md:w-1/2 px-2">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                    <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">
                      {label}
                    </div>
                    <div className="text-sm text-slate-700">
                      {String(value ?? "") || "-"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Notes */}
        {request.notes && (
          <div className="mb-6 p-4 bg-amber-50/50 border border-amber-100 rounded-lg">
            <div className="text-xs font-semibold text-amber-700 mb-1">
              Notes
            </div>
            <div className="text-sm text-amber-800">{request.notes}</div>
          </div>
        )}

        <Separator className="my-6" />

        {/* Approval Chain */}
        {request.status !== "cancelled" && (
          <ApprovalChain approvals={request.approvals} />
        )}

        {/* Action buttons for current approver */}
        {canApprove && (
          <div
            className="mt-6 p-5 border border-blue-200 bg-blue-50/30 rounded-lg"
            data-testid="approval-actions"
          >
            <h4 className="text-sm font-semibold text-slate-800 mb-3">
              Your Action Required
            </h4>
            <Textarea
              data-testid="approval-comments"
              placeholder="Add comments (optional)..."
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              className="mb-3 bg-white text-sm"
              rows={3}
            />
            <div className="flex gap-3">
              <Button
                data-testid="approve-button"
                onClick={() => handleAction("approve")}
                disabled={actionLoading}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-5"
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Approve
              </Button>
              <Button
                data-testid="reject-button"
                onClick={() => handleAction("reject")}
                disabled={actionLoading}
                variant="outline"
                className="border-red-200 text-red-600 hover:bg-red-50 font-medium px-5"
              >
                <XCircle className="w-4 h-4 mr-2" />
                Reject
              </Button>
            </div>
          </div>
        )}

        {/* Cancel for requester while pending */}
        {canCancel && (
          <div className="mt-4 p-4 border border-slate-200 bg-slate-50/40 rounded-lg">
            <h4 className="text-sm font-semibold text-slate-800 mb-2">
              Cancel this request
            </h4>
            <p className="text-xs text-slate-500 mb-3">
              You can cancel this request while it is still in progress. Once
              cancelled, approvers will no longer be able to approve or reject
              it.
            </p>
            <Button
              data-testid="cancel-request-button"
              variant="outline"
              className="border-slate-300 text-slate-700 hover:bg-slate-100"
              disabled={cancelLoading}
              onClick={handleCancel}
            >
              <XCircle className="w-4 h-4 mr-2" />
              {cancelLoading ? "Cancelling..." : "Cancel Request"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
