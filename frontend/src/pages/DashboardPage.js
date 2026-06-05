import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/store";
import { useLiveUpdates } from "@/hooks/useLiveUpdates";
import { useReactiveRefresh } from "@/hooks/useReactiveRefresh";

import {
  listRequests,
  listUsers,
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
import ChangePasswordDialog from "@/components/ChangePasswordDialog";
import NotificationPanel from "@/components/NotificationPanel";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { getSettingsMenuItems } from "@/components/settingsMenu";
import { isRequestorRole, isApproverRole, isSuperAdminRole, isManagerRole } from "@/lib/roles";
import { Plus, Bell, Settings, LogOut, Menu, KeyRound, ClipboardList } from "lucide-react";

const INITIAL_REQUEST_PAGE_SIZE = 12;
const REQUESTS_LOAD_MORE_SIZE = 5;
const EMPTY_REQUEST_DATE_FILTER = { preset: "all", from: "", to: "" };

export default function DashboardPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [departments, setDepartments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [users, setUsers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [totalRequests, setTotalRequests] = useState(0);
  const [stats, setStats] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const [selectedDept, setSelectedDept] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");

  const canCreateRequest = isRequestorRole(user?.role);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [requestDetailLoading, setRequestDetailLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [requestDateFilter, setRequestDateFilter] = useState(EMPTY_REQUEST_DATE_FILTER);
  const [requestFormFilter, setRequestFormFilter] = useState("");
  const [requestUserFilter, setRequestUserFilter] = useState("");
  const linkedRequestId = searchParams.get("request");

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showChangePasswordDialog, setShowChangePasswordDialog] = useState(false);
  const [showSettingsMenu, setShowSettingsMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMoreRequests, setLoadingMoreRequests] = useState(false);
  const [hasMoreRequests, setHasMoreRequests] = useState(false);

  const [listWidth, setListWidth] = useState(480);
  const minListWidth = 240;
  const maxListWidth = 580;
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

  const fetchRequests = useCallback(async ({ offset = 0, append = false } = {}) => {
    if (append) {
      setLoadingMoreRequests(true);
    } else {
      setLoading(true);
    }

    try {
      const limit = offset === 0 ? INITIAL_REQUEST_PAGE_SIZE : REQUESTS_LOAD_MORE_SIZE;
      const params = { offset, limit };
      const isSuperAdmin = isSuperAdminRole(user?.role);
      // Only super admin can filter by department
      if (isSuperAdmin && selectedDept) params.department_id = selectedDept;
      if (activeFilter === "my_requests") params.my_requests = true;
      if (activeFilter === "my_approvals") params.my_approvals = true;
      if (activeFilter === "pending") params.status = "pending";
      if (activeFilter === "custodian_pending") params.custodian_status = "pending";
      if (activeFilter === "approved") params.status = "approved";
      if (activeFilter === "custodian_fulfilled") params.custodian_status = "fulfilled";
      if (activeFilter === "rejected") params.status = "rejected";
      if (activeFilter === "cancelled") params.status = "cancelled";
      if (searchQuery) params.search = searchQuery;
      if (requestFormFilter) params.form_template_id = requestFormFilter;
      if (requestUserFilter) params.requester_id = requestUserFilter;
      if (requestDateFilter.from) params.date_from = requestDateFilter.from;
      if (requestDateFilter.to) params.date_to = requestDateFilter.to;

      const res = await listRequests(params);
      let nextLoadedCount = res.data.items.length;

      setRequests((prev) => {
        if (!append) {
          return res.data.items;
        }

        const seenIds = new Set(prev.map((item) => item.id));
        const nextItems = res.data.items.filter((item) => !seenIds.has(item.id));
        nextLoadedCount = prev.length + nextItems.length;
        return [...prev, ...nextItems];
      });
      setTotalRequests(res.data.total);
      setHasMoreRequests(nextLoadedCount < res.data.total);
    } catch (err) {
      console.error("Fetch requests error:", err);
    } finally {
      if (append) {
        setLoadingMoreRequests(false);
      } else {
        setLoading(false);
      }
    }
  }, [user?.role, selectedDept, activeFilter, searchQuery, requestFormFilter, requestUserFilter, requestDateFilter]);

  const fetchTemplates = useCallback(async () => {
    try {
      const params = selectedDept ? { department_id: selectedDept } : {};
      const res = await listTemplates(params);
      setTemplates(res.data);
    } catch (err) {
      console.error("Fetch templates error:", err);
    }
  }, [selectedDept]);

  const fetchUsers = useCallback(async () => {
    if (!isSuperAdminRole(user?.role) && !isManagerRole(user?.role)) {
      setUsers([]);
      return;
    }

    try {
      const params = selectedDept ? { department_id: selectedDept } : {};
      const res = await listUsers(params);
      setUsers(res.data);
    } catch (err) {
      console.error("Fetch users error:", err);
      setUsers([]);
    }
  }, [selectedDept, user?.role]);

  // Reset activeFilter if current filter is not allowed for user's role
  useEffect(() => {
    if (!user?.role) return;
    const role = user.role;
    const canUseMyRequests = isRequestorRole(role);
    const canUseMyApprovals = isApproverRole(role);
    if (activeFilter === "my_requests" && !canUseMyRequests) setActiveFilter("all");
    if (activeFilter === "my_approvals" && !canUseMyApprovals) setActiveFilter("all");
  }, [user?.role, activeFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  useEffect(() => {
    fetchRequests({ offset: 0, append: false });
  }, [fetchRequests]);
  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);
  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

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

  useReactiveRefresh(
    () => {
      fetchRequests();
      fetchData();

      if (selectedRequest?.id) {
        return getRequest(selectedRequest.id)
          .then((res) => setSelectedRequest((prev) => (
            prev?.id === selectedRequest.id ? res.data : prev
          )))
          .catch(() => {});
      }

      return Promise.resolve();
    },
    {
      enabled: !!user,
      intervalMs: 30000,
      refetchOnFocus: true,
    }
  );

  const handleCreateRequest = async (data) => {
    try {
      const res = await createRequest(data);
      toast.success("Request submitted successfully");
      setSelectedRequest(res.data);
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
      const actionLabel =
        action === "fulfill" ? "fulfilled" : `${action}d`;
      toast.success(`Request ${actionLabel} successfully`);
      setSelectedRequest(res.data);
      fetchRequests();
      fetchData();
    } catch (err) {
      toast.error(
        err.response?.data?.detail ||
          `Failed to ${action === "fulfill" ? "confirm fulfillment for" : action} request`,
      );
    }
  };

  const handleCancel = async (requestId, comments) => {
    try {
      const res = await cancelRequest(requestId, { comments });
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
    setSelectedRequest(req);
    setRequestDetailLoading(true);
    try {
      const res = await getRequest(req.id);
      setSelectedRequest(res.data);
    } catch {
      setSelectedRequest(req);
    } finally {
      setRequestDetailLoading(false);
    }
  };

  useEffect(() => {
    if (!linkedRequestId) return;

    setRequestDetailLoading(true);
    getRequest(linkedRequestId)
      .then((res) => setSelectedRequest(res.data))
      .catch((err) => {
        toast.error(
          err.response?.data?.detail || "Unable to open the linked request",
        );
      })
      .finally(() => setRequestDetailLoading(false));
  }, [linkedRequestId]);

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

  const settingsItems = getSettingsMenuItems(user?.role);

  const handleSettingsAction = (key) => {
    setShowSettingsMenu(false);

    if (key === "change_password") {
      setShowChangePasswordDialog(true);
      return;
    }

    if (key === "admin_panel" || key === "manage_forms") {
      navigate("/admin");
    }
  };

  const handleLoadMoreRequests = useCallback(() => {
    if (loading || loadingMoreRequests || !hasMoreRequests) {
      return;
    }

    fetchRequests({ offset: requests.length, append: true });
  }, [fetchRequests, hasMoreRequests, loading, loadingMoreRequests, requests.length]);

  const isShowingMobileDetail = !!selectedRequest || requestDetailLoading;

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
        <div className="min-h-14 border-b border-slate-200 flex items-center justify-between px-3 sm:px-4 py-2 bg-white flex-shrink-0 gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <button
              className="lg:hidden p-1.5 hover:bg-slate-100 rounded flex-shrink-0"
              onClick={() => setShowMobileSidebar(true)}
              data-testid="mobile-menu-button"
            >
              <Menu className="w-5 h-5 text-slate-600" />
            </button>
            <h2 className="text-sm font-semibold text-slate-800 truncate">
              {activeFilter === "all"
                ? "All Requests"
                : activeFilter === "my_requests"
                  ? "My Requests"
                  : activeFilter === "my_approvals"
                    ? "Pending My Approval"
                    : activeFilter === "custodian_pending"
                      ? "Pending Fulfillment"
                      : activeFilter === "custodian_fulfilled"
                        ? "Fulfilled Requests"
                        : activeFilter.charAt(0).toUpperCase() +
                          activeFilter.slice(1)}
              <span className="ml-2 text-xs text-slate-400 font-normal">
                ({totalRequests})
              </span>
            </h2>
          </div>
          <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
            {canCreateRequest && (
              <Button
                data-testid="new-request-button"
                onClick={() => setShowCreateDialog(true)}
                className="h-8 px-2 sm:px-3 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium"
              >
                <Plus className="w-3.5 h-3.5 sm:mr-1" />
                <span className="hidden sm:inline">New Request</span>
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
            {isSuperAdminRole(user?.role) ? (
              <button
                data-testid="admin-button"
                onClick={() => handleSettingsAction("admin_panel")}
                className="p-2 hover:bg-slate-100 rounded-md transition-colors"
                title="Admin Panel"
              >
                <Settings className="w-4.5 h-4.5 text-slate-500" />
              </button>
            ) : (
              <Popover open={showSettingsMenu} onOpenChange={setShowSettingsMenu}>
                <PopoverTrigger asChild>
                  <button
                    data-testid="settings-button"
                    className="p-2 hover:bg-slate-100 rounded-md transition-colors"
                    title="Settings"
                  >
                    <Settings className="w-4.5 h-4.5 text-slate-500" />
                  </button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-56 p-1.5">
                  {settingsItems.map((item) => {
                    const ItemIcon = item.key === "change_password" ? KeyRound : ClipboardList;
                    return (
                      <button
                        key={item.key}
                        type="button"
                        data-testid={`settings-${item.key}`}
                        onClick={() => handleSettingsAction(item.key)}
                        className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-slate-700 hover:bg-slate-100"
                      >
                        <ItemIcon className="h-4 w-4 text-slate-500" />
                        <span>{item.label}</span>
                      </button>
                    );
                  })}
                </PopoverContent>
              </Popover>
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

        <div className="flex-1 min-h-0 overflow-hidden lg:hidden bg-slate-50/40">
          {isShowingMobileDetail ? (
            <div className="h-full min-w-0 bg-white">
              <RequestDetail
                request={selectedRequest}
                currentUser={user}
                onAction={handleAction}
                onCancel={handleCancel}
                departments={departments}
                isLoading={requestDetailLoading}
                onBack={() => {
                  setRequestDetailLoading(false);
                  setSelectedRequest(null);
                }}
              />
            </div>
          ) : (
            <div className="h-full min-w-0  bg-white">
              <RequestList
                requests={requests}
                selectedRequest={selectedRequest}
                onSelect={handleSelectRequest}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                templates={templates}
                dateFilter={requestDateFilter}
                onDateFilterChange={setRequestDateFilter}
                formFilter={requestFormFilter}
                onFormFilterChange={setRequestFormFilter}
                users={users}
                userFilter={requestUserFilter}
                onUserFilterChange={setRequestUserFilter}
                loading={loading}
                loadingMore={loadingMoreRequests}
                hasMore={hasMoreRequests}
                onLoadMore={handleLoadMoreRequests}
              />
            </div>
          )}
        </div>

        {/* Desktop 2-panel: list + detail */}
        <div className="hidden lg:flex flex-1 overflow-hidden min-h-0">
          <div
            className="border-r border-slate-200 bg-slate-50/50 flex-shrink-0 overflow-hidden flex flex-col min-w-0 max-w-[500px]"
            style={{ width: listWidth, minWidth: minListWidth }}
          >
            <RequestList
              requests={requests}
              selectedRequest={selectedRequest}
              onSelect={handleSelectRequest}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              templates={templates}
              dateFilter={requestDateFilter}
              onDateFilterChange={setRequestDateFilter}
              formFilter={requestFormFilter}
              onFormFilterChange={setRequestFormFilter}
              users={users}
              userFilter={requestUserFilter}
              onUserFilterChange={setRequestUserFilter}
              loading={loading}
              loadingMore={loadingMoreRequests}
              hasMore={hasMoreRequests}
              onLoadMore={handleLoadMoreRequests}
            />
          </div>
          <div
            role="separator"
            aria-label="Resize panels"
            className=" flex-shrink-0 bg-slate-200 hover:bg-blue-400 active:bg-blue-500 cursor-col-resize transition-colors flex items-center justify-center group"
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
              isLoading={requestDetailLoading}
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
      <ChangePasswordDialog
        user={user}
        open={showChangePasswordDialog}
        onOpenChange={setShowChangePasswordDialog}
      />
    </div>
  );
}
