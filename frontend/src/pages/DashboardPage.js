import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/store";
import { useLiveUpdates } from "@/hooks/useLiveUpdates";

import {
  listRequests,
  listDepartments,
  listTemplates,
  getDashboardStats,
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  createRequest,
  actionRequest,
  getRequest,
  cancelRequest,
} from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import RequestList from "@/components/RequestList";
import RequestDetail from "@/components/RequestDetail";
import CreateRequestDialog from "@/components/CreateRequestDialog";
import NotificationPanel from "@/components/NotificationPanel";
import { Button } from "@/components/ui/button";
import { Plus, Bell, Settings, LogOut, Menu, X } from "lucide-react";

export default function DashboardPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const [departments, setDepartments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [requests, setRequests] = useState([]);
  const [totalRequests, setTotalRequests] = useState(0);
  const [stats, setStats] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const [selectedDept, setSelectedDept] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");

  const canCreateRequest = user?.role === "requestor" || user?.role === "both" || user?.role === "manager" || user?.role === "super_admin";
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [loading, setLoading] = useState(true);

  const [listWidth, setListWidth] = useState(480);
  const minListWidth = 240;
  const maxListWidth = 480;
  const isResizingRef = useRef(false);

  const handleResizeStart = useCallback(
    (e) => {
      e.preventDefault();
      isResizingRef.current = true;
      const startX = e.clientX;
      const startWidth = listWidth;

      const onMouseMove = (moveEvent) => {
        const delta = moveEvent.clientX - startX;
        setListWidth((prev) =>
          Math.min(maxListWidth, Math.max(minListWidth, startWidth + delta)),
        );
      };

      const onMouseUp = () => {
        isResizingRef.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [listWidth, minListWidth, maxListWidth],
  );

  const fetchData = useCallback(async () => {
    try {
      const [deptRes, statsRes, notifRes] = await Promise.all([
        listDepartments(),
        getDashboardStats(),
        listNotifications({ limit: 20 }),
      ]);
      setDepartments(deptRes.data);
      setStats(statsRes.data);
      setNotifications(notifRes.data.items);
      setUnreadCount(notifRes.data.unread_count);
    } catch (err) {
      console.error("Fetch error:", err);
    }
  }, []);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 100 };
      const isSuperAdmin = user?.role === "super_admin";
      // Only super admin can filter by department
      if (isSuperAdmin && selectedDept) params.department_id = selectedDept;
      if (activeFilter === "my_requests") params.my_requests = true;
      if (activeFilter === "my_approvals") params.my_approvals = true;
      if (activeFilter === "pending") params.status = "in_progress";
      if (activeFilter === "approved") params.status = "approved";
      if (activeFilter === "rejected") params.status = "rejected";
      if (activeFilter === "cancelled") params.status = "cancelled";
      if (searchQuery) params.search = searchQuery;

      const res = await listRequests(params);
      setRequests(res.data.items);
      setTotalRequests(res.data.total);
    } catch (err) {
      console.error("Fetch requests error:", err);
    } finally {
      setLoading(false);
    }
  }, [user?.role, selectedDept, activeFilter, searchQuery]);

  const fetchTemplates = useCallback(async () => {
    try {
      const params = selectedDept ? { department_id: selectedDept } : {};
      const res = await listTemplates(params);
      setTemplates(res.data);
    } catch (err) {
      console.error("Fetch templates error:", err);
    }
  }, [selectedDept]);

  // Reset activeFilter if current filter is not allowed for user's role
  useEffect(() => {
    if (!user?.role) return;
    const role = user.role;
    const canUseMyRequests = role === "requestor" || role === "both" || role === "manager" || role === "super_admin";
    const canUseMyApprovals = role === "approver" || role === "both" || role === "manager" || role === "super_admin";
    if (activeFilter === "my_requests" && !canUseMyRequests) setActiveFilter("all");
    if (activeFilter === "my_approvals" && !canUseMyApprovals) setActiveFilter("all");
  }, [user?.role, activeFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);
  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useLiveUpdates({
    enabled: !!user,
    onEvent: ({ event, payload }) => {
      switch (event) {
        case "REQUEST_CREATED":
        case "REQUEST_UPDATED":
        case "REQUEST_APPROVED":
        case "REQUEST_REJECTED":
        case "REQUEST_CANCELLED":
        case "REQUEST_STATE_CHANGED": {
          // Refresh request lists and stats
          fetchRequests();
          fetchData();

          // If the currently opened request changed, refresh it
          if (selectedRequest?.id === payload?.request_id) {
            getRequest(payload.request_id)
              .then((res) => setSelectedRequest(res.data))
              .catch(() => {});
          }
          break;
        }

        case "NOTIFICATION_CREATED": {
          if (payload?.user_id === user?.id) {
            listNotifications({ limit: 20 }).then((res) => {
              setNotifications(res.data.items);
              setUnreadCount(res.data.unread_count);
            });
            fetchData(); // unread badge in dashboard stats
          }
          break;
        }

        case "NOTIFICATION_READ":
        case "NOTIFICATIONS_CLEARED": {
          if (payload?.user_id === user?.id) {
            listNotifications({ limit: 20 }).then((res) => {
              setNotifications(res.data.items);
              setUnreadCount(res.data.unread_count);
            });
            fetchData();
          }
          break;
        }

        default:
          break;
      }
    },
  });

  // When requests list is refreshed (e.g. by polling), refetch the selected
  // request so the detail panel shows latest approval state without full reload.
  // const selectedIdRef = useRef(selectedRequest?.id);
  // selectedIdRef.current = selectedRequest?.id;
  // useEffect(() => {
  //   const id = selectedIdRef.current;
  //   if (!id) return;
  //   getRequest(id)
  //     .then((res) => setSelectedRequest((prev) => (prev?.id === id ? res.data : prev)))
  //     .catch(() => {});
  // }, [requests]);

  const handleCreateRequest = async (data) => {
    try {
      await createRequest(data);
      toast.success("Request submitted successfully");
      setShowCreateDialog(false);
      fetchRequests();
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create request");
    }
  };

  const handleAction = async (requestId, action, comments) => {
    try {
      const res = await actionRequest(requestId, { action, comments });
      toast.success(`Request ${action}d successfully`);
      setSelectedRequest(res.data);
      fetchRequests();
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Failed to ${action} request`);
    }
  };

  const handleCancel = async (requestId) => {
    try {
      const res = await cancelRequest(requestId);
      toast.success("Request cancelled successfully");
      setSelectedRequest(res.data);
      fetchRequests();
      fetchData();
    } catch (err) {
      toast.error(
        err.response?.data?.detail || "Failed to cancel request",
      );
    }
  };

  const handleSelectRequest = async (req) => {
    try {
      const res = await getRequest(req.id);
      setSelectedRequest(res.data);
    } catch {
      setSelectedRequest(req);
    }
  };

  const handleMarkRead = async (id) => {
    await markNotificationRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div
      className="h-screen flex overflow-hidden bg-white"
      data-testid="dashboard-page"
    >
      {/* Mobile sidebar overlay */}
      {showMobileSidebar && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowMobileSidebar(false)}
          />
          <div className="relative w-64 h-full">
            <Sidebar
              user={user}
              departments={departments}
              selectedDept={selectedDept}
              setSelectedDept={(d) => {
                setSelectedDept(d);
                setShowMobileSidebar(false);
              }}
              activeFilter={activeFilter}
              setActiveFilter={(f) => {
                setActiveFilter(f);
                setShowMobileSidebar(false);
              }}
              stats={stats}
              onClose={() => setShowMobileSidebar(false)}
            />
          </div>
        </div>
      )}

      {/* Desktop Sidebar */}
      <div className="hidden lg:block w-64 flex-shrink-0">
        <Sidebar
          user={user}
          departments={departments}
          selectedDept={selectedDept}
          setSelectedDept={setSelectedDept}
          activeFilter={activeFilter}
          setActiveFilter={setActiveFilter}
          stats={stats}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="h-14 border-b border-slate-200 flex items-center justify-between px-4 bg-white flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-1.5 hover:bg-slate-100 rounded"
              onClick={() => setShowMobileSidebar(true)}
              data-testid="mobile-menu-button"
            >
              <Menu className="w-5 h-5 text-slate-600" />
            </button>
            <h2 className="text-sm font-semibold text-slate-800">
              {activeFilter === "all"
                ? "All Requests"
                : activeFilter === "my_requests"
                  ? "My Requests"
                  : activeFilter === "my_approvals"
                    ? "Pending My Approval"
                    : activeFilter.charAt(0).toUpperCase() +
                      activeFilter.slice(1)}
              <span className="ml-2 text-xs text-slate-400 font-normal">
                ({totalRequests})
              </span>
            </h2>
          </div>
          <div className="flex items-center gap-2">
            {canCreateRequest && (
              <Button
                data-testid="new-request-button"
                onClick={() => setShowCreateDialog(true)}
                className="h-8 px-3 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium"
              >
                <Plus className="w-3.5 h-3.5 mr-1" /> New Request
              </Button>
            )}
            <div className="relative">
              <button
                data-testid="notifications-button"
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 hover:bg-slate-100 rounded-md transition-colors"
              >
                <Bell className="w-4.5 h-4.5 text-slate-500" />
                {unreadCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>
              {showNotifications && (
                <NotificationPanel
                  notifications={notifications}
                  onMarkRead={handleMarkRead}
                  onMarkAllRead={handleMarkAllRead}
                  onClose={() => setShowNotifications(false)}
                  onSelectRequest={(notif) => {
                    if (notif.request_id) {
                      const req = requests.find(
                        (r) => r.id === notif.request_id,
                      );
                      if (req) handleSelectRequest(req);
                    }
                    setShowNotifications(false);
                  }}
                />
              )}
            </div>
            {user?.role === "super_admin" && (
              <button
                data-testid="admin-button"
                onClick={() => navigate("/admin")}
                className="p-2 hover:bg-slate-100 rounded-md transition-colors"
                title="Admin Panel"
              >
                <Settings className="w-4.5 h-4.5 text-slate-500" />
              </button>
            )}
            <button
              data-testid="logout-button"
              onClick={handleLogout}
              className="p-2 hover:bg-slate-100 rounded-md transition-colors"
              title="Sign out"
            >
              <LogOut className="w-4.5 h-4.5 text-slate-500" />
            </button>
          </div>
        </div>

        {/* 2-panel: list + detail (resizable divider) */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          <div
            className="border-r border-slate-200 bg-slate-50/50 flex-shrink-0 overflow-hidden flex flex-col min-w-0"
            style={{ width: listWidth, minWidth: minListWidth }}
          >
            <RequestList
              requests={requests}
              selectedRequest={selectedRequest}
              onSelect={handleSelectRequest}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              loading={loading}
            />
          </div>
          <div
            role="separator"
            aria-label="Resize panels"
            className="w-1 flex-shrink-0 bg-slate-200 hover:bg-blue-400 active:bg-blue-500 cursor-col-resize transition-colors flex items-center justify-center group"
            onMouseDown={handleResizeStart}
          >
            <div className="w-0.5 h-8 bg-slate-400 group-hover:bg-blue-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="flex-1 min-w-0 overflow-y-auto bg-white">
            <RequestDetail
              request={selectedRequest}
              currentUser={user}
              onAction={handleAction}
              onCancel={handleCancel}
              departments={departments}
            />
          </div>
        </div>
      </div>

      {/* Create Request Dialog */}
      {showCreateDialog && (
        <CreateRequestDialog
          templates={templates}
          departments={departments}
          onSubmit={handleCreateRequest}
          onClose={() => setShowCreateDialog(false)}
        />
      )}
    </div>
  );
}
