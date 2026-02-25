import React, { useState, useCallback, useEffect, useRef } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { X, FileText, ChevronRight, Upload, File } from "lucide-react";

const DROPZONE_MAX_SIZE = 2 * 1024 * 1024; // 2MB
const ALLOWED_EXTENSIONS = /\.(png|jpg|jpeg|gif|webp|pdf|xls|xlsx|doc|docx)$/i;


function DropzoneInput({ value, onFile, fieldName, required, accept, maxSize, allowedExtensions }) {
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const inputRef = React.useRef(null);

  const validateAndSet = (file) => {
    setError("");
    if (!file) return;
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
    if (!allowedExtensions.test(ext)) {
      setError("Allowed: images, PDF, Excel, Word only");
      return;
    }
    if (file.size > maxSize) {
      setError("File must be 2MB or less");
      return;
    }
    onFile(fieldName, file);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) validateAndSet(f);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDrag(true);
  };

  const onDragLeave = () => setDrag(false);

  const onInputChange = (e) => {
    const f = e.target?.files?.[0];
    if (f) validateAndSet(f);
    e.target.value = "";
  };

 

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          drag ? "border-blue-400 bg-blue-50/50" : "border-slate-200 hover:border-slate-300"
        } ${error ? "border-red-300 bg-red-50/30" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={onInputChange}
          className="hidden"
          data-testid={`field-${fieldName}`}
        />
        {value ? (
          <div className="flex items-center justify-center gap-2 text-sm text-slate-700">
            <File className="w-4 h-4 text-slate-500" />
            {value.filename}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 text-slate-500">
            <Upload className="w-8 h-8 text-slate-400" />
            <span className="text-sm">Drop file here or click to upload</span>
            <span className="text-xs">Images, PDF, Excel, Word • Max 2MB</span>
          </div>
        )}
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export default function CreateRequestDialog({
  templates,
  departments,
  onSubmit,
  onClose,
}) {
  const [step, setStep] = useState(1); // 1: select dept, 2: select form, 3: fill form
  const [selectedDeptId, setSelectedDeptId] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [title, setTitle] = useState("");
  const [formData, setFormData] = useState({});
  const [notes, setNotes] = useState("");
  const [priority, setPriority] = useState("normal");
  const [submitting, setSubmitting] = useState(false);


  const filteredTemplates = templates.filter(
    (t) => !selectedDeptId || t.department_id === selectedDeptId,
  );

  const deptName = departments.find((d) => d.id === selectedDeptId)?.name || "";
  


  const handleSelectTemplate = (tmpl) => {
    setSelectedTemplate(tmpl);
    setTitle("");
    const initial = {};
    tmpl.fields.forEach((f) => {
      if (f.type === "table") {
        const headers = f.column_headers || [];
        const numRows = Math.max(1, Math.min(50, f.num_rows || 3));
        const rows = Array.from({ length: numRows }, () =>
          headers.map(() => ""),
        );
        initial[f.name] = {
          title: f.table_title || "",
          headers,
          rows,
        };
      } else if (f.type === "dropzone") {
        initial[f.name] = null;
      } else {
        initial[f.name] = "";
      }
    });
    setFormData(initial);
    setStep(3);
  };

  const validateForm = () => {
    if (!selectedTemplate || !title.trim()) return false;
    for (const f of selectedTemplate.fields) {
      if (!f.required) continue;
      const val = formData[f.name];
      if (f.type === "table") {
        const hasContent = val?.rows?.some((row) =>
          row?.some((cell) => String(cell || "").trim()),
        );
        if (!hasContent) return false;
      } else if (f.type === "dropzone") {
        if (val == null) return false;
      } else if (val == null || String(val || "").trim() === "") {
        return false;
      }
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    await onSubmit({
      form_template_id: selectedTemplate.id,
      title: title.trim(),
      form_data: formData,
      notes,
      priority,
    });
    setSubmitting(false);
  };

  const updateTableCell = useCallback(
    (fieldName, rowIdx, colIdx, value) => {
      setFormData((prev) => {
        const tbl = prev[fieldName];
        if (!tbl?.rows) return prev;
        const rows = tbl.rows.map((r, ri) =>
          ri === rowIdx ? r.map((c, ci) => (ci === colIdx ? value : c)) : r,
        );
        return { ...prev, [fieldName]: { ...tbl, rows } };
      });
    },
    [],
  );

  const handleFileDrop = useCallback(
    (fieldName, file) => {
      if (!file) return;
      const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
      if (!ALLOWED_EXTENSIONS.test(ext)) {
        return; // invalid type - will show error
      }
      if (file.size > DROPZONE_MAX_SIZE) {
        return; // too large
      }
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result;
        setFormData((prev) => ({
          ...prev,
          [fieldName]: {
            filename: file.name,
            base64: base64.split(",")[1] || base64,
            mimeType: file.type,
          },
        }));
      };
      reader.readAsDataURL(file);
    },
    [],
  );

  const renderFieldInput = (field) => {
    const val = formData[field.name] ?? "";
    const onChange = (v) =>
      setFormData((prev) => ({ ...prev, [field.name]: v }));

    switch (field.type) {
      case "table": {
        const tbl = formData[field.name];
        const rows = tbl?.rows || [];
        const headers = tbl?.headers || field.column_headers || [];
        if (headers.length === 0) {
          return (
            <div className="text-xs text-slate-400 italic py-2">
              Add column headers in the form builder
            </div>
          );
        }
        return (
          <div className="rounded-lg border border-slate-200 overflow-hidden">
            {tbl?.title && (
              <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 text-sm font-medium text-slate-700">
                {tbl.title}
              </div>
            )}
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-100">
                  {headers.map((h, i) => (
                    <TableHead key={i} className="text-xs font-medium">
                      {h}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row, ri) => (
                  <TableRow key={ri}>
                    {row.map((cell, ci) => (
                      <TableCell key={ci} className="p-1">
                        <Input
                          value={cell}
                          onChange={(e) =>
                            updateTableCell(field.name, ri, ci, e.target.value)
                          }
                          className="text-sm h-8 border-slate-200"
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        );
      }
      case "dropzone":
        return (
          <DropzoneInput
            value={formData[field.name]}
            onFile={handleFileDrop}
            fieldName={field.name}
            required={field.required}
            accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.xls,.xlsx,.doc,.docx"
            maxSize={DROPZONE_MAX_SIZE}
            allowedExtensions={ALLOWED_EXTENSIONS}
          />
        );
      case "textarea":
        return (
          <Textarea
            data-testid={`field-${field.name}`}
            value={val}
            onChange={(e) => onChange(e.target.value)}
            placeholder={
              field.placeholder || `Enter ${field.label.toLowerCase()}`
            }
            className="text-sm"
            rows={3}
          />
        );
      case "number":
        return (
          <Input
            data-testid={`field-${field.name}`}
            type="number"
            value={val}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || "0"}
            className="text-sm"
          />
        );
      case "date":
        return (
          <Input
            data-testid={`field-${field.name}`}
            type="date"
            value={val}
            onChange={(e) => onChange(e.target.value)}
            className="text-sm"
          />
        );
      case "select":
        return (
          <Select value={val} onValueChange={onChange}>
            <SelectTrigger
              data-testid={`field-${field.name}`}
              className="text-sm"
            >
              <SelectValue
                placeholder={`Select ${field.label.toLowerCase()}`}
              />
            </SelectTrigger>
            <SelectContent>
              {(field.options || []).map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      default:
        return (
          <Input
            data-testid={`field-${field.name}`}
            type="text"
            value={val}
            onChange={(e) => onChange(e.target.value)}
            placeholder={
              field.placeholder || `Enter ${field.label.toLowerCase()}`
            }
            className="text-sm"
          />
        );
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      data-testid="create-request-dialog"
    >
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col animate-slide-up mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-200 flex-shrink-0">
          <div>
            <h3 className="text-lg font-bold text-slate-900">New Request</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {step === 1 && "Select a department"}
              {step === 2 && `${deptName} — Select a form type`}
              {step === 3 && `${deptName} — ${selectedTemplate?.name}`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-slate-100 rounded-md"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto p-5" >
          {/* Step 1: Select Department */}
          {step === 1 && (
            <div className="grid grid-cols-2 gap-3">
              {departments.map((dept) => (
                <button
                  key={dept.id}
                  data-testid={`select-dept-${dept.code}`}
                  className="p-4 text-left border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50/30 transition-all group"
                  onClick={() => {
                    setSelectedDeptId(dept.id);
                    setStep(2);
                  }}
                >
                  <div className="text-sm font-semibold text-slate-800 group-hover:text-blue-700">
                    {dept.name}
                  </div>
                  <div className="text-xs text-slate-400 mt-1 line-clamp-2">
                    {dept.description}
                  </div>
                  <div className="flex items-center text-[10px] text-blue-500 mt-2 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                    Select <ChevronRight className="w-3 h-3 ml-0.5" />
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Step 2: Select Form Template */}
          {step === 2 && (
            <div className="space-y-2">
              {filteredTemplates.length === 0 ? (
                <div className="text-center py-8 text-sm text-slate-400">
                  No forms available for this department
                </div>
              ) : (
                filteredTemplates.map((tmpl) => (
                  <button
                    key={tmpl.id}
                    data-testid={`select-template-${tmpl.id}`}
                    className="w-full p-4 text-left border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50/30 transition-all flex items-center justify-between group"
                    onClick={() => handleSelectTemplate(tmpl)}
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-slate-400 group-hover:text-blue-500" />
                      <div>
                        <div className="text-sm font-medium text-slate-800">
                          {tmpl.name}
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5">
                          {tmpl.fields?.length || 0} fields
                          {tmpl.approver_chain?.length > 0 &&
                            ` · ${tmpl.approver_chain.length} approver${tmpl.approver_chain.length > 1 ? "s" : ""}`}
                        </div>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-500" />
                  </button>
                ))
              )}
            </div>
          )}

          {/* Step 3: Fill Form */}
          {step === 3 && selectedTemplate && (
            <div className="space-y-4" >
              <div className="space-y-2">
                <Label className="text-sm font-medium text-slate-700">
                  Request Title *
                </Label>
                <Input
                  data-testid="request-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Brief description of your request"
                  className="text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">
                    Priority
                  </Label>
                  <Select value={priority} onValueChange={setPriority}>
                    <SelectTrigger
                      data-testid="request-priority"
                      className="text-sm"
                    >
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="border-t border-slate-100 pt-4 mt-4">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                  Form Fields
                </div>
                <div className="space-y-4">
                  {selectedTemplate.fields.map((field) => (
                    <div key={field.name} className="space-y-1.5">
                      <Label className="text-sm font-medium text-slate-700">
                        {field.label}{" "}
                        {field.required && (
                          <span className="text-red-500">*</span>
                        )}
                      </Label>
                      {renderFieldInput(field)}
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <Label className="text-sm font-medium text-slate-700">
                  Additional Notes
                </Label>
                <Textarea
                  data-testid="request-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any additional information..."
                  className="text-sm"
                  rows={3}
                />
              </div>

              {selectedTemplate.approver_chain?.length > 0 && (
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-xs font-semibold text-slate-500 mb-2">
                    Approval Chain
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedTemplate.approver_chain.map((a, i) => (
                      <React.Fragment key={i}>
                        <span className="text-xs bg-white border border-slate-200 px-2 py-1 rounded">
                          Step {a.step}: {a.user_name || "Approver"}
                        </span>
                        {i < selectedTemplate.approver_chain.length - 1 && (
                          <span className="text-slate-300">→</span>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 flex items-center justify-between flex-shrink-0">
          <div>
            {step > 1 && (
              <Button
                variant="ghost"
                onClick={() => setStep(step - 1)}
                className="text-sm text-slate-600"
                data-testid="back-button"
              >
                Back
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={onClose}
              className="text-sm"
              data-testid="cancel-request"
            >
              Cancel
            </Button>
            {step === 3 && (
              <Button
                data-testid="submit-request"
                onClick={handleSubmit}
                disabled={!validateForm() || submitting}
                className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
              >
                {submitting ? "Submitting..." : "Submit Request"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
