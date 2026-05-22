import React, { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { changePassword } from "@/lib/api";

export default function ChangePasswordDialog({ user, open, onOpenChange }) {
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [saving, setSaving] = useState(false);

  const resetForm = () => {
    setForm({
      current_password: "",
      new_password: "",
      confirm_password: "",
    });
  };

  const handleOpenChange = (nextOpen) => {
    if (!nextOpen) {
      resetForm();
    }
    onOpenChange?.(nextOpen);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (form.new_password !== form.confirm_password) {
      toast.error("New passwords do not match");
      return;
    }

    if (form.new_password.length < 6) {
      toast.error("New password must be at least 6 characters");
      return;
    }

    setSaving(true);
    try {
      await changePassword(user.id, {
        current_password: form.current_password,
        new_password: form.new_password,
      });
      toast.success("Password changed successfully");
      handleOpenChange(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to change password");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="w-[calc(100vw-2rem)] max-w-md border-slate-200 bg-white">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Change password</DialogTitle>
            <DialogDescription>
              Update the password for your account.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600" htmlFor="current-password">
                Current password
              </label>
              <Input
                id="current-password"
                data-testid="current-password"
                type="password"
                value={form.current_password}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, current_password: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600" htmlFor="new-password">
                New password
              </label>
              <Input
                id="new-password"
                data-testid="new-password"
                type="password"
                value={form.new_password}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, new_password: e.target.value }))
                }
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600" htmlFor="confirm-password">
                Confirm new password
              </label>
              <Input
                id="confirm-password"
                data-testid="confirm-password"
                type="password"
                value={form.confirm_password}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, confirm_password: e.target.value }))
                }
                required
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700">
              {saving ? "Saving..." : "Save password"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
