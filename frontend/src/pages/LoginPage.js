import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Lock, Mail, ArrowRight, FileText } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const res = await login({ email, password });
      setAuth(res.data.user, res.data.token);
      toast.success("Welcome back!");
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 relative overflow-hidden flex-col justify-between p-12">
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `url("https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80")`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-slate-900/60 to-slate-900/95" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="text-white text-xl font-bold tracking-tight">Workflow Bridge</span>
          </div>
        </div>
        <div className="relative z-10">
          <h1 className="text-4xl font-bold text-white leading-tight tracking-tight mb-4">
            Paperless<br />Transaction<br />System
          </h1>
          <p className="text-slate-400 text-base max-w-md leading-relaxed">
            Streamline approvals across all departments. Submit, track, and manage requests from anywhere.
          </p>
        </div>
        <div className="relative z-10 flex gap-8 text-sm">
          <div>
            <div className="text-2xl font-bold text-white">10</div>
            <div className="text-slate-500">Departments</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">89</div>
            <div className="text-slate-500">Form Types</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-white">3-Step</div>
            <div className="text-slate-500">Approvals</div>
          </div>
        </div>
      </div>

      {/* Right panel - login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-sm animate-slide-up">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-slate-900 text-lg font-bold">Workflow Bridge</span>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Sign in</h2>
          <p className="text-slate-500 text-sm mt-1 mb-8">Enter your credentials to access the system</p>

          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-700 text-sm font-medium">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  id="email"
                  data-testid="login-email-input"
                  type="email"
                  placeholder="admin@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-11 bg-white border-slate-200 focus:border-blue-500 focus:ring-blue-100"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-700 text-sm font-medium">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  id="password"
                  data-testid="login-password-input"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 h-11 bg-white border-slate-200 focus:border-blue-500 focus:ring-blue-100"
                />
              </div>
            </div>

            <Button
              type="submit"
              data-testid="login-submit-button"
              disabled={loading}
              className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition-all active:scale-[0.98]"
            >
              {loading ? "Signing in..." : "Sign in"}
              {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
            </Button>
          </form>

          <div className="mt-8 p-4 bg-white border border-slate-200 rounded-lg">
            <p className="text-xs font-medium text-slate-500 mb-2">Demo credentials</p>
            <div className="font-mono text-xs text-slate-600 space-y-1">
              <div>Email: <span className="text-slate-900">admin@company.com</span></div>
              <div>Password: <span className="text-slate-900">admin123</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
