import React, { useCallback, useMemo, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Search,
  FileText,
  AlertTriangle,
  CalendarDays,
  UserRound,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { differenceInHours, formatDistanceToNow } from "date-fns";
import { getRequestStatusConfig } from "./requestStatus";

function getRequestAgeIndicator(request) {
  if (!["in_progress", "pending"].includes(request.status) || !request.created_at) {
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

const EMPTY_DATE_FILTER = { preset: "all", from: "", to: "" };

function toDateInputValue(date) {
  const timezoneOffset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 10);
}

function getPresetRange(preset) {
  const today = new Date();
  const from = new Date(today);

  if (preset === "today") {
    return {
      preset,
      from: toDateInputValue(today),
      to: toDateInputValue(today),
    };
  }

  if (preset === "last7") {
    from.setDate(today.getDate() - 6);
    return {
      preset,
      from: toDateInputValue(from),
      to: toDateInputValue(today),
    };
  }

  if (preset === "last30") {
    from.setDate(today.getDate() - 29);
    return {
      preset,
      from: toDateInputValue(from),
      to: toDateInputValue(today),
    };
  }

  return EMPTY_DATE_FILTER;
}

function getDateFilterLabel(dateFilter) {
  if (!dateFilter?.from && !dateFilter?.to) return "Any date";
  if (dateFilter.preset === "today") return "Today";
  if (dateFilter.preset === "last7") return "Last 7 days";
  if (dateFilter.preset === "last30") return "Last 30 days";
  if (dateFilter.from && dateFilter.to) return `${dateFilter.from} to ${dateFilter.to}`;
  if (dateFilter.from) return `From ${dateFilter.from}`;
  return `Until ${dateFilter.to}`;
}

export default function RequestList({
  requests,
  selectedRequest,
  onSelect,
  searchQuery,
  onSearchChange,
  loading,
  // Pagination props (replaces loadingMore / hasMore / onLoadMore)
  currentPage = 1,
  totalPages = 1,
  onPageChange,
  templates = [],
  dateFilter = EMPTY_DATE_FILTER,
  onDateFilterChange,
  formFilter = "",
  onFormFilterChange,
  users = [],
  userFilter = "",
  onUserFilterChange,
  // Role-gated visibility
  showUserFilter = false,
}) {
  const scrollAreaRef = useRef(null);
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const showInitialLoading = loading && requests.length === 0;
  const dateFilterActive = Boolean(dateFilter?.from || dateFilter?.to);
  const userFilterActive = Boolean(userFilter);

  const formOptions = useMemo(
    () => templates.filter((template) => template.is_active !== false),
    [templates],
  );

  // Users come entirely from the users prop — no request-scanning fallback.
  const allUserOptions = useMemo(() => {
    return [...users]
      .filter((item) => item?.id && item.is_active !== false)
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [users]);

  const selectedUser = allUserOptions.find((item) => item.id === userFilter);

  const userOptions = useMemo(() => {
    const normalizedSearch = userSearchQuery.trim().toLowerCase();
    if (!normalizedSearch) return allUserOptions;
    return allUserOptions.filter((item) =>
      [item.name, item.email]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(normalizedSearch)),
    );
  }, [allUserOptions, userSearchQuery]);

  const hasPrev = currentPage > 1;
  const hasNext = currentPage < totalPages;

  return (
    <div className="h-full flex flex-col min-h-0 min-w-0" data-testid="request-list">
      {/* Search + filter bar */}
      <div className="p-3 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="relative flex-1 min-w-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              data-testid="search-requests"
              placeholder="Search requests..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-9 h-9 text-sm max-[420px]:text-[13px] bg-white border-slate-200"
            />
          </div>

          {/* Date filter */}
          <Popover>
            <PopoverTrigger asChild>
              <button
                type="button"
                data-testid="date-filter-trigger"
                title={getDateFilterLabel(dateFilter)}
                className={`relative h-9 w-9 rounded-md border flex items-center justify-center transition-colors ${
                  dateFilterActive
                    ? "border-blue-200 bg-blue-50 text-blue-700"
                    : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
                }`}
              >
                <CalendarDays className="w-4 h-4" />
                {dateFilterActive && (
                  <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-blue-500" />
                )}
              </button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-72 p-3">
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-semibold text-slate-700">Date filter</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {getDateFilterLabel(dateFilter)}
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {[
                    ["today", "Today"],
                    ["last7", "7 days"],
                    ["last30", "30 days"],
                  ].map(([preset, label]) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => onDateFilterChange?.(getPresetRange(preset))}
                      className={`h-8 rounded-md border text-xs transition-colors ${
                        dateFilter?.preset === preset
                          ? "border-blue-200 bg-blue-50 text-blue-700"
                          : "border-slate-200 text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="grid gap-2">
                  <div className="space-y-1 w-[150px]">
                    <label className="text-[11px] text-slate-500" htmlFor="request-date-from">
                      From
                    </label>
                    <Input
                      id="request-date-from"
                      data-testid="date-filter-from"
                      type="date"
                      value={dateFilter?.from || ""}
                      onChange={(e) =>
                        onDateFilterChange?.({
                          ...dateFilter,
                          preset: "custom",
                          from: e.target.value,
                        })
                      }
                      className="h-8 text-xs"
                    />
                  </div>
                  <div className="space-y-1 w-[150px]">
                    <label className="text-[11px] text-slate-500" htmlFor="request-date-to">
                      To
                    </label>
                    <Input
                      id="request-date-to"
                      data-testid="date-filter-to"
                      type="date"
                      value={dateFilter?.to || ""}
                      onChange={(e) =>
                        onDateFilterChange?.({
                          ...dateFilter,
                          preset: "custom",
                          to: e.target.value,
                        })
                      }
                      className="h-8 text-xs"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => onDateFilterChange?.(EMPTY_DATE_FILTER)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-xs text-slate-500 hover:bg-slate-100"
                >
                  <X className="w-3.5 h-3.5" />
                  Clear date
                </button>
              </div>
            </PopoverContent>
          </Popover>

          {/* User filter — only rendered for roles that can see other users' requests */}
          {showUserFilter && (
            <Popover>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  data-testid="user-filter-trigger"
                  title={selectedUser?.name || "Any user"}
                  className={`relative h-9 w-9 rounded-md border flex items-center justify-center transition-colors ${
                    userFilterActive
                      ? "border-blue-200 bg-blue-50 text-blue-700"
                      : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
                  }`}
                >
                  <UserRound className="w-4 h-4" />
                  {userFilterActive && (
                    <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-blue-500" />
                  )}
                </button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-72 p-2">
                <div className="px-1.5 pb-2 pt-1">
                  <p className="text-xs font-semibold text-slate-700">User filter</p>
                  <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                    {selectedUser?.name || "Any user"}
                  </p>
                </div>
                <div className="relative mb-2">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                  <Input
                    data-testid="user-filter-search"
                    placeholder="Search users..."
                    value={userSearchQuery}
                    onChange={(e) => setUserSearchQuery(e.target.value)}
                    className="h-8 pl-8 text-xs"
                  />
                </div>
                <div className="max-h-64 overflow-y-auto pr-1">
                  <button
                    type="button"
                    onClick={() => onUserFilterChange?.("")}
                    className={`w-full rounded-md px-2 py-2 text-left text-xs transition-colors ${
                      !userFilter
                        ? "bg-blue-50 text-blue-700"
                        : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    All users
                  </button>
                  {userOptions.length === 0 ? (
                    <div className="px-2 py-4 text-center text-xs text-slate-400">
                      No users found
                    </div>
                  ) : (
                    userOptions.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => onUserFilterChange?.(item.id)}
                        className={`mt-1 w-full rounded-md px-2 py-2 text-left text-xs transition-colors ${
                          userFilter === item.id
                            ? "bg-blue-50 text-blue-700"
                            : "text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        <span className="block truncate">{item.name}</span>
                        {item.email && (
                          <span className="mt-0.5 block truncate text-[11px] text-slate-400">
                            {item.email}
                          </span>
                        )}
                      </button>
                    ))
                  )}
                </div>
              </PopoverContent>
            </Popover>
          )}
        </div>

        {/* Loading bar */}
        <div className="mt-2 h-0.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full bg-blue-500 transition-all duration-300 ${
              loading ? "w-full opacity-100 animate-pulse" : "w-0 opacity-0"
            }`}
          />
        </div>
      </div>

      {/* Request items */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 min-h-0 overflow-y-auto">
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
              const statusCfg = getRequestStatusConfig(req);
              const isActive = selectedRequest?.id === req.id;
              const ageIndicator = getRequestAgeIndicator(req);
              const timeAgo = req.created_at
                ? formatDistanceToNow(new Date(req.created_at), { addSuffix: true })
                : "";

              return (
                <div
                  key={req.id}
                  data-testid={`request-item-${req.id}`}
                  className={`request-item px-4 py-3 max-[420px]:px-3 max-[420px]:py-2.5 border-b border-slate-100 ${isActive ? "active" : ""}`}
                  onClick={() => onSelect(req)}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] max-[420px]:text-[9px] text-slate-400">
                          {req.request_number}
                        </span>
                        {ageIndicator && (
                          <AlertTriangle className={`w-3 h-3 ${ageIndicator.iconClassName}`} />
                        )}
                      </div>
                      <h4 className="text-sm max-[420px]:text-[13px] max-w-[90%] font-medium text-slate-800 truncate mt-0.5">
                        {req.form_template_name || req.title}
                      </h4>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {ageIndicator && (
                        <span
                          className={`text-[10px] max-[420px]:text-[9px] px-1.5 py-0.5 rounded border font-medium ${ageIndicator.badgeClassName}`}
                        >
                          {ageIndicator.label}
                        </span>
                      )}
                      <span
                        className={`text-[10px] max-[420px]:text-[9px] px-1.5 py-0.5 rounded border font-medium ${statusCfg.cls}`}
                      >
                        {statusCfg.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs max-[420px]:text-[11px] text-slate-400 mt-1.5">
                    <span className="truncate">By {req.requester_name}</span>
                    <span className="flex-shrink-0 ml-2">{timeAgo}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs max-[420px]:text-[11px] text-slate-400 min-w-0">
                    {req.total_approval_steps > 0 && (
                      <span className="font-mono text-[10px] max-[420px]:text-[9px]">
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

      {/* Pagination footer — only shown when there is more than one page */}
      {totalPages > 1 && (
        <div className="flex-shrink-0 flex items-center justify-between gap-2 px-3 py-2 border-t border-slate-200 bg-white">
          <button
            type="button"
            data-testid="pagination-prev"
            onClick={() => onPageChange?.(currentPage - 1)}
            disabled={!hasPrev || loading}
            className="flex items-center gap-1 h-7 px-2 rounded-md border border-slate-200 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Prev
          </button>

          <span className="text-xs text-slate-500 tabular-nums">
            Page {currentPage} of {totalPages}
          </span>

          <button
            type="button"
            data-testid="pagination-next"
            onClick={() => onPageChange?.(currentPage + 1)}
            disabled={!hasNext || loading}
            className="flex items-center gap-1 h-7 px-2 rounded-md border border-slate-200 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}