import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/store";
import { useLiveUpdates } from "@/hooks/useLiveUpdates";
import { useReactiveRefresh } from "@/hooks/useReactiveRefresh";
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  listDepartments,
  listAllDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
  listAllTemplates,
  updateTemplate,
  createTemplate,
  deleteTemplate,
  listApprovers,
  listCustodians,
  getDashboardStats,
} from "@/lib/api";
import {
  isApproverUser,
  isCustodianUser,
  getAvailableDepartmentGroupMembers,
  getEditableDepartmentGroups,
  getSpecialApproverLabel,
  mergeServerItemsWithLocalChanges,
  removeById,
  SPECIAL_APPROVERS,
  upsertById,
} from "@/pages/adminState";
import { shouldRefreshAdminData } from "@/pages/adminRealtime";
import {
  getRoleLabel,
  isApproverRole,
  isExecutiveRole,
  isManagerRole,
  isSuperAdminRole,
  ROLE_OPTIONS,
} from "@/lib/roles";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import BuildFormDialog from "@/components/BuildFormDialog";
import {
  ArrowLeft,
  Users,
  FileText,
  Building,
  Plus,
  Pencil,
  Trash2,
  Shield,
  X,
  Save,
  Check,
  ChevronDown,
  ChevronUp,
  Search,
  Wrench,
} from "lucide-react";

const MAX_APPROVER_STEPS = 8;
const LOCAL_CHANGE_TTL_MS = 90000;
const APPROVER_STEPS = Array.from(
  { length: MAX_APPROVER_STEPS },
  (_, index) => index + 1,
);

function ApproverPicker({ assigned, approvers, onSelect, testId, placeholder }) {
  const [open, setOpen] = useState(false);
  const selectedApprover = approvers.find((a) => a.id === assigned?.user_id);
  const specialLabel = getSpecialApproverLabel(assigned?.user_id);
  const selectedLabel =
    specialLabel ||
    (selectedApprover
        ? `${selectedApprover.name} (${selectedApprover.email})`
        : assigned?.user_name || "");

  const handleSelect = (userId) => {
    onSelect(userId);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={testId}
          className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 text-left text-xs text-slate-700 hover:border-blue-300 hover:bg-blue-50/40 focus:outline-none focus:ring-2 focus:ring-blue-100 transition-colors flex items-center justify-between gap-2"
        >
          <span className={selectedLabel ? "truncate" : "truncate text-slate-400"}>
            {selectedLabel || placeholder}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[calc(100vw-2rem)] p-0 sm:w-[22rem]" align="start">
        <Command>
          <CommandInput placeholder="Search approvers by name or email..." />
          <CommandList>
            <CommandEmpty>No matching approvers found.</CommandEmpty>
            <CommandGroup heading="Role-based approvers">
              {SPECIAL_APPROVERS.map((special) => (
                <CommandItem
                  key={special.id}
                  value={special.label}
                  onSelect={() => handleSelect(special.id)}
                  className="text-xs"
                >
                  <Check
                    className={`w-3.5 h-3.5 ${
                      assigned?.user_id === special.id ? "opacity-100" : "opacity-0"
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="font-medium text-slate-700">{special.label}</div>
                    <div className="text-[11px] text-slate-400">
                      {special.description}
                    </div>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="Suggested users">
              {approvers.map((approver) => (
                <CommandItem
                  key={approver.id}
                  value={`${approver.name} ${approver.email}`}
                  onSelect={() => handleSelect(approver.id)}
                  className="text-xs"
                >
                  <Check
                    className={`w-3.5 h-3.5 ${
                      assigned?.user_id === approver.id
                        ? "opacity-100"
                        : "opacity-0"
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="font-medium text-slate-700 truncate">
                      {approver.name}
                    </div>
                    <div className="text-[11px] text-slate-400 truncate">
                      {approver.email}
                    </div>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

function CustodianPicker({ assigned, custodians, onSelect, testId, placeholder }) {
  const [open, setOpen] = useState(false);
  const selectedCustodian = custodians.find((c) => c.id === assigned?.user_id);
  const selectedLabel = selectedCustodian
    ? `${selectedCustodian.name} (${selectedCustodian.email})`
    : assigned?.user_name || "";

  const handleSelect = (userId) => {
    onSelect(userId);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={testId}
          className="h-9 w-full rounded-md border border-slate-200 bg-white px-3 text-left text-xs text-slate-700 hover:border-amber-300 hover:bg-amber-50/40 focus:outline-none focus:ring-2 focus:ring-amber-100 transition-colors flex items-center justify-between gap-2"
        >
          <span className={selectedLabel ? "truncate" : "truncate text-slate-400"}>
            {selectedLabel || placeholder}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[calc(100vw-2rem)] p-0 sm:w-[22rem]" align="start">
        <Command>
          <CommandInput placeholder="Search custodians by name or email..." />
          <CommandList>
            <CommandEmpty>No matching custodians found.</CommandEmpty>
            <CommandGroup heading="Suggested custodians">
              {custodians.map((custodian) => (
                <CommandItem
                  key={custodian.id}
                  value={`${custodian.name} ${custodian.email}`}
                  onSelect={() => handleSelect(custodian.id)}
                  className="text-xs"
                >
                  <Check
                    className={`w-3.5 h-3.5 ${
                      assigned?.user_id === custodian.id
                        ? "opacity-100"
                        : "opacity-0"
                    }`}
                  />
                  <div className="min-w-0">
                    <div className="font-medium text-slate-700 truncate">
                      {custodian.name}
                    </div>
                    <div className="text-[11px] text-slate-400 truncate">
                      {custodian.email}
                    </div>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

const NO_HEAD_VALUE = "__none__";

function DepartmentHeadSelect({ label, value, options, onChange, placeholder, testId }) {
  const currentOption = options.find((option) => option.id === value);

  return (
    <div className="flex items-center gap-2">
      <span className="w-20 flex-shrink-0 text-[11px] font-medium text-slate-500">
        {label}
      </span>
      <Select
        value={value || NO_HEAD_VALUE}
        onValueChange={(v) => onChange(v === NO_HEAD_VALUE ? "" : v)}
      >
        <SelectTrigger className="h-8 flex-1 text-xs" data-testid={testId}>
          <SelectValue placeholder={placeholder}>
            {value
              ? currentOption
                ? currentOption.name
                : "Unknown user"
              : placeholder}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_HEAD_VALUE}>
            <span className="text-slate-400">{placeholder}</span>
          </SelectItem>
          {options.map((option) => (
            <SelectItem key={option.id} value={option.id}>
              {option.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function createLocalGroupId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `group-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function DepartmentGroupsDialog({
  department,
  users,
  groups,
  onGroupsChange,
  onClose,
  onSave,
  isSaving,
}) {
  const departmentUsers = users.filter(
    (u) => u.department_id === department?.id && u.is_active !== false,
  );
  const supervisorOptions = departmentUsers.filter((u) => u.role === "supervisor");

  const updateGroup = (groupId, updates) => {
    onGroupsChange(
      groups.map((group) =>
        group.id === groupId ? { ...group, ...updates } : group,
      ),
    );
  };

  const addGroup = () => {
    onGroupsChange([
      ...groups,
      {
        id: createLocalGroupId(),
        name: "",
        supervisor_id: "",
        member_ids: [],
      },
    ]);
  };

  const removeGroup = (groupId) => {
    onGroupsChange(groups.filter((group) => group.id !== groupId));
  };

  const toggleMember = (group, memberId, checked) => {
    const currentIds = group.member_ids || [];
    updateGroup(group.id, {
      member_ids: checked
        ? [...currentIds, memberId]
        : currentIds.filter((id) => id !== memberId),
    });
  };

  return (
    <Dialog open={Boolean(department)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Department Groups</DialogTitle>
          <DialogDescription>
            Assign supervisors and one group membership per department user.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-4">
          <div className="space-y-3">
            {groups.map((group, index) => {
              const availableMembers = getAvailableDepartmentGroupMembers(
                users,
                department?.id,
                groups,
                group.id,
              );
              const selectedMembers = departmentUsers.filter((u) =>
                (group.member_ids || []).includes(u.id),
              );
              const memberOptions = Array.from(
                new Map(
                  [...selectedMembers, ...availableMembers].map((member) => [
                    member.id,
                    member,
                  ]),
                ).values(),
              );

              return (
                <div
                  key={group.id}
                  className="rounded-md border border-slate-200 bg-white p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-xs font-semibold text-slate-600">
                      Group {index + 1}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeGroup(group.id)}
                      className="h-7 px-2 text-slate-400 hover:text-red-600"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>

                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600">Group name *</Label>
                      <Input
                        value={group.name}
                        onChange={(e) => updateGroup(group.id, { name: e.target.value })}
                        className="h-9 text-sm"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-slate-600">Supervisor *</Label>
                      <Select
                        value={group.supervisor_id || ""}
                        onValueChange={(value) =>
                          updateGroup(group.id, { supervisor_id: value })
                        }
                      >
                        <SelectTrigger className="h-9 text-sm">
                          <SelectValue placeholder="Select supervisor" />
                        </SelectTrigger>
                        <SelectContent>
                          {supervisorOptions.map((supervisor) => (
                            <SelectItem key={supervisor.id} value={supervisor.id}>
                              {supervisor.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="mt-3 space-y-2">
                    <Label className="text-xs text-slate-600">Members</Label>
                    {memberOptions.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {memberOptions.map((member) => {
                          const checked = (group.member_ids || []).includes(member.id);
                          return (
                            <label
                              key={member.id}
                              className="flex items-center gap-2 rounded-md border border-slate-100 px-2 py-2 text-xs text-slate-600"
                            >
                              <Checkbox
                                checked={checked}
                                onCheckedChange={(value) =>
                                  toggleMember(group, member.id, value === true)
                                }
                              />
                              <span className="min-w-0">
                                <span className="block truncate font-medium text-slate-700">
                                  {member.name}
                                </span>
                                <span className="block truncate text-[11px] text-slate-400">
                                  {member.email}
                                </span>
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400">
                        No eligible unassigned members in this department.
                      </p>
                    )}
                  </div>
                </div>
              );
            })}

            {groups.length === 0 && (
              <div className="rounded-md border border-dashed border-slate-200 py-8 text-center text-xs text-slate-400">
                No groups configured.
              </div>
            )}
          </div>
        </ScrollArea>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            onClick={addGroup}
            className="h-9 px-3 text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            Add Group
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            className="h-9 px-3 text-xs"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onSave}
            disabled={isSaving}
            className="h-9 px-3 text-xs bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Save className="w-3.5 h-3.5 mr-1" />
            {isSaving ? "Saving..." : "Save Groups"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminPage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("users");
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [approvers, setApprovers] = useState([]);
  const [custodians, setCustodians] = useState([]);
  const [stats, setStats] = useState({});
  const latestRefreshId = useRef(0);
  const refreshTimeoutRef = useRef(null);
  const localChangesRef = useRef({
    users: new Map(),
    templates: new Map(),
    departments: new Map(),
  });

  const pruneLocalChanges = useCallback((now = Date.now()) => {
    Object.values(localChangesRef.current).forEach((changes) => {
      changes.forEach((change, id) => {
        if (now - change.changedAt > LOCAL_CHANGE_TTL_MS) {
          changes.delete(id);
        }
      });
    });
  }, []);
  const [searchQuery, setSearchQuery] = useState("");
  const isSuperAdmin = isSuperAdminRole(user?.role);
  const isManager = isManagerRole(user?.role);
  const canManageSettings = isSuperAdmin || isManager;

  // User form state
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    email: "",
    password: "",
    name: "",
    role: "requestor",
    department_id: "",
  });

  // Template approver state
  const [expandedTemplate, setExpandedTemplate] = useState(null);

  // Build / Edit form dialog
  const [showBuildFormDialog, setShowBuildFormDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [departmentForm, setDepartmentForm] = useState({
    name: "",
    code: "",
    description: "",
  });
  const [isSavingDepartment, setIsSavingDepartment] = useState(false);
  const [editingDepartmentId, setEditingDepartmentId] = useState(null);
  const [editingDepartmentForm, setEditingDepartmentForm] = useState({
    name: "",
    code: "",
    description: "",
  });
  const [isUpdatingDepartment, setIsUpdatingDepartment] = useState(false);
  const [groupDialogDepartment, setGroupDialogDepartment] = useState(null);
  const [editingGroups, setEditingGroups] = useState([]);
  const [isSavingGroups, setIsSavingGroups] = useState(false);

  const fetchAll = useCallback(async () => {
    const refreshId = latestRefreshId.current + 1;
    latestRefreshId.current = refreshId;

    try {
      const departmentParams = isManager && user?.department_id
        ? { department_id: user.department_id }
        : {};
      const [deptRes, usersRes, tmplRes, approversRes, custodiansRes, statsRes] =
        await Promise.all([
          isSuperAdmin ? listAllDepartments() : listDepartments(),
          listUsers(departmentParams),
          listAllTemplates(),
          listApprovers(departmentParams),
          listCustodians(departmentParams),
          getDashboardStats(),
        ]);
      if (refreshId !== latestRefreshId.current) {
        return;
      }

      const now = Date.now();
      pruneLocalChanges(now);
      const localUsers = Array.from(localChangesRef.current.users.values());
      const localTemplates = Array.from(localChangesRef.current.templates.values());
      const localDepartments = Array.from(localChangesRef.current.departments.values());
      const visibleDepartments = isManager
        ? deptRes.data.filter((dept) => dept.id === user?.department_id)
        : deptRes.data;
      const mergedDepartments = mergeServerItemsWithLocalChanges(
        visibleDepartments,
        localDepartments,
        { now, ttlMs: LOCAL_CHANGE_TTL_MS },
      );
      const mergedUsers = mergeServerItemsWithLocalChanges(
        usersRes.data,
        localUsers,
        { now, ttlMs: LOCAL_CHANGE_TTL_MS },
      );
      const mergedTemplates = mergeServerItemsWithLocalChanges(
        tmplRes.data,
        localTemplates,
        { now, ttlMs: LOCAL_CHANGE_TTL_MS },
      );
      const mergedApprovers = mergeServerItemsWithLocalChanges(
        approversRes.data,
        localUsers,
        { now, ttlMs: LOCAL_CHANGE_TTL_MS },
      ).filter(isApproverUser);
      const mergedCustodians = mergeServerItemsWithLocalChanges(
        custodiansRes.data,
        localUsers,
        { now, ttlMs: LOCAL_CHANGE_TTL_MS },
      ).filter(isCustodianUser);
      setDepartments(mergedDepartments);
      setUsers(mergedUsers);
      setTemplates(mergedTemplates);
      setApprovers(mergedApprovers);
      setCustodians(mergedCustodians);
      setStats({
        ...statsRes.data,
        total_users: mergedUsers.length,
        total_templates: mergedTemplates.length,
      });
    } catch (err) {
      console.error(err);
    }
  }, [isManager, isSuperAdmin, pruneLocalChanges, user?.department_id]);

  const refreshAll = useCallback(() => {
    void fetchAll();
  }, [fetchAll]);

  const scheduleRefreshAll = useCallback(() => {
    if (refreshTimeoutRef.current) {
      window.clearTimeout(refreshTimeoutRef.current);
    }
    refreshTimeoutRef.current = window.setTimeout(() => {
      refreshTimeoutRef.current = null;
      refreshAll();
    }, 400);
  }, [refreshAll]);

  const rememberLocalChange = useCallback((collection, itemOrId, deleted = false) => {
    const id = typeof itemOrId === "string" ? itemOrId : itemOrId?.id;
    if (!id) {
      return;
    }

    pruneLocalChanges();
    latestRefreshId.current += 1;
    localChangesRef.current[collection].set(id, {
      id,
      item: deleted ? null : itemOrId,
      deleted,
      changedAt: Date.now(),
    });
  }, [pruneLocalChanges]);

  const applyUserToState = useCallback((savedUser) => {
    rememberLocalChange("users", savedUser);
    setUsers((prev) => {
      const next = upsertById(prev, savedUser);
      setStats((current) => ({ ...current, total_users: next.length }));
      return next;
    });
    setApprovers((prev) =>
      isApproverUser(savedUser)
        ? upsertById(prev, savedUser)
        : removeById(prev, savedUser.id),
    );
    setCustodians((prev) =>
      isCustodianUser(savedUser)
        ? upsertById(prev, savedUser)
        : removeById(prev, savedUser.id),
    );
  }, [rememberLocalChange]);

  const removeUserFromState = useCallback((userId) => {
    rememberLocalChange("users", userId, true);
    setUsers((prev) => {
      const next = removeById(prev, userId);
      setStats((current) => ({ ...current, total_users: next.length }));
      return next;
    });
    setApprovers((prev) => removeById(prev, userId));
    setCustodians((prev) => removeById(prev, userId));
  }, [rememberLocalChange]);

  const applyTemplateToState = useCallback((savedTemplate) => {
    rememberLocalChange("templates", savedTemplate);
    setTemplates((prev) => {
      const next = upsertById(prev, savedTemplate);
      setStats((current) => ({ ...current, total_templates: next.length }));
      return next;
    });
  }, [rememberLocalChange]);

  const removeTemplateFromState = useCallback((templateId) => {
    rememberLocalChange("templates", templateId, true);
    setTemplates((prev) => {
      const next = removeById(prev, templateId);
      setStats((current) => ({ ...current, total_templates: next.length }));
      return next;
    });
  }, [rememberLocalChange]);

  useEffect(() => {
    if (!canManageSettings) {
      navigate("/");
      return;
    }
    if (isManager) {
      setActiveTab("forms");
    }
    fetchAll();
  }, [canManageSettings, isManager, navigate, fetchAll]);

  useEffect(() => () => {
    if (refreshTimeoutRef.current) {
      window.clearTimeout(refreshTimeoutRef.current);
    }
  }, []);

  useLiveUpdates({
    enabled: canManageSettings,
    onEvent: ({ event, payload }) => {
      if (shouldRefreshAdminData({ event, payload, user })) {
        scheduleRefreshAll();
      }
    },
  });

  // Reactive updates: refetch when the user returns to this tab and poll
  // periodically so admin data also catches changes made elsewhere.
  useReactiveRefresh(fetchAll, {
    intervalMs: 300000,
    refetchOnFocus: true,
    enabled: canManageSettings,
  });

  // User management
  const handleSaveUser = async () => {
    try {
      if (editingUser) {
        const updates = {
          email: userForm.email,
          name: userForm.name,
          role: userForm.role,
          department_id: userForm.department_id,
        };
        if (userForm.password) {
          updates.password = userForm.password;
        }
        const { data: savedUser } = await updateUser(editingUser.id, updates);
        applyUserToState(savedUser);
        toast.success("User updated");
      } else {
        const { data: savedUser } = await createUser(userForm);
        applyUserToState(savedUser);
        toast.success("User created");
      }
      setShowUserForm(false);
      setEditingUser(null);
      setUserForm({
        email: "",
        password: "",
        name: "",
        role: "requestor",
        department_id: "",
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save user");
    }
  };

  const handleDeleteUser = async (uid) => {
    const isApproverOnAnyTemplate = templates.some((t) =>
      (t.approver_chain || []).some((a) => a.user_id === uid),
    );
    const isCustodianOnAnyTemplate = templates.some(
      (t) => t.custodian?.user_id === uid,
    );
    if (isApproverOnAnyTemplate || isCustodianOnAnyTemplate) {
      toast.error(
        "This user is currently assigned as an approver or custodian on one or more forms. Please reassign or remove them before deleting.",
      );
      return;
    }

    if (!window.confirm("Delete this user?")) return;
    try {
      await deleteUser(uid);
      removeUserFromState(uid);
      toast.success("User deleted");
    } catch (err) {
      toast.error("Failed to delete user");
    }
  };

  const handleToggleUserActive = async (u) => {
    try {
      const { data: savedUser } = await updateUser(u.id, { is_active: !u.is_active });
      applyUserToState(savedUser);
      toast.success(u.is_active ? "User deactivated" : "User activated");
    } catch (err) {
      toast.error("Failed to update user");
    }
  };

  const handleEditUser = (u) => {
    setEditingUser(u);
    setUserForm({
      email: u.email,
      password: "",
      name: u.name,
      role: u.role,
      department_id: u.department_id,
    });
    setShowUserForm(true);
  };

  // Approver assignment
  const handleAssignApprover = async (templateId, step, userId) => {
    const tmpl = templates.find((t) => t.id === templateId);
    if (!tmpl) return;
    const specialName = getSpecialApproverLabel(userId);
    const approver = approvers.find((a) => a.id === userId);
    if (!specialName && !approver) return;
    const displayName = specialName || approver?.name || "";
    const chain = [...(tmpl.approver_chain || [])];
    const existingIdx = chain.findIndex((a) => a.step === step);
    if (existingIdx >= 0) {
      chain[existingIdx] = {
        step,
        user_id: userId,
        user_name: displayName,
      };
    } else {
      chain.push({ step, user_id: userId, user_name: displayName });
    }
    chain.sort((a, b) => a.step - b.step);
    try {
      const { data: savedTemplate } = await updateTemplate(templateId, { approver_chain: chain });
      applyTemplateToState(savedTemplate);
      toast.success("Approver assigned");
    } catch (err) {
      toast.error("Failed to assign approver");
    }
  };

  const handleRemoveApprover = async (templateId, step) => {
    const tmpl = templates.find((t) => t.id === templateId);
    if (!tmpl) return;
    let chain = (tmpl.approver_chain || []).filter((a) => a.step !== step);
    chain = chain.map((a, i) => ({ ...a, step: i + 1 }));
    try {
      const { data: savedTemplate } = await updateTemplate(templateId, { approver_chain: chain });
      applyTemplateToState(savedTemplate);
      toast.success("Approver removed");
    } catch (err) {
      toast.error("Failed to remove approver");
    }
  };

  const handleAssignCustodian = async (templateId, userId) => {
    const custodian = custodians.find((a) => a.id === userId);
    if (!custodian) return;
    try {
      const { data: savedTemplate } = await updateTemplate(templateId, {
        custodian: {
          user_id: userId,
          user_name: custodian.name || "",
        },
      });
      applyTemplateToState(savedTemplate);
      toast.success("Custodian assigned");
    } catch (err) {
      toast.error("Failed to assign custodian");
    }
  };

  const handleRemoveCustodian = async (templateId) => {
    try {
      const { data: savedTemplate } = await updateTemplate(templateId, { custodian: null });
      applyTemplateToState(savedTemplate);
      toast.success("Custodian removed");
    } catch (err) {
      toast.error("Failed to remove custodian");
    }
  };

  const handleBuildFormSubmit = async (payload, templateId) => {
    try {
      const scopedPayload = isManager
        ? { ...payload, department_id: user.department_id }
        : payload;
      if (templateId) {
        const { data: savedTemplate } = await updateTemplate(templateId, {
          name: scopedPayload.name,
          description: scopedPayload.description,
          fields: scopedPayload.fields,
        });
        applyTemplateToState(savedTemplate);
        toast.success("Form updated");
      } else {
        const { data: savedTemplate } = await createTemplate(scopedPayload);
        applyTemplateToState(savedTemplate);
        toast.success("Form created");
      }
      setShowBuildFormDialog(false);
      setEditingTemplate(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save form");
      throw err;
    }
  };

  const handleEditForm = (tmpl) => {
    setEditingTemplate(tmpl);
    setShowBuildFormDialog(true);
  };

  const handleDeleteForm = async (tmpl) => {
    if (!window.confirm(`Delete the form "${tmpl.name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await deleteTemplate(tmpl.id);
      removeTemplateFromState(tmpl.id);
      toast.success("Form deleted");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete form");
    }
  };

  const handleToggleTemplateActive = async (tmpl) => {
    const isCurrentlyActive = tmpl.is_active !== false;
    try {
      const { data: savedTemplate } = await updateTemplate(tmpl.id, {
        is_active: !isCurrentlyActive,
      });
      applyTemplateToState(savedTemplate);
      toast.success(isCurrentlyActive ? "Form disabled" : "Form enabled");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update form status");
    }
  };

  const handleDepartmentFormChange = (key, value) => {
    setDepartmentForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleEditingDepartmentFormChange = (key, value) => {
    setEditingDepartmentForm((prev) => ({ ...prev, [key]: value }));
  };

  const resetDepartmentForm = () => {
    setDepartmentForm({
      name: "",
      code: "",
      description: "",
    });
  };

  const startEditingDepartment = (dept) => {
    setEditingDepartmentId(dept.id);
    setEditingDepartmentForm({
      name: dept.name || "",
      code: dept.code || "",
      description: dept.description || "",
    });
  };

  const cancelEditingDepartment = () => {
    setEditingDepartmentId(null);
    setEditingDepartmentForm({
      name: "",
      code: "",
      description: "",
    });
  };

  const handleCreateDepartment = async () => {
    const payload = {
      name: departmentForm.name.trim(),
      code: departmentForm.code.trim().toUpperCase(),
      description: departmentForm.description.trim(),
    };

    if (!payload.name || !payload.code) {
      toast.error("Department name and code are required");
      return;
    }

    setIsSavingDepartment(true);
    try {
      const { data: savedDepartment } = await createDepartment(payload);
      rememberLocalChange("departments", savedDepartment);
      setDepartments((prev) => upsertById(prev, savedDepartment));
      toast.success("Department created");
      resetDepartmentForm();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create department");
    } finally {
      setIsSavingDepartment(false);
    }
  };

  const handleDeleteDepartment = async (dept) => {
    const deptUserCount = users.filter((u) => u.department_id === dept.id).length;
    const deptTemplateCount = templates.filter(
      (t) => t.department_id === dept.id,
    ).length;

    if (deptUserCount > 0) {
      toast.error(
        `Cannot remove ${dept.name} while ${deptUserCount} user${deptUserCount === 1 ? "" : "s"} are still assigned to it.`,
      );
      return;
    }

    if (deptTemplateCount > 0) {
      toast.error(
        `Cannot remove ${dept.name} while ${deptTemplateCount} form${deptTemplateCount === 1 ? "" : "s"} still belong to it.`,
      );
      return;
    }

    if (
      !window.confirm(
        `Remove the department "${dept.name}"? This action cannot be undone.`,
      )
    ) {
      return;
    }

    try {
      await deleteDepartment(dept.id);
      rememberLocalChange("departments", dept.id, true);
      setDepartments((prev) => removeById(prev, dept.id));
      toast.success("Department removed");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to remove department");
    }
  };

  const handleUpdateDepartment = async (deptId) => {
    const payload = {
      name: editingDepartmentForm.name.trim(),
      code: editingDepartmentForm.code.trim().toUpperCase(),
      description: editingDepartmentForm.description.trim(),
    };

    if (!payload.name || !payload.code) {
      toast.error("Department name and code are required");
      return;
    }

    setIsUpdatingDepartment(true);
    try {
      const { data: savedDepartment } = await updateDepartment(deptId, payload);
      rememberLocalChange("departments", savedDepartment);
      setDepartments((prev) => upsertById(prev, savedDepartment));
      toast.success("Department updated");
      cancelEditingDepartment();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update department");
    } finally {
      setIsUpdatingDepartment(false);
    }
  };

  const openDepartmentGroupsDialog = (dept) => {
    setGroupDialogDepartment(dept);
    setEditingGroups(
      getEditableDepartmentGroups(users, dept.id, dept.department_groups).map((group) => ({
        ...group,
        member_ids: [...(group.member_ids || [])],
      })),
    );
  };

  const closeDepartmentGroupsDialog = () => {
    setGroupDialogDepartment(null);
    setEditingGroups([]);
  };

  const handleSaveDepartmentGroups = async () => {
    if (!groupDialogDepartment) return;

    setIsSavingGroups(true);
    try {
      const { data: savedDepartment } = await updateDepartment(
        groupDialogDepartment.id,
        { department_groups: editingGroups },
      );
      rememberLocalChange("departments", savedDepartment);
      setDepartments((prev) => upsertById(prev, savedDepartment));
      toast.success("Department groups updated");
      closeDepartmentGroupsDialog();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update department groups");
    } finally {
      setIsSavingGroups(false);
    }
  };

  const handleAssignDepartmentHead = async (deptId, field, userId) => {
    try {
      const { data: savedDepartment } = await updateDepartment(deptId, {
        [field]: userId || "",
      });
      rememberLocalChange("departments", savedDepartment);
      setDepartments((prev) => upsertById(prev, savedDepartment));
      toast.success(
        field === "executive_id"
          ? "Department executive updated"
          : "Department manager updated",
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update department");
    }
  };

  const getDeptName = (id) => departments.find((d) => d.id === id)?.name || "—";

  const filteredUsers = users.filter(
    (u) =>
      !searchQuery ||
      u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const filteredTemplates = templates.filter(
    (t) =>
      (!isManager || t.department_id === user?.department_id) &&
      (!searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase())),
  );

  const visibleDepartments = isManager
    ? departments.filter((dept) => dept.id === user?.department_id)
    : departments;

  const ROLE_COLORS = {
    super_admin: "bg-purple-50 text-purple-700 border-purple-200",
    requestor: "bg-slate-100 text-slate-600 border-slate-200",
    approver: "bg-blue-50 text-blue-700 border-blue-200",
    both: "bg-emerald-50 text-emerald-700 border-emerald-200",
    supervisor: "bg-teal-50 text-teal-700 border-teal-200",
    manager: "bg-amber-50 text-amber-700 border-amber-200",
    manager_ops: "bg-amber-50 text-amber-700 border-amber-200",
    manager_sup: "bg-orange-50 text-orange-700 border-orange-200",
    executive: "bg-indigo-50 text-indigo-700 border-indigo-200",
    executive_ops: "bg-indigo-50 text-indigo-700 border-indigo-200",
    executive_sup: "bg-cyan-50 text-cyan-700 border-cyan-200",
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="admin-page">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="p-1.5 hover:bg-slate-100 rounded"
            data-testid="admin-back"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">
              {isManager ? "Manager Settings" : "Admin Panel"}
            </h1>
            <p className="text-xs text-slate-500">
              {isManager
                ? "Manage forms and assignments for your department"
                : "Manage users, forms, and approvers"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="text-center">
            <div className="text-lg font-bold text-slate-800">
              {stats.total_users || 0}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">Users</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-slate-800">
              {stats.total_templates || 0}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">Forms</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-blue-600">
              {stats.total_requests || 0}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">Requests</div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        {/* Search */}
        <div className="mb-4 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            data-testid="admin-search"
            placeholder="Search users or forms..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-10 bg-white"
          />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-white border border-slate-200 mb-6">
            {isSuperAdmin && (
              <TabsTrigger
                value="users"
                className="gap-2 text-sm"
                data-testid="tab-users"
              >
                <Users className="w-4 h-4" /> Users
              </TabsTrigger>
            )}
            <TabsTrigger
              value="forms"
              className="gap-2 text-sm"
              data-testid="tab-forms"
            >
              <FileText className="w-4 h-4" /> Form Templates & Approvers
            </TabsTrigger>
            {isSuperAdmin && (
              <TabsTrigger
                value="departments"
                className="gap-2 text-sm"
                data-testid="tab-departments"
              >
                <Building className="w-4 h-4" /> Departments
              </TabsTrigger>
            )}
          </TabsList>

          {/* USERS TAB */}
          {isSuperAdmin && (
          <TabsContent value="users">
         
              <div className="bg-white rounded-lg border border-slate-200">
                <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-800">
                    Users ({filteredUsers.length})
                  </h3>
                  <Button
                    data-testid="add-user-button"
                    onClick={() => {
                      setShowUserForm(true);
                      setEditingUser(null);
                      setUserForm({
                        email: "",
                        password: "",
                        name: "",
                        role: "requestor",
                        department_id: "",
                      });
                    }}
                    className="h-8 px-3 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" /> Add User
                  </Button>
                </div>

                {showUserForm && (
                  <div
                    className="p-4 border-b border-slate-200 bg-slate-50 animate-slide-up "
                    data-testid="user-form"
                  >
                    <div className="grid grid-cols-2 gap-3 max-w-xl">
                      <div className="space-y-1">
                        <Label className="text-xs text-slate-600">Name *</Label>
                        <Input
                          data-testid="user-name"
                          value={userForm.name}
                          onChange={(e) =>
                            setUserForm((p) => ({ ...p, name: e.target.value }))
                          }
                          className="text-sm h-9"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-slate-600">
                          Email *
                        </Label>
                        <Input
                          data-testid="user-email"
                          type="email"
                          value={userForm.email}
                          onChange={(e) =>
                            setUserForm((p) => ({
                              ...p,
                              email: e.target.value,
                            }))
                          }
                          className="text-sm h-9"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-slate-600">
                          {editingUser ? "New password" : "Password *"}
                        </Label>
                        <Input
                          data-testid="user-password"
                          type="password"
                          value={userForm.password}
                          onChange={(e) =>
                            setUserForm((p) => ({
                              ...p,
                              password: e.target.value,
                            }))
                          }
                          placeholder={editingUser ? "Leave blank to keep current password" : ""}
                          className="text-sm h-9"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-slate-600">Role *</Label>
                        <Select
                          value={userForm.role}
                          onValueChange={(v) =>
                            setUserForm((p) => ({ ...p, role: v }))
                          }
                        >
                          <SelectTrigger
                            data-testid="user-role"
                            className="text-sm h-9"
                          >
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {ROLE_OPTIONS.map((roleOption) => (
                              <SelectItem key={roleOption.value} value={roleOption.value}>
                                {roleOption.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-slate-600">
                          Department *
                        </Label>
                        <Select
                          value={userForm.department_id}
                          onValueChange={(v) =>
                            setUserForm((p) => ({ ...p, department_id: v }))
                          }
                        >
                          <SelectTrigger
                            data-testid="user-department"
                            className="text-sm h-9"
                          >
                            <SelectValue placeholder="Select dept" />
                          </SelectTrigger>
                          <SelectContent>
                            {departments.map((d) => (
                              <SelectItem key={d.id} value={d.id}>
                                {d.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-3">
                      <Button
                        data-testid="save-user"
                        onClick={handleSaveUser}
                        className="h-8 px-4 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        <Save className="w-3 h-3 mr-1" />{" "}
                        {editingUser ? "Update" : "Create"}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setShowUserForm(false);
                          setEditingUser(null);
                        }}
                        className="h-8 text-xs"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                <div className="flex-1 overflow-y-auto max-h-[32rem]">
                  <table className="w-full text-sm" data-testid="users-table">
                    <thead className="sticky top-0 bg-slate-50 border-b border-slate-100">
                      <tr>
                        <th className="text-left p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Name
                        </th>
                        <th className="text-left p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Email
                        </th>
                        <th className="text-left p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Role
                        </th>
                        <th className="text-left p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Department
                        </th>
                        <th className="text-left p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="text-right p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map((u) => (
                        <tr
                          key={u.id}
                          className="border-b border-slate-50 hover:bg-slate-50/50"
                          data-testid={`user-row-${u.id}`}
                        >
                          <td className="p-3 font-medium text-slate-800">
                            {u.name}
                          </td>
                          <td className="p-3 text-slate-500">{u.email}</td>
                          <td className="p-3">
                            <Badge
                              className={`text-[10px] ${ROLE_COLORS[u.role] || ROLE_COLORS.requestor} border`}
                            >
                              {getRoleLabel(u.role)}
                            </Badge>
                          </td>
                          <td className="p-3 text-slate-500">
                            {getDeptName(u.department_id)}
                          </td>
                          <td className="p-3">
                            <Switch
                              checked={u.is_active}
                              onCheckedChange={() => handleToggleUserActive(u)}
                              data-testid={`toggle-user-${u.id}`}
                            />
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => handleEditUser(u)}
                                className="p-1.5 hover:bg-slate-100 rounded"
                                data-testid={`edit-user-${u.id}`}
                              >
                                <Pencil className="w-3.5 h-3.5 text-slate-400" />
                              </button>
                              <button
                                onClick={() => handleDeleteUser(u.id)}
                                className="p-1.5 hover:bg-red-50 rounded"
                                data-testid={`delete-user-${u.id}`}
                              >
                                <Trash2 className="w-3.5 h-3.5 text-red-400" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            
          </TabsContent>
          )}

          {/* FORMS & APPROVERS TAB */}
          <TabsContent value="forms">
            <div className="bg-white rounded-lg border border-slate-200">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between flex-wrap gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-800">
                    Form Templates & Approver Assignment (
                    {filteredTemplates.length})
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Expand a form to assign up to {MAX_APPROVER_STEPS} sequential approvers and an optional custodian
                  </p>
                </div>
                <Button
                  data-testid="build-forms-button"
                  onClick={() => {
                    setEditingTemplate(null);
                    setShowBuildFormDialog(true);
                  }}
                  className="h-8 px-3 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Wrench className="w-3.5 h-3.5 mr-1" /> Build Forms
                </Button>
                </div>
              <div className="flex-1 overflow-y-auto max-h-[32rem]">
                {visibleDepartments.map((dept) => {
                  const deptTemplates = filteredTemplates.filter(
                    (t) => t.department_id === dept.id,
                  );
                  if (deptTemplates.length === 0) return null;
                  return (
                    <div key={dept.id}>
                      <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 sticky top-0 z-[5]">
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                          <Building className="w-3 h-3" />
                          {dept.name} ({deptTemplates.length} forms)
                        </div>
                      </div>
                      {deptTemplates.map((tmpl) => {
                        const isExpanded = expandedTemplate === tmpl.id;
                        const isTemplateActive = tmpl.is_active !== false;
                        const chain = tmpl.approver_chain || [];
                        const custodian = tmpl.custodian;
                        const selectableApprovers = approvers.filter(
                          (a) => isApproverRole(a.role) && a.is_active !== false,
                        );
                        const selectableCustodians = custodians.filter(
                          (a) => a.is_active !== false,
                        );
                        return (
                          <div
                            key={tmpl.id}
                            className={`border-b border-slate-50 ${
                              isTemplateActive ? "" : "bg-slate-50/70"
                            }`}
                          >
                            <div className="w-full flex items-center justify-between p-3 px-4 hover:bg-slate-50/50 transition-colors">
                              <button
                                data-testid={`expand-template-${tmpl.id}`}
                                className="flex-1 flex items-center justify-between text-left min-w-0"
                                onClick={() =>
                                  setExpandedTemplate(isExpanded ? null : tmpl.id)
                                }
                              >
                                <div className="flex items-center gap-3 min-w-0">
                                  <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <div
                                        className={`text-sm font-medium truncate ${
                                          isTemplateActive
                                            ? "text-slate-700"
                                            : "text-slate-400"
                                        }`}
                                      >
                                        {tmpl.name}
                                      </div>
                                      {!isTemplateActive && (
                                        <Badge className="bg-slate-100 text-slate-500 border-slate-200 text-[10px]">
                                          Disabled
                                        </Badge>
                                      )}
                                    </div>
                                    <div className="text-[10px] text-slate-400">
                                      {tmpl.fields?.length} fields ·{" "}
                                      {chain.length} approver
                                      {chain.length !== 1 ? "s" : ""}
                                      {custodian?.user_name
                                        ? ` · Custodian: ${custodian.user_name}`
                                        : ""}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                                  {chain.length > 0 && (
                                    <div className="flex -space-x-1">
                                      {chain.map((a, i) => {
                                        const specialLabel = getSpecialApproverLabel(a.user_id);
                                        return (
                                          <div
                                            key={i}
                                            className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center border-2 border-white"
                                            title={specialLabel || a.user_name}
                                          >
                                            {specialLabel
                                              ? specialLabel
                                                  .split(" ")
                                                  .map((word) => word[0])
                                                  .join("")
                                                  .slice(0, 2)
                                                  .toUpperCase()
                                              : (a.user_name?.[0] || i + 1)}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                  {isExpanded ? (
                                    <ChevronUp className="w-4 h-4 text-slate-400" />
                                  ) : (
                                    <ChevronDown className="w-4 h-4 text-slate-400" />
                                  )}
                                </div>
                              </button>
                              <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                                <div
                                  className="flex items-center gap-1.5 px-1.5"
                                  title={isTemplateActive ? "Disable form" : "Enable form"}
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <Switch
                                    checked={isTemplateActive}
                                    onCheckedChange={() =>
                                      handleToggleTemplateActive(tmpl)
                                    }
                                    data-testid={`toggle-template-active-${tmpl.id}`}
                                  />
                                  <span className="text-[10px] text-slate-400">
                                    {isTemplateActive ? "Enabled" : "Disabled"}
                                  </span>
                                </div>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleEditForm(tmpl);
                                  }}
                                  className="p-1.5 hover:bg-slate-200 rounded text-slate-500 hover:text-blue-600 transition-colors"
                                  title="Edit form"
                                  data-testid={`edit-template-${tmpl.id}`}
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteForm(tmpl);
                                  }}
                                  className="p-1.5 hover:bg-red-50 rounded text-slate-500 hover:text-red-600 transition-colors"
                                  title="Delete form"
                                  aria-label="Delete form"
                                  data-testid={`delete-template-${tmpl.id}`}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                            {isExpanded && (
                              <div className="px-4 pb-4 pt-1 bg-slate-50/50 animate-slide-up">
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between gap-3 px-1 pb-1">
                                    <p className="text-[11px] text-slate-500">
                                      Approval route
                                    </p>
                                    <Badge className="bg-blue-50 text-blue-700 border-blue-100 text-[10px]">
                                      {chain.length}/{MAX_APPROVER_STEPS} approvers
                                    </Badge>
                                  </div>
                                  {APPROVER_STEPS.map((step) => {
                                    const assigned = chain.find(
                                      (a) => a.step === step,
                                    );
                                    return (
                                      <div
                                        key={step}
                                        className="flex items-center gap-3 p-2 bg-white rounded-md border border-slate-100"
                                      >
                                        <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-600 text-xs font-bold flex items-center justify-center flex-shrink-0">
                                          {step}
                                        </div>
                                        <div className="flex-1">
                                          <ApproverPicker
                                            assigned={assigned}
                                            approvers={selectableApprovers}
                                            placeholder={`Step ${step} approver (optional)`}
                                            testId={`approver-step-${step}-${tmpl.id}`}
                                            onSelect={(v) =>
                                              handleAssignApprover(
                                                tmpl.id,
                                                step,
                                                v,
                                              )
                                            }
                                          />
                                        </div>
                                        {assigned && (
                                          <button
                                            onClick={() =>
                                              handleRemoveApprover(
                                                tmpl.id,
                                                step,
                                              )
                                            }
                                            className="p-1 hover:bg-red-50 rounded"
                                            data-testid={`remove-approver-${step}-${tmpl.id}`}
                                          >
                                            <X className="w-3.5 h-3.5 text-red-400" />
                                          </button>
                                        )}
                                      </div>
                                    );
                                  })}
                                  <div className="flex items-center gap-3 p-2 bg-white rounded-md border border-slate-100">
                                    <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                                      C
                                    </div>
                                    <div className="flex-1">
                                      <CustodianPicker
                                        assigned={custodian}
                                        custodians={selectableCustodians}
                                        placeholder="Custodian (optional)"
                                        testId={`custodian-${tmpl.id}`}
                                        onSelect={(v) =>
                                          handleAssignCustodian(tmpl.id, v)
                                        }
                                      />
                                    </div>
                                    {custodian && (
                                      <button
                                        onClick={() =>
                                          handleRemoveCustodian(tmpl.id)
                                        }
                                        className="p-1 hover:bg-red-50 rounded"
                                        data-testid={`remove-custodian-${tmpl.id}`}
                                      >
                                        <X className="w-3.5 h-3.5 text-red-400" />
                                      </button>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </TabsContent>

          {/* DEPARTMENTS TAB */}
          {isSuperAdmin && (
          <TabsContent value="departments">
            <div className="bg-white rounded-lg border border-slate-200">
              <div className="p-4 border-b border-slate-100 flex items-start justify-between gap-6 flex-wrap">
                <div>
                  <h3 className="text-sm font-semibold text-slate-800">
                    Departments ({departments.length})
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Add departments here, and remove them only when they no longer have users or forms.
                  </p>
                </div>
                <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-600">Department name *</Label>
                    <Input
                      value={departmentForm.name}
                      onChange={(e) =>
                        handleDepartmentFormChange("name", e.target.value)
                      }
                      placeholder="e.g. Human Resources"
                      className="h-9 text-sm"
                      data-testid="department-name"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs text-slate-600">Department code *</Label>
                    <Input
                      value={departmentForm.code}
                      onChange={(e) =>
                        handleDepartmentFormChange(
                          "code",
                          e.target.value.toUpperCase(),
                        )
                      }
                      placeholder="e.g. HR"
                      className="h-9 text-sm uppercase"
                      data-testid="department-code"
                    />
                  </div>
                  <div className="space-y-1 md:col-span-2">
                    <Label className="text-xs text-slate-600">Description</Label>
                    <Textarea
                      value={departmentForm.description}
                      onChange={(e) =>
                        handleDepartmentFormChange("description", e.target.value)
                      }
                      placeholder="Optional description for admins"
                      className="text-sm min-h-[84px]"
                      data-testid="department-description"
                    />
                  </div>
                  <div className="md:col-span-2 flex justify-end">
                    <Button
                      onClick={handleCreateDepartment}
                      disabled={isSavingDepartment}
                      className="h-9 px-4 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                      data-testid="add-department-button"
                    >
                      <Plus className="w-3.5 h-3.5 mr-1" />
                      {isSavingDepartment ? "Saving..." : "Add Department"}
                    </Button>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
                {departments.map((dept) => {
                  const deptTemplateCount = templates.filter(
                    (t) => t.department_id === dept.id,
                  ).length;
                  const deptUserCount = users.filter(
                    (u) => u.department_id === dept.id,
                  ).length;
                  const cannotDelete = deptUserCount > 0 || deptTemplateCount > 0;
                  const isEditingDepartment = editingDepartmentId === dept.id;
                  const executiveOptions = users.filter(
                    (u) => isExecutiveRole(u.role) && u.is_active !== false,
                  );
                  // A manager can head only one department; hide managers
                  // already assigned elsewhere.
                  const managerOptions = users.filter(
                    (u) =>
                      isManagerRole(u.role) &&
                      u.is_active !== false &&
                      !departments.some(
                        (d) => d.id !== dept.id && d.manager_id === u.id,
                      ),
                  );
                  return (
                    <div
                      key={dept.id}
                      data-testid={`dept-card-${dept.code}`}
                      className="p-4 border border-slate-200 rounded-lg hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        {isEditingDepartment ? (
                          <div className="w-full space-y-3">
                            <div className="space-y-1">
                              <Label className="text-xs text-slate-600">Department name *</Label>
                              <Input
                                value={editingDepartmentForm.name}
                                onChange={(e) =>
                                  handleEditingDepartmentFormChange(
                                    "name",
                                    e.target.value,
                                  )
                                }
                                className="h-9 text-sm"
                                data-testid={`edit-department-name-${dept.id}`}
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-slate-600">Department code *</Label>
                              <Input
                                value={editingDepartmentForm.code}
                                onChange={(e) =>
                                  handleEditingDepartmentFormChange(
                                    "code",
                                    e.target.value.toUpperCase(),
                                  )
                                }
                                className="h-9 text-sm uppercase"
                                data-testid={`edit-department-code-${dept.id}`}
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs text-slate-600">Description</Label>
                              <Textarea
                                value={editingDepartmentForm.description}
                                onChange={(e) =>
                                  handleEditingDepartmentFormChange(
                                    "description",
                                    e.target.value,
                                  )
                                }
                                className="text-sm min-h-[96px]"
                                data-testid={`edit-department-description-${dept.id}`}
                              />
                            </div>
                            <div className="flex justify-end gap-2">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => openDepartmentGroupsDialog(dept)}
                                className="h-8 px-3 text-xs"
                                data-testid={`department-groups-${dept.id}`}
                              >
                                <Users className="w-3.5 h-3.5 mr-1" />
                                Groups
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingDepartment}
                                className="h-8 px-3 text-xs"
                              >
                                Cancel
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                onClick={() => handleUpdateDepartment(dept.id)}
                                disabled={isUpdatingDepartment}
                                className="h-8 px-3 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                                data-testid={`save-department-${dept.id}`}
                              >
                                <Save className="w-3.5 h-3.5 mr-1" />
                                {isUpdatingDepartment ? "Saving..." : "Save"}
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div>
                              <h4 className="text-sm font-semibold text-slate-800">
                                {dept.name}
                              </h4>
                              <span className="inline-flex mt-1 font-mono text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                                {dept.code}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => startEditingDepartment(dept)}
                                className="h-8 px-2 text-slate-400 hover:text-blue-600"
                                data-testid={`edit-department-${dept.id}`}
                                title="Edit department"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteDepartment(dept)}
                                disabled={cannotDelete}
                                className="h-8 px-2 text-slate-400 hover:text-red-600 disabled:text-slate-300"
                                data-testid={`delete-department-${dept.id}`}
                                title={
                                  deptUserCount > 0
                                    ? "Remove users from this department before deleting it."
                                    : deptTemplateCount > 0
                                      ? "Remove this department's forms before deleting it."
                                      : "Remove department"
                                }
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            </div>
                          </>
                        )}
                      </div>
                      {!isEditingDepartment && (
                        <>
                          <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                            {dept.description || "No description provided."}
                          </p>
                          <div className="space-y-2 mb-3">
                            <DepartmentHeadSelect
                              label="Executive"
                              value={dept.executive_id || ""}
                              options={executiveOptions}
                              placeholder="No executive assigned"
                              testId={`dept-executive-${dept.id}`}
                              onChange={(v) =>
                                handleAssignDepartmentHead(dept.id, "executive_id", v)
                              }
                            />
                            <DepartmentHeadSelect
                              label="Manager"
                              value={dept.manager_id || ""}
                              options={managerOptions}
                              placeholder="No manager assigned"
                              testId={`dept-manager-${dept.id}`}
                              onChange={(v) =>
                                handleAssignDepartmentHead(dept.id, "manager_id", v)
                              }
                            />
                            {!dept.executive_id && (
                              <p className="text-[11px] text-amber-600">
                                Assign an executive — Executive and Immediate Head
                                approval steps need one.
                              </p>
                            )}
                          </div>
                          <div className="flex gap-4 text-xs text-slate-500">
                            <span>{deptTemplateCount} forms</span>
                            <span>{deptUserCount} users</span>
                            <span>{(dept.department_groups || []).length} groups</span>
                          </div>
                          {cannotDelete && (
                            <p className="mt-3 text-[11px] text-amber-600">
                              {deptUserCount > 0
                                ? "Users are still assigned to this department."
                                : "Forms are still assigned to this department."}
                            </p>
                          )}
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </TabsContent>
          )}
        </Tabs>
      </div>

      {showBuildFormDialog && (
        <BuildFormDialog
          departments={visibleDepartments}
          onClose={() => {
            setShowBuildFormDialog(false);
            setEditingTemplate(null);
          }}
          onSubmit={handleBuildFormSubmit}
          initialTemplate={editingTemplate}
          lockedDepartmentId={isManager ? user?.department_id : null}
        />
      )}

      {groupDialogDepartment && (
        <DepartmentGroupsDialog
          department={groupDialogDepartment}
          users={users}
          groups={editingGroups}
          onGroupsChange={setEditingGroups}
          onClose={closeDepartmentGroupsDialog}
          onSave={handleSaveDepartmentGroups}
          isSaving={isSavingGroups}
        />
      )}
    </div>
  );
}
