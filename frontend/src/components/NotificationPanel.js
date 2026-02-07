import React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Bell, CheckCircle2, XCircle, Clock, Check, ExternalLink } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const TYPE_ICONS = {
  approval_required: Clock,
  request_approved: CheckCircle2,
  request_rejected: XCircle,
};

const TYPE_COLORS = {
  approval_required: "text-blue-500 bg-blue-50",
  request_approved: "text-emerald-500 bg-emerald-50",
  request_rejected: "text-red-500 bg-red-50",
};

export default function NotificationPanel({ notifications, onMarkRead, onMarkAllRead, onClose, onSelectRequest }) {
  return (
    <div
      className="absolute right-0 top-12 w-96 bg-white rounded-xl shadow-2xl border border-slate-200 z-50 animate-slide-up"
      data-testid="notification-panel"
    >
      <div className="flex items-center justify-between p-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-slate-600" />
          <span className="text-sm font-semibold text-slate-800">Notifications</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onMarkAllRead}
          className="text-xs text-blue-600 hover:text-blue-700 h-7 px-2"
          data-testid="mark-all-read"
        >
          <Check className="w-3 h-3 mr-1" /> Mark all read
        </Button>
      </div>
      <ScrollArea className="max-h-80">
        {notifications.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-400">No notifications</div>
        ) : (
          notifications.map((notif) => {
            const Icon = TYPE_ICONS[notif.type] || Bell;
            const colorCls = TYPE_COLORS[notif.type] || "text-slate-500 bg-slate-50";
            const timeAgo = notif.created_at
              ? formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })
              : "";
            return (
              <div
                key={notif.id}
                data-testid={`notification-${notif.id}`}
                className={`flex items-start gap-3 p-4 border-b border-slate-50 cursor-pointer transition-colors hover:bg-slate-50 ${!notif.is_read ? "bg-blue-50/30" : ""}`}
                onClick={() => {
                  if (!notif.is_read) onMarkRead(notif.id);
                  onSelectRequest(notif);
                }}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${colorCls}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-700 leading-snug">{notif.message}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-slate-400">{timeAgo}</span>
                    {notif.request_number && (
                      <span className="text-[10px] font-mono text-slate-400">{notif.request_number}</span>
                    )}
                  </div>
                </div>
                {!notif.is_read && <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0 mt-2" />}
              </div>
            );
          })
        )}
      </ScrollArea>
      <div className="p-3 border-t border-slate-100 text-center">
        <button onClick={onClose} className="text-xs text-slate-500 hover:text-slate-700">Close</button>
      </div>
    </div>
  );
}
