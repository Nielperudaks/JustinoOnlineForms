import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ImageOff } from "lucide-react";
import { markTutorialViewed } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const tutorialPages = [
  {
    title: "Welcome to the dashboard",
    description: "Review the guide image to see where the main navigation and request actions are located.",
    imagePath: "/first-login-tutorial-1.png",
  },
  {
    title: "Check your workspace",
    description: "Open the dashboard and confirm your assigned department, pending approvals, and recent requests.",
    imagePath: "/first-login-tutorial-2.png",
  },
  {
    title: "Create your first request",
    description: "Choose the correct form template and complete the required fields before submitting.",
    imagePath: "/first-login-tutorial-3.png",
  },
  {
    title: "Track approvals and updates",
    description: "Use request status and notifications to follow each approval step from submission to completion.",
    imagePath: "/first-login-tutorial-4.png",
  },
];

const FADE_DURATION_MS = 220;

export default function FirstLoginTutorialDialog() {
  const { user, updateUser } = useAuthStore();
  const [saving, setSaving] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isFading, setIsFading] = useState(false);
  const [imageAvailable, setImageAvailable] = useState(true);

  const isOpen = useMemo(
    () => Boolean(user) && user.has_viewed_tutorial === false,
    [user]
  );

  const currentPage = tutorialPages[currentStep];
  const isLastStep = currentStep === tutorialPages.length - 1;

  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
      setImageAvailable(true);
      setIsFading(false);
    }
  }, [isOpen]);

  useEffect(() => {
    setImageAvailable(true);
  }, [currentStep]);

  const goToNextStep = () => {
    if (isFading || isLastStep) {
      return;
    }

    setIsFading(true);
    window.setTimeout(() => {
      setCurrentStep((step) => step + 1);
      setIsFading(false);
    }, FADE_DURATION_MS);
  };

  const handleComplete = async () => {
    if (saving) {
      return;
    }

    setSaving(true);
    try {
      const res = await markTutorialViewed();
      updateUser(res.data);
      toast.success("Tutorial completed.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Unable to save tutorial progress");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={isOpen}>
      <DialogContent className="max-w-2xl gap-5 border-slate-200 bg-white p-0 sm:rounded-2xl">
        <div className="border-b border-slate-100 px-6 pt-6 pb-4">
          <DialogHeader className="text-left">
            <DialogTitle className="text-xl text-slate-900">Welcome to Justino Online Forms</DialogTitle>
            <DialogDescription className="mt-2 text-sm text-slate-500">
              This quick guide appears on first login only. 
            </DialogDescription>
          </DialogHeader>
        </div>

        <div
          className="px-6 transition-opacity duration-200"
          style={{ opacity: isFading ? 0 : 1 }}
        >
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Step {currentStep + 1} of {tutorialPages.length}
              </p>
              <p className="mt-1 text-sm text-slate-500">{currentPage.title}</p>
            </div>
          </div>

          {imageAvailable ? (
            <img
              src={currentPage.imagePath}
              alt={currentPage.title}
              className="h-auto w-full rounded-xl border border-slate-200 bg-slate-50 object-cover"
              onError={() => setImageAvailable(false)}
            />
          ) : (
            <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
              <ImageOff className="mb-3 h-8 w-8 text-slate-400" />
              <p className="text-sm font-medium text-slate-700">Tutorial image not found</p>
              <p className="mt-2 max-w-md text-sm text-slate-500">
                Add
                <span className="mx-1 rounded bg-white px-1.5 py-0.5 font-mono text-slate-700">
                  {currentPage.imagePath.replace("/", "")}
                </span>
                inside
                <span className="mx-1 rounded bg-white px-1.5 py-0.5 font-mono text-slate-700">
                  frontend/public
                </span>
                and it will appear here automatically.
              </p>
            </div>
          )}
        </div>

        <div className="px-6 pb-6">
          <div className="rounded-xl bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">{currentPage.title}</h3>
            <p className="mt-3 text-sm leading-6 text-slate-600">{currentPage.description}</p>
          </div>

          <DialogFooter className="mt-5">
            <Button
              type="button"
              onClick={isLastStep ? handleComplete : goToNextStep}
              disabled={saving || isFading}
              className="w-full bg-blue-600 text-white hover:bg-blue-700 sm:w-auto"
            >
              {isLastStep ? (saving ? "Saving..." : "Complete tutorial") : "Next"}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
