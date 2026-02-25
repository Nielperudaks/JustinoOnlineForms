import React, { useState, useEffect } from "react";
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
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Plus, Trash2, FileText, Building } from "lucide-react";

const FIELD_TYPES = [
  { value: "text", label: "Text" },
  { value: "textarea", label: "Text area" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "select", label: "Dropdown (select)" },
  { value: "table", label: "Table" },
  { value: "dropzone", label: "File dropzone" },
];

function slugify(str) {
  return (str || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "");
}

export default function BuildFormDialog({
  departments,
  onClose,
  onSubmit,
  initialTemplate = null,
}) {
  const isEdit = !!initialTemplate;

  const [department_id, setDepartment_id] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fields, setFields] = useState([
    { name: "field_1", label: "Field 1", type: "text", required: true, options: null, table_title: "", column_headers: null, num_rows: 3 },
  ]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initialTemplate) {
      setDepartment_id(initialTemplate.department_id || "");
      setName(initialTemplate.name || "");
      setDescription(initialTemplate.description || "");
      setFields(
        (initialTemplate.fields || []).length > 0
          ? initialTemplate.fields.map((f) => ({
              name: f.name,
              label: f.label || f.name,
              type: f.type || "text",
              required: f.required !== false,
              options: f.options && f.options.length ? f.options : null,
              table_title: f.table_title || "",
              column_headers: f.column_headers && f.column_headers.length ? f.column_headers : null,
              num_rows: typeof f.num_rows === "number" ? f.num_rows : 3,
            }))
          : [{ name: "field_1", label: "Field 1", type: "text", required: true, options: null, table_title: "", column_headers: null, num_rows: 3 }]
      );
    } else if (departments.length && !department_id) {
      setDepartment_id(departments[0].id);
    }
  }, [initialTemplate, departments, department_id]);

  const addField = () => {
    const idx = fields.length + 1;
    setFields((prev) => [
      ...prev,
      {
        name: `field_${idx}`,
        label: `Field ${idx}`,
        type: "text",
        required: true,
        options: null,
        table_title: "",
        column_headers: null,
        num_rows: 3,
      },
    ]);
  };

  const removeField = (index) => {
    if (fields.length <= 1) return;
    setFields((prev) => prev.filter((_, i) => i !== index));
  };

  const updateField = (index, key, value) => {
    setFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [key]: value };
      if (key === "label") {
        next[index].name = slugify(value) || next[index].name;
      }
      // if (key === "column_headers" && typeof value === "string") {
      //   next[index].column_headers = value.split(",").map((s) => s.trim()).filter(Boolean);
      // }
      return next;
    });
  };

  const buildPayload = () => {
    const fieldPayload = fields.map((f) => {
      const out = {
        name: f.name || slugify(f.label) || `field_${fields.indexOf(f) + 1}`,
        label: (f.label || f.name).trim() || "Field",
        type: f.type || "text",
        required: f.required !== false,
      };
      if (f.type === "select" && f.options) {
        const opts =
          typeof f.options === "string"
            ? f.options.split("\n").map((s) => s.trim()).filter(Boolean)
            : Array.isArray(f.options)
              ? f.options
              : [];
        out.options = opts.length ? opts : ["Option 1", "Option 2"];
      }
      if (f.type === "table") {
        out.table_title = (f.table_title || "").trim();
        const tbl =
          typeof f.column_headers === "string"
            ? f.column_headers.split("\n").map((s) => s.trim()).filter(Boolean)
            : Array.isArray(f.column_headers)
              ? f.column_headers
              : [];
        out.column_headers = tbl.length ? tbl : ["Header 1", "Header 2"];
        out.num_rows = Number.isInteger(f.num_rows) ? f.num_rows : 3;
      }
      return out;
    });

    return {
      department_id: department_id || (departments[0]?.id ?? ""),
      name: name.trim(),
      description: (description || "").trim(),
      fields: fieldPayload,
    };
  };

  const handleSubmit = async () => {
    if (!name.trim()) return;
    const payload = buildPayload();
    if (!payload.fields.length) return;
    setSubmitting(true);
    try {
      await onSubmit(payload, isEdit ? initialTemplate.id : null);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      data-testid="build-form-dialog"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-slide-up mx-4">
        <div className="flex items-center justify-between p-5 border-b border-slate-200 flex-shrink-0">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              {isEdit ? "Edit Form" : "Build Form"}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {isEdit
                ? "Update form name, department, and fields"
                : "Choose department, name the form, and add fields"}
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-md">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <ScrollArea className="flex-1 overflow-y-auto min-h-0">
          <div className="p-5 space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-slate-700">Department *</Label>
              <Select
                value={department_id}
                onValueChange={setDepartment_id}
                disabled={isEdit}
              >
                <SelectTrigger data-testid="build-form-department" className="text-sm">
                  <SelectValue placeholder="Select department" />
                </SelectTrigger>
                <SelectContent>
                  {departments.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      <span className="flex items-center gap-2">
                        <Building className="w-3.5 h-3.5 text-slate-400" />
                        {d.name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-slate-700">Form name *</Label>
              <Input
                data-testid="build-form-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Office Supplies Request"
                className="text-sm"
              />
            </div>

            <div className="space-y-2 flex flex-col gap-2">
              <Label className="text-sm font-medium text-slate-700">Description (optional)</Label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of the form"
                className="text-sm"
                rows={3}
              />
            </div>

            <div className="border-t border-slate-100 pt-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Form fields
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addField}
                  className="h-8 text-xs"
                  data-testid="build-form-add-field"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add field
                </Button>
              </div>

              <div className="space-y-3">
                {fields.map((field, index) => (
                  <div
                    key={index}
                    className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-2"
                    data-testid={`build-form-field-${index}`}
                  >
                    <div className="flex gap-2 flex-wrap items-end">
                      <div className="flex-1 min-w-[120px] space-y-1">
                        <Label className="text-xs text-slate-500">Label</Label>
                        <Input
                          value={field.label}
                          onChange={(e) => updateField(index, "label", e.target.value)}
                          placeholder="Field label"
                          className="text-sm h-8"
                        />
                      </div>
                      <div className="w-[130px] space-y-1">
                        <Label className="text-xs text-slate-500">Type</Label>
                        <Select
                          value={field.type}
                          onValueChange={(v) => updateField(index, "type", v)}
                        >
                          <SelectTrigger className="text-sm h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {FIELD_TYPES.map((t) => (
                              <SelectItem key={t.value} value={t.value}>
                                {t.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <label className="flex items-center gap-1.5 h-8 text-xs text-slate-600 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={field.required}
                          onChange={(e) => updateField(index, "required", e.target.checked)}
                          className="rounded border-slate-300"
                        />
                        Required
                      </label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeField(index)}
                        disabled={fields.length <= 1}
                        className="h-8 w-8 p-0 text-slate-400 hover:text-red-600"
                        data-testid={`build-form-remove-field-${index}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                    {field.type === "select" && (
                      <div className="space-y-1">
                        <Label className="text-xs text-slate-500">
                          Options (one per line; commas allowed in text)
                        </Label>
                        <Textarea
                          value={
                            Array.isArray(field.options)
                              ? field.options.join("\n")
                              : typeof field.options === "string"
                                ? field.options
                                : ""
                          }
                          onChange={(e) =>
                            updateField(index, "options", e.target.value)
                          }
                          placeholder={"Option 1\nOption 2\nOption 3"}
                          className="flex min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          rows={3}
                        />
                      </div>
                    )}
                    {field.type === "table" && (
                      <div className="space-y-3 pt-1">
                        <div className="space-y-1">
                          <Label className="text-xs text-slate-500">Table title</Label>
                          <Input
                            value={field.table_title || ""}
                            onChange={(e) => updateField(index, "table_title", e.target.value)}
                            placeholder="e.g. Budget Breakdown"
                            className="text-sm h-8"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-slate-500">Column headers (one per line; commas allowed in text)</Label>
                          <Textarea
                            value={
                              Array.isArray(field.column_headers)
                                ? field.column_headers.join("\n")
                                : typeof field.column_headers === "string"
                                  ? field.column_headers
                                  : ""
                            }
                            onChange={(e) => updateField(index, "column_headers", e.target.value)}
                            placeholder={"Header 1\nHeader 2\nHeader 3\n..."}
                            className="text-sm h-8"
                            rows={4}
                          />
                        </div>
                        <div className="space-y-1 w-24">
                          <Label className="text-xs text-slate-500">Number of rows</Label>
                          <Input
                            type="number"
                            min={1}
                            max={50}
                            value={field.num_rows ?? 3}
                            onChange={(e) => updateField(index, "num_rows", parseInt(e.target.value, 10))}
                            className="text-sm h-8"
                          />
                        </div>
                      </div>
                    )}
                    {field.type === "dropzone" && (
                      <div className="text-xs text-slate-500 pt-1">
                        Accepts: images, PDF, Excel, Word. Max 2MB per file.
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ScrollArea>

        <div className="p-4 border-t border-slate-200 flex items-center justify-end gap-2 flex-shrink-0">
          <Button variant="outline" onClick={onClose} className="text-sm">
            Cancel
          </Button>
          <Button
            data-testid="build-form-submit"
            onClick={handleSubmit}
            disabled={!name.trim() || fields.length === 0 || submitting}
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
          >
            {submitting ? "Saving..." : isEdit ? "Update Form" : "Create Form"}
          </Button>
        </div>
      </div>
    </div>
  );
}
