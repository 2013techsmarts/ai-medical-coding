"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Note {
  id: number;
  doctor_id: number;
  content: string;
  status: string;
  created_at: string;
  final_codes_id: number | null;
}

interface ICDCode {
  code: string;
  description: string;
  type: string;
  reason?: string;
  score?: number;
}

export default function CoderDashboard() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [suggestedCodes, setSuggestedCodes] = useState<ICDCode[]>([]);
  const [confidenceScore, setConfidenceScore] = useState("");
  const [codingResultId, setCodingResultId] = useState<number | null>(null);

  // Form for adding a new code
  const [newCode, setNewCode] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newType, setNewType] = useState("cm");
  const [newReason, setNewReason] = useState("");

  const [loadingNotes, setLoadingNotes] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [submittingApproval, setSubmittingApproval] = useState(false);
  
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const storedUsername = localStorage.getItem("username");

    if (!token || role !== "coder") {
      localStorage.clear();
      router.push("/");
      return;
    }

    setUsername(storedUsername || "Coder");
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
        setNotes(data.reverse());
      }
    } catch (err) {
      console.error("Error fetching notes:", err);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleSelectNote = async (note: Note) => {
    setSelectedNote(note);
    setSuggestedCodes([]);
    setCodingResultId(null);
    setConfidenceScore("");
    setError("");
    setMessage("");
    
    // Clear add code form
    setNewCode("");
    setNewDesc("");
    setNewReason("");

    const token = localStorage.getItem("token");
    setLoadingSuggestions(true);

    try {
      const res = await fetch(`${apiBase}/coding/notes/${note.id}/ai-suggestions`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error("Could not retrieve AI suggestions. The AI workflow might have failed or not completed yet.");
      }

      const data = await res.json();
      setCodingResultId(data.id);
      setSuggestedCodes(data.ai_suggested_codes || []);
      setConfidenceScore(data.confidence_score);
    } catch (err: any) {
      setError(err.message || "Failed to load suggestions");
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleRemoveCode = (index: number) => {
    const updated = [...suggestedCodes];
    updated.splice(index, 1);
    setSuggestedCodes(updated);
  };

  const handleAddCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim() || !newDesc.trim()) return;

    const codeObj: ICDCode = {
      code: newCode.trim().toUpperCase(),
      description: newDesc.trim(),
      type: newType,
      reason: newReason.trim() || "Manually added by coder",
      score: 1.0
    };

    setSuggestedCodes([...suggestedCodes, codeObj]);
    
    // Reset form
    setNewCode("");
    setNewDesc("");
    setNewReason("");
  };

  const handleApprove = async () => {
    if (!codingResultId || !selectedNote) return;

    setSubmittingApproval(true);
    setError("");
    setMessage("");
    const token = localStorage.getItem("token");

    try {
      const res = await fetch(`${apiBase}/coding/approvals`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          coding_result_id: codingResultId,
          final_codes: suggestedCodes,
        }),
      });

      if (!res.ok) {
        throw new Error("Approval submission failed");
      }

      setMessage("ICD codes successfully approved and saved!");
      
      // Update local notes list
      const updatedNotes = notes.map((n) =>
        n.id === selectedNote.id ? { ...n, status: "approved" } : n
      );
      setNotes(updatedNotes);
      setSelectedNote({ ...selectedNote, status: "approved" });

      if (token) fetchNotes(token);
    } catch (err: any) {
      setError(err.message || "Failed to approve codes");
    } finally {
      setSubmittingApproval(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-900 bg-slate-900/40 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-r from-blue-500 to-indigo-500 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20">
              M
            </div>
            <span className="font-semibold text-lg tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              Coder Audit Hub
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400">
              Welcome, <span className="text-slate-200 font-medium">{username}</span> (Coder)
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

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-8 overflow-hidden">
        
        {/* Left Panel: Notes List (col-span-4) */}
        <div className="lg:col-span-4 bg-slate-900/40 border border-slate-900 rounded-2xl p-6 flex flex-col h-[calc(100vh-140px)]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-slate-200">Clinical Dictations</h2>
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

          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {loadingNotes ? (
              <div className="text-center py-12 text-slate-500 text-sm">Loading records...</div>
            ) : notes.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-sm italic">No records found.</div>
            ) : (
              notes.map((note) => (
                <div
                  key={note.id}
                  onClick={() => handleSelectNote(note)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    selectedNote?.id === note.id
                      ? "bg-blue-600/10 border-blue-500/50 shadow-md"
                      : "bg-slate-950/40 border-slate-880 hover:border-slate-800"
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-mono text-xs text-slate-500">#{note.id}</span>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        note.status === "approved"
                          ? "bg-emerald-950/40 border-emerald-800 text-emerald-400"
                          : note.status === "reviewed"
                          ? "bg-blue-950/40 border-blue-800 text-blue-400"
                          : "bg-amber-950/40 border-amber-800 text-amber-400"
                      }`}
                    >
                      {note.status === "approved" ? "Approved" : note.status === "reviewed" ? "Needs Audit" : "Pending AI"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-2">{note.content}</p>
                  <span className="text-[10px] text-slate-500 block mt-2">
                    {new Date(note.created_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Panel: Audit View (col-span-8) */}
        <div className="lg:col-span-8 flex flex-col h-[calc(100vh-140px)]">
          {selectedNote ? (
            <div className="flex-1 bg-slate-900/60 border border-slate-900 rounded-2xl p-6 backdrop-blur-xl flex flex-col overflow-hidden">
              
              {/* Feedback banners */}
              {message && (
                <div className="bg-emerald-950/40 border border-emerald-900/50 text-emerald-300 text-sm px-4 py-3 rounded-xl mb-4">
                  {message}
                </div>
              )}
              {error && (
                <div className="bg-red-950/40 border border-red-900/50 text-red-300 text-sm px-4 py-3 rounded-xl mb-4">
                  {error}
                </div>
              )}

              {/* Top Section: Note Details */}
              <div className="border-b border-slate-900 pb-4 mb-4 flex-shrink-0">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-bold text-slate-200">Auditing Record #{selectedNote.id}</h3>
                    <span className="text-xs text-slate-500">Submitted by Doctor ID: {selectedNote.doctor_id}</span>
                  </div>
                  {confidenceScore && (
                    <div className="text-right">
                      <span className="text-xs text-slate-500 block">AI Confidence</span>
                      <span className={`text-xs uppercase font-bold tracking-wider ${
                        confidenceScore === "high" ? "text-emerald-400" : "text-amber-400"
                      }`}>
                        {confidenceScore}
                      </span>
                    </div>
                  )}
                </div>

                <div className="mt-3 bg-slate-950/80 border border-slate-900 rounded-xl p-4 max-h-36 overflow-y-auto text-sm text-slate-300 italic">
                  "{selectedNote.content}"
                </div>
              </div>

              {/* Suggestions Panel */}
              <div className="flex-1 overflow-y-auto space-y-6 pr-1">
                {loadingSuggestions ? (
                  <div className="text-center py-12 text-slate-500 text-sm">Running RAG & generating codes...</div>
                ) : (
                  <>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Active ICD Codes ({suggestedCodes.length})
                      </h4>

                      <div className="space-y-3">
                        {suggestedCodes.length === 0 ? (
                          <div className="text-center py-6 text-slate-600 text-xs italic bg-slate-950/40 border border-slate-900 rounded-xl">
                            No codes currently attached to this record. Use the form below to add one.
                          </div>
                        ) : (
                          suggestedCodes.map((c, i) => (
                            <div key={i} className="flex justify-between items-start bg-slate-950 border border-slate-900/60 rounded-xl p-4 hover:border-slate-800 transition-all">
                              <div className="space-y-1.5 flex-1 pr-4">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono font-bold text-xs bg-blue-950 border border-blue-900 px-2 py-0.5 rounded text-blue-400">
                                    {c.code}
                                  </span>
                                  <span className="text-[10px] uppercase font-bold text-slate-500">
                                    ICD-10-{c.type.toUpperCase()}
                                  </span>
                                  {c.score && (
                                    <span className="text-[10px] text-slate-500 italic">
                                      Match: {(c.score * 100).toFixed(0)}%
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm font-semibold text-slate-200">{c.description}</p>
                                {c.reason && (
                                  <p className="text-xs text-slate-400 italic bg-slate-900/30 p-2 rounded border border-slate-900/40">
                                    <span className="font-semibold not-italic">Justification:</span> {c.reason}
                                  </p>
                                )}
                              </div>
                              <button
                                onClick={() => handleRemoveCode(i)}
                                disabled={selectedNote.status === "approved"}
                                className="text-slate-600 hover:text-red-400 p-1 transition-colors disabled:opacity-30 disabled:pointer-events-none"
                                title="Remove Code"
                              >
                                &times;
                              </button>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Add Code Form (only enabled if not approved) */}
                    {selectedNote.status !== "approved" && (
                      <div className="border-t border-slate-900 pt-6">
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                          Add Custom ICD-10 Code
                        </h4>
                        <form onSubmit={handleAddCode} className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-950/40 border border-slate-900 rounded-xl p-4">
                          <div className="space-y-1">
                            <label className="text-[10px] font-bold text-slate-500 uppercase">Code</label>
                            <input
                              type="text"
                              required
                              placeholder="e.g. E11.9"
                              className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500/50"
                              value={newCode}
                              onChange={(e) => setNewCode(e.target.value)}
                            />
                          </div>

                          <div className="space-y-1">
                            <label className="text-[10px] font-bold text-slate-500 uppercase">Type</label>
                            <select
                              className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500/50"
                              value={newType}
                              onChange={(e) => setNewType(e.target.value)}
                            >
                              <option value="cm">CM (Diagnostic)</option>
                              <option value="pcs">PCS (Procedural)</option>
                            </select>
                          </div>

                          <div className="space-y-1">
                            <label className="text-[10px] font-bold text-slate-500 uppercase">Description</label>
                            <input
                              type="text"
                              required
                              placeholder="e.g. Type 2 diabetes mellitus..."
                              className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500/50"
                              value={newDesc}
                              onChange={(e) => setNewDesc(e.target.value)}
                            />
                          </div>

                          <div className="md:col-span-3 space-y-1">
                            <label className="text-[10px] font-bold text-slate-500 uppercase">Auditor justification</label>
                            <input
                              type="text"
                              placeholder="Reason code is clinically justified..."
                              className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500/50"
                              value={newReason}
                              onChange={(e) => setNewReason(e.target.value)}
                            />
                          </div>

                          <div className="md:col-span-3 flex justify-end">
                            <button
                              type="submit"
                              className="bg-slate-800 hover:bg-slate-700 text-xs font-semibold py-2 px-4 rounded-lg transition-colors"
                            >
                              + Add to List
                            </button>
                          </div>
                        </form>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Bottom Audit Buttons */}
              <div className="border-t border-slate-900 pt-4 mt-4 flex justify-end gap-3 flex-shrink-0">
                {selectedNote.status === "approved" ? (
                  <span className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                    ✓ Audit Finalized
                  </span>
                ) : (
                  <button
                    onClick={handleApprove}
                    disabled={submittingApproval || suggestedCodes.length === 0 || loadingSuggestions}
                    className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:scale-[0.98] disabled:opacity-50 text-white font-semibold py-2.5 px-6 rounded-xl transition-all shadow-lg shadow-blue-500/10 text-sm"
                  >
                    {submittingApproval ? "Saving..." : "Approve and Save ICD Codes"}
                  </button>
                )}
              </div>

            </div>
          ) : (
            <div className="flex-1 bg-slate-900/40 border border-slate-900 border-dashed rounded-2xl flex flex-col items-center justify-center p-8 text-center">
              <div className="h-12 w-12 rounded-2xl bg-slate-900 flex items-center justify-center font-bold text-slate-600 text-lg border border-slate-800 mb-4">
                👁
              </div>
              <h3 className="text-lg font-bold text-slate-300">Auditor Panel</h3>
              <p className="text-sm text-slate-500 max-w-sm mt-1">
                Select a patient note from the left sidebar to audit the AI suggestions, add custom overrides, and finalize coding records.
              </p>
            </div>
          )}
        </div>

      </main>
    </div>
  );
}
