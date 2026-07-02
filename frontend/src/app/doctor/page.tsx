"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Note {
  id: number;
  doctor_id: number;
  content: str;
  status: string;
  created_at: string;
  final_codes_id: number | null;
}

interface ICDCode {
  code: str;
  description: str;
  type: string;
  reason?: string;
}

export default function DoctorDashboard() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [content, setContent] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [finalCodes, setFinalCodes] = useState<ICDCode[]>([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [submittingNote, setSubmittingNote] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const storedUsername = localStorage.getItem("username");

    if (!token || role !== "doctor") {
      localStorage.clear();
      router.push("/");
      return;
    }

    setUsername(storedUsername || "Doctor");
    fetchNotes(token);
  }, [router]);

  const fetchNotes = async (token: string) => {
    setLoadingNotes(true);
    try {
      const res = await fetch(`${apiBase}/coding/notes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setNotes(data.reverse()); // Show newest first
      }
    } catch (err) {
      console.error("Error fetching notes:", err);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push("/");
  };

  const handleSubmitNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setSubmittingNote(true);
    setError("");
    const token = localStorage.getItem("token");

    try {
      const res = await fetch(`${apiBase}/coding/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content }),
      });

      if (!res.ok) {
        throw new Error("Failed to submit note");
      }

      setContent("");
      if (token) fetchNotes(token);
    } catch (err: any) {
      setError(err.message || "Submission failed");
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleViewFinalCodes = async (note: Note) => {
    setSelectedNote(note);
    setError("");
    const token = localStorage.getItem("token");

    try {
      const res = await fetch(`${apiBase}/coding/notes/${note.id}/final`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error("Finalized codes not found for this note");
      }

      const data = await res.json();
      setFinalCodes(data.final_codes);
      setModalOpen(true);
    } catch (err: any) {
      setError(err.message || "Failed to fetch codes");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-900/40 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-500 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20">
              M
            </div>
            <span className="font-semibold text-lg tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Medical Coding Workspace
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400">
              Welcome, <span className="text-slate-200 font-medium">{username}</span> (Doctor)
            </span>
            <button
              onClick={handleLogout}
              className="text-xs bg-slate-900 border border-slate-800 hover:bg-slate-800 px-3 py-1.5 rounded-lg font-medium transition-colors"
            >
              Log Out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Submit Note */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900/60 border border-slate-900 rounded-2xl p-6 backdrop-blur-xl">
            <h2 className="text-xl font-bold text-slate-200 mb-4">Submit Clinical Note</h2>
            
            {error && (
              <div className="bg-red-950/40 border border-red-900/50 text-red-300 text-xs px-4 py-3 rounded-lg mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmitNote} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Clinical Dictation / Note Content
                </label>
                <textarea
                  required
                  rows={8}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors resize-none"
                  placeholder="Type or paste patient note here..."
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                />
              </div>

              <button
                type="submit"
                disabled={submittingNote || !content.trim()}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] disabled:opacity-50 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-lg shadow-blue-500/10"
              >
                {submittingNote ? "Analyzing..." : "Submit for Coding"}
              </button>
            </form>
          </div>
        </div>

        {/* Right Side: Notes History */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900/60 border border-slate-900 rounded-2xl p-6 backdrop-blur-xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-slate-200">Patient Notes History</h2>
              <button
                onClick={() => {
                  const token = localStorage.getItem("token");
                  if (token) fetchNotes(token);
                }}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Refresh
              </button>
            </div>

            {loadingNotes ? (
              <div className="text-center py-12 text-slate-500 text-sm">Loading records...</div>
            ) : notes.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
                No clinical notes submitted yet. Use the left panel to submit one.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                      <th className="pb-3 pl-2">ID</th>
                      <th className="pb-3">Clinical Note Summary</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Submitted</th>
                      <th className="pb-3 text-right">Codes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900">
                    {notes.map((note) => (
                      <tr key={note.id} className="hover:bg-slate-900/30 transition-colors">
                        <td className="py-4 pl-2 font-mono text-xs text-slate-500">#{note.id}</td>
                        <td className="py-4 pr-4">
                          <p className="line-clamp-2 max-w-md text-slate-300 text-sm">
                            {note.content}
                          </p>
                        </td>
                        <td className="py-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                              note.status === "approved"
                                ? "bg-emerald-950/40 border-emerald-800 text-emerald-400"
                                : note.status === "rejected"
                                ? "bg-rose-950/40 border-rose-800 text-rose-400"
                                : note.status === "reviewed"
                                ? "bg-blue-950/40 border-blue-800 text-blue-400"
                                : "bg-amber-950/40 border-amber-800 text-amber-400"
                            }`}
                          >
                            {note.status === "approved"
                              ? "Approved"
                              : note.status === "rejected"
                              ? "Rejected"
                              : note.status === "reviewed"
                              ? "AI-Reviewed"
                              : "Pending AI"}
                          </span>
                        </td>
                        <td className="py-4 text-xs text-slate-400">
                          {new Date(note.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-4 text-right">
                          {note.status === "approved" ? (
                            <button
                              onClick={() => handleViewFinalCodes(note)}
                              className="text-xs bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 px-3 py-1.5 rounded-lg border border-blue-900/40 transition-colors"
                            >
                              View ICD
                            </button>
                          ) : note.status === "rejected" ? (
                            <span className="text-xs text-rose-400 font-semibold italic">Blocked by Safety</span>
                          ) : (
                            <span className="text-xs text-slate-600 italic">Awaiting Approval</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Code Viewer Modal */}
      {modalOpen && selectedNote && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 relative">
            <button
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 text-xl"
            >
              &times;
            </button>

            <h3 className="text-xl font-bold text-slate-200 mb-2">Approved ICD Codes</h3>
            <p className="text-xs text-slate-400 mb-6">Note ID #{selectedNote.id}</p>

            <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
              {finalCodes.length === 0 ? (
                <p className="text-sm text-slate-500 italic">No codes approved for this note.</p>
              ) : (
                finalCodes.map((c, i) => (
                  <div key={i} className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-bold text-sm bg-blue-950/60 border border-blue-800 px-2 py-0.5 rounded text-blue-400">
                        {c.code}
                      </span>
                      <span className="text-xs uppercase tracking-wider text-slate-500 font-semibold">
                        ICD-10-{c.type.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-200">{c.description}</p>
                    {c.reason && (
                      <div className="mt-2 pt-2 border-t border-slate-900">
                        <span className="text-xs text-slate-400 font-semibold block mb-0.5">Clinical Justification:</span>
                        <p className="text-xs text-slate-400 italic">{c.reason}</p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setModalOpen(false)}
                className="bg-slate-800 hover:bg-slate-700 text-sm font-semibold py-2 px-4 rounded-xl transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
