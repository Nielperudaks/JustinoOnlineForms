import React, { useState, useEffect } from "react";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, FileText, ChevronRight } from "lucide-react";

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
      initial[f.name] = "";
    });
    setFormData(initial);
    setStep(3);
  };

  const handleSubmit = async () => {
    if (!title.trim()) return;
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

  const renderFieldInput = (field) => {
    const val = formData[field.name] || "";
    const onChange = (v) =>
      setFormData((prev) => ({ ...prev, [field.name]: v }));

    switch (field.type) {
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
        <div className="flex-1 overflow-y-auto p-5">
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
            <div className="space-y-4">
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
                disabled={!title.trim() || submitting}
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
