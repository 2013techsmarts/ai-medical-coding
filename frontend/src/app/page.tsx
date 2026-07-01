"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AuthPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [role, setRole] = useState("doctor");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Check if already logged in
  useEffect(() => {
    const token = localStorage.getItem("token");
    const userRole = localStorage.getItem("role");
    if (token && userRole) {
      router.push(`/${userRole}`);
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

    try {
      if (isLogin) {
        // Login request
        const res = await fetch(`${apiBase}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Login failed");
        }

        // Save token and info
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("username", data.username);

        router.push(`/${data.role}`);
      } else {
        // Register request
        const res = await fetch(`${apiBase}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, email, password, role }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Registration failed");
        }

        setMessage("Registration successful! Please login.");
        setIsLogin(true);
        setPassword("");
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6 relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl -z-10 pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl -z-10 pointer-events-none"></div>

      {/* Main card Container */}
      <div className="w-full max-w-md bg-slate-900/60 border border-slate-800 rounded-2xl shadow-2xl p-8 backdrop-blur-xl transition-all duration-300">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            AI Medical Coding
          </h1>
          <p className="text-slate-400 text-sm mt-2">
            ICD-10 Autonomous Suggestion & Human Audit
          </p>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-slate-800 mb-6">
          <button
            type="button"
            className={`flex-1 pb-3 text-sm font-medium transition-all ${
              isLogin
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => {
              setIsLogin(true);
              setError("");
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`flex-1 pb-3 text-sm font-medium transition-all ${
              !isLogin
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => {
              setIsLogin(false);
              setError("");
            }}
          >
            Register
          </button>
        </div>

        {/* Feedback Messages */}
        {error && (
          <div className="bg-red-950/50 border border-red-900 text-red-300 text-xs px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}
        {message && (
          <div className="bg-emerald-950/50 border border-emerald-900 text-emerald-300 text-xs px-4 py-3 rounded-lg mb-6">
            {message}
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Username
            </label>
            <input
              type="text"
              required
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors"
              placeholder="e.g. jdoe"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          {!isLogin && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Email
                </label>
                <input
                  type="email"
                  required
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                  placeholder="e.g. john@hospital.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Assign Role
                </label>
                <div className="flex gap-4">
                  <label className="flex-1 flex items-center justify-center border border-slate-800 bg-slate-950/40 rounded-xl px-4 py-3 cursor-pointer hover:border-slate-700 transition-all">
                    <input
                      type="radio"
                      name="role"
                      value="doctor"
                      checked={role === "doctor"}
                      onChange={() => setRole("doctor")}
                      className="sr-only"
                    />
                    <span className={`text-sm ${role === "doctor" ? "text-blue-400 font-bold" : "text-slate-400"}`}>
                      Doctor
                    </span>
                  </label>
                  <label className="flex-1 flex items-center justify-center border border-slate-800 bg-slate-950/40 rounded-xl px-4 py-3 cursor-pointer hover:border-slate-700 transition-all">
                    <input
                      type="radio"
                      name="role"
                      value="coder"
                      checked={role === "coder"}
                      onChange={() => setRole("coder")}
                      className="sr-only"
                    />
                    <span className={`text-sm ${role === "coder" ? "text-blue-400 font-bold" : "text-slate-400"}`}>
                      Coder
                    </span>
                  </label>
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Password
            </label>
            <input
              type="password"
              required
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] disabled:opacity-50 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-lg shadow-blue-500/10 mt-6"
          >
            {loading ? "Processing..." : isLogin ? "Sign In" : "Register"}
          </button>
        </form>
      </div>
    </div>
  );
}
