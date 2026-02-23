import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/store";
import { useReactiveRefresh } from "@/hooks/useReactiveRefresh";
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  listAllDepartments,
  listAllTemplates,
  updateTemplate,
  createTemplate,
  deleteTemplate,
  listApprovers,
  getDashboardStats,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
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
  ChevronDown,
  ChevronUp,
  Search,
  Wrench,
} from "lucide-react";

export default function AdminPage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("users");
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [approvers, setApprovers] = useState([]);
  const [stats, setStats] = useState({});
  const [searchQuery, setSearchQuery] = useState("");

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

  const fetchAll = useCallback(async () => {
    try {
      const [deptRes, usersRes, tmplRes, approversRes, statsRes] =
        await Promise.all([
          listAllDepartments(),
          listUsers({}),
          listAllTemplates(),
          listApprovers({}),
          getDashboardStats(),
        ]);
      setDepartments(deptRes.data);
      setUsers(usersRes.data);
      setTemplates(tmplRes.data);
      setApprovers(approversRes.data);
      setStats(statsRes.data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    if (user?.role !== "super_admin") {
      navigate("/");
      return;
    }
    fetchAll();
  }, [user, navigate, fetchAll]);

  // Reactive updates: poll and refetch when user returns to tab so stats
  // and lists update when other admins or users make changes.
  // useReactiveRefresh(fetchAll, {
  //   intervalMs: 30000,
  //   refetchOnFocus: true,
  //   enabled: user?.role === "super_admin",
  // });

  // User management
  const handleSaveUser = async () => {
    try {
      if (editingUser) {
        const updates = {
          name: userForm.name,
          role: userForm.role,
          department_id: userForm.department_id,
        };
        await updateUser(editingUser.id, updates);
        toast.success("User updated");
      } else {
        await createUser(userForm);
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
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to save user");
    }
  };

  const handleDeleteUser = async (uid) => {
    if (!window.confirm("Delete this user?")) return;
    try {
      await deleteUser(uid);
      toast.success("User deleted");
      fetchAll();
    } catch (err) {
      toast.error("Failed to delete user");
    }
  };

  const handleToggleUserActive = async (u) => {
    try {
      await updateUser(u.id, { is_active: !u.is_active });
      toast.success(u.is_active ? "User deactivated" : "User activated");
      fetchAll();
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
    const approver = approvers.find((a) => a.id === userId);
    const chain = [...(tmpl.approver_chain || [])];
    const existingIdx = chain.findIndex((a) => a.step === step);
    if (existingIdx >= 0) {
      chain[existingIdx] = {
        step,
        user_id: userId,
        user_name: approver?.name || "",
      };
    } else {
      chain.push({ step, user_id: userId, user_name: approver?.name || "" });
    }
    chain.sort((a, b) => a.step - b.step);
    try {
      await updateTemplate(templateId, { approver_chain: chain });
      toast.success("Approver assigned");
      fetchAll();
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
      await updateTemplate(templateId, { approver_chain: chain });
      toast.success("Approver removed");
      fetchAll();
    } catch (err) {
      toast.error("Failed to remove approver");
    }
  };

  const handleBuildFormSubmit = async (payload, templateId) => {
    try {
      if (templateId) {
        await updateTemplate(templateId, {
          name: payload.name,
          description: payload.description,
          fields: payload.fields,
        });
        toast.success("Form updated");
      } else {
        await createTemplate(payload);
        toast.success("Form created");
      }
      setShowBuildFormDialog(false);
      setEditingTemplate(null);
      fetchAll();
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
    const confirmed = window.confirm(
      `This will permanently delete the form "${tmpl.name}".\n\n` +
        "- It will no longer be available for new requests.\n" +
        "- You cannot undo this action.\n" +
        "- Forms with pending or active requests cannot be deleted.\n\n" +
        "Do you want to permanently delete this form?"
    );
    if (!confirmed) return;

    try {
      await deleteTemplate(tmpl.id);
      toast.success("Form deleted");
      setExpandedTemplate((prev) => (prev === tmpl.id ? null : prev));
      fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete form");
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
      !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const ROLE_COLORS = {
    super_admin: "bg-purple-50 text-purple-700 border-purple-200",
    requestor: "bg-slate-100 text-slate-600 border-slate-200",
    approver: "bg-blue-50 text-blue-700 border-blue-200",
    both: "bg-emerald-50 text-emerald-700 border-emerald-200",
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
              Admin Panel
            </h1>
            <p className="text-xs text-slate-500">
              Manage users, forms, and approvers
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
            <TabsTrigger
              value="users"
              className="gap-2 text-sm"
              data-testid="tab-users"
            >
              <Users className="w-4 h-4" /> Users
            </TabsTrigger>
            <TabsTrigger
              value="forms"
              className="gap-2 text-sm"
              data-testid="tab-forms"
            >
              <FileText className="w-4 h-4" /> Form Templates & Approvers
            </TabsTrigger>
            <TabsTrigger
              value="departments"
              className="gap-2 text-sm"
              data-testid="tab-departments"
            >
              <Building className="w-4 h-4" /> Departments
            </TabsTrigger>
          </TabsList>

          {/* USERS TAB */}
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
                          disabled={!!editingUser}
                        />
                      </div>
                      {!editingUser && (
                        <div className="space-y-1">
                          <Label className="text-xs text-slate-600">
                            Password *
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
                            className="text-sm h-9"
                          />
                        </div>
                      )}
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
                            <SelectItem value="requestor">Requestor</SelectItem>
                            <SelectItem value="approver">Approver</SelectItem>
                            <SelectItem value="both">Both</SelectItem>
                            <SelectItem value="super_admin">
                              Super Admin
                            </SelectItem>
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
                              className={`text-[10px] ${ROLE_COLORS[u.role] || ROLE_COLORS.requestor} border capitalize`}
                            >
                              {u.role?.replace("_", " ")}
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
                    Expand a form to assign up to 3 sequential approvers
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
                {departments.map((dept) => {
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
                        const chain = tmpl.approver_chain || [];
                        return (
                          <div
                            key={tmpl.id}
                            className="border-b border-slate-50"
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
                                    <div className="text-sm font-medium text-slate-700">
                                      {tmpl.name}
                                    </div>
                                    <div className="text-[10px] text-slate-400">
                                      {tmpl.fields?.length} fields ·{" "}
                                      {chain.length} approver
                                      {chain.length !== 1 ? "s" : ""}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                                  {chain.length > 0 && (
                                    <div className="flex -space-x-1">
                                      {chain.map((a, i) => (
                                        <div
                                          key={i}
                                          className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center border-2 border-white"
                                        >
                                          {a.user_name?.[0] || i + 1}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  {isExpanded ? (
                                    <ChevronUp className="w-4 h-4 text-slate-400" />
                                  ) : (
                                    <ChevronDown className="w-4 h-4 text-slate-400" />
                                  )}
                                </div>
                              </button>
                              <div className="flex items-center gap-0.5 flex-shrink-0 ml-2">
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
                                  className="p-1.5 hover:bg-slate-200 rounded text-slate-500 hover:text-red-600 transition-colors"
                                  title="Deactivate form"
                                  data-testid={`delete-template-${tmpl.id}`}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                            {isExpanded && (
                              <div className="px-4 pb-4 pt-1 bg-slate-50/50 animate-slide-up">
                                <div className="space-y-2">
                                  {[1, 2, 3].map((step) => {
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
                                          <Select
                                            value={assigned?.user_id || ""}
                                            onValueChange={(v) =>
                                              handleAssignApprover(
                                                tmpl.id,
                                                step,
                                                v,
                                              )
                                            }
                                          >
                                            <SelectTrigger
                                              data-testid={`approver-step-${step}-${tmpl.id}`}
                                              className="h-8 text-xs border-slate-200"
                                            >
                                              <SelectValue
                                                placeholder={`Step ${step} approver (optional)`}
                                              />
                                            </SelectTrigger>
                                            <SelectContent>
                                              {approvers.map((a) => (
                                                <SelectItem
                                                  key={a.id}
                                                  value={a.id}
                                                >
                                                  {a.name} ({a.email})
                                                </SelectItem>
                                              ))}
                                            </SelectContent>
                                          </Select>
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
          <TabsContent value="departments">
            <div className="bg-white rounded-lg border border-slate-200">
              <div className="p-4 border-b border-slate-100">
                <h3 className="text-sm font-semibold text-slate-800">
                  Departments ({departments.length})
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
                {departments.map((dept) => {
                  const deptTemplateCount = templates.filter(
                    (t) => t.department_id === dept.id,
                  ).length;
                  const deptUserCount = users.filter(
                    (u) => u.department_id === dept.id,
                  ).length;
                  return (
                    <div
                      key={dept.id}
                      data-testid={`dept-card-${dept.code}`}
                      className="p-4 border border-slate-200 rounded-lg hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold text-slate-800">
                          {dept.name}
                        </h4>
                        <span className="font-mono text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                          {dept.code}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                        {dept.description}
                      </p>
                      <div className="flex gap-4 text-xs text-slate-500">
                        <span>{deptTemplateCount} forms</span>
                        <span>{deptUserCount} users</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {showBuildFormDialog && (
        <BuildFormDialog
          departments={departments}
          onClose={() => {
            setShowBuildFormDialog(false);
            setEditingTemplate(null);
          }}
          onSubmit={handleBuildFormSubmit}
          initialTemplate={editingTemplate}
        />
      )}
    </div>
  );
}
