"use client";
import { useState, useRef, useEffect } from "react";
import {
  analystQuery,
  getAnalystExamples,
  type AnalystResult,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { BrainCircuit, Send, ChevronRight, AlertCircle, Code2, Loader2 } from "lucide-react";

interface Message {
  id: number;
  role: "user" | "assistant";
  question?: string;
  result?: AnalystResult;
  error?: string;
  loading?: boolean;
}

let _id = 0;
const nextId = () => ++_id;

function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
      >
        <Code2 size={12} />
        {open ? "Hide SQL" : "Show SQL"}
        <ChevronRight
          size={12}
          className={cn("transition-transform", open && "rotate-90")}
        />
      </button>
      {open && (
        <pre className="mt-2 p-3 bg-surface-3 rounded-lg text-xs text-accent-cyan font-mono overflow-x-auto whitespace-pre-wrap break-all">
          {sql}
        </pre>
      )}
    </div>
  );
}

function ResultTable({ result }: { result: AnalystResult }) {
  if (result.rows.length === 0) {
    return (
      <p className="text-sm text-text-muted italic mt-2">
        Query returned no rows.
      </p>
    );
  }

  const cols = result.columns.map((c) => c.name);

  const fmt = (v: unknown): string => {
    if (v === null || v === undefined) return "—";
    if (typeof v === "number") {
      if (Math.abs(v) >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(2)}B`;
      if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
      if (Number.isInteger(v)) return v.toLocaleString();
      return Number(v.toFixed(4)).toString();
    }
    return String(v);
  };

  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-surface-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-surface-2/70 border-b border-surface-border">
            {cols.map((c) => (
              <th
                key={c}
                className="px-3 py-2 text-left text-text-muted font-medium whitespace-nowrap"
              >
                {c.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, i) => (
            <tr
              key={i}
              className={cn(
                "border-b border-surface-border/50",
                i % 2 === 0 ? "bg-surface-1" : "bg-surface-2/30"
              )}
            >
              {cols.map((c) => (
                <td
                  key={c}
                  className="px-3 py-2 text-text-secondary font-mono whitespace-nowrap max-w-xs truncate"
                >
                  {fmt(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {result.truncated && (
        <div className="px-3 py-2 text-xs text-text-muted bg-surface-2/40 border-t border-surface-border">
          Showing first {result.row_count} rows — refine your question to narrow results.
        </div>
      )}
    </div>
  );
}

function AssistantMessage({ msg }: { msg: Message }) {
  if (msg.loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted py-3">
        <Loader2 size={14} className="animate-spin text-accent-blue" />
        Thinking...
      </div>
    );
  }

  if (msg.error) {
    return (
      <div className="flex items-start gap-2 text-sm text-red-400 py-2">
        <AlertCircle size={14} className="shrink-0 mt-0.5" />
        <span>{msg.error}</span>
      </div>
    );
  }

  if (!msg.result) return null;

  return (
    <div className="space-y-1">
      {/* AI explanation */}
      <p className="text-sm text-text-primary leading-relaxed">
        {msg.result.explanation}
      </p>

      {/* Data table */}
      <ResultTable result={msg.result} />

      {/* SQL toggle */}
      <SqlBlock sql={msg.result.sql} />
    </div>
  );
}

export default function AnalystPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [examples, setExamples] = useState<string[]>([]);
  const [loadingExamples, setLoadingExamples] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getAnalystExamples()
      .then((d) => setExamples(d.examples))
      .catch(console.error)
      .finally(() => setLoadingExamples(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = async (question: string) => {
    const q = question.trim();
    if (!q) return;
    setInput("");

    const userMsg: Message = { id: nextId(), role: "user", question: q };
    const loadingMsg: Message = { id: nextId(), role: "assistant", loading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);

    try {
      const result = await analystQuery(q);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id ? { ...m, loading: false, result } : m
        )
      );
    } catch (err) {
      const errorText =
        err instanceof Error
          ? err.message.replace(/^API error \d+: /, "")
          : "An unexpected error occurred.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id ? { ...m, loading: false, error: errorText } : m
        )
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] animate-fade-in">
      {/* Header */}
      <div className="shrink-0 mb-4">
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <BrainCircuit size={22} className="text-accent-blue" />
          AI Analyst
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Ask plain-English questions about insider trades, company metrics, signals, and more.
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto space-y-5 pr-1">
        {/* Empty state — show examples */}
        {empty && (
          <div className="mt-4">
            <p className="text-xs text-text-muted uppercase tracking-widest font-semibold mb-3">
              Example questions
            </p>
            {loadingExamples ? (
              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Loader2 size={13} className="animate-spin" />
                Loading examples...
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {examples.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => submit(ex)}
                    className="text-left px-4 py-3 rounded-xl border border-surface-border bg-surface-1 hover:bg-surface-2 hover:border-accent-blue/40 transition-colors text-sm text-text-secondary"
                  >
                    <ChevronRight size={12} className="inline mr-1.5 text-accent-blue" />
                    {ex}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Message thread */}
        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.role === "user" && (
              <div className="flex justify-end">
                <div className="max-w-xl px-4 py-2.5 rounded-2xl rounded-tr-sm bg-accent-blue/15 border border-accent-blue/25 text-sm text-text-primary">
                  {msg.question}
                </div>
              </div>
            )}
            {msg.role === "assistant" && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-lg bg-accent-blue/15 border border-accent-blue/25 flex items-center justify-center shrink-0 mt-0.5">
                  <BrainCircuit size={13} className="text-accent-blue" />
                </div>
                <div className="flex-1 min-w-0 bg-surface-1 border border-surface-border rounded-2xl rounded-tl-sm px-4 py-3">
                  <AssistantMessage msg={msg} />
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="shrink-0 mt-4 bg-surface-1 border border-surface-border rounded-2xl flex items-end gap-2 px-4 py-3">
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about the data… (Enter to send, Shift+Enter for newline)"
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted resize-none outline-none max-h-28 overflow-y-auto"
        />
        <button
          onClick={() => submit(input)}
          disabled={!input.trim()}
          className={cn(
            "shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-colors",
            input.trim()
              ? "bg-accent-blue hover:bg-accent-blue/80 text-white"
              : "bg-surface-2 text-text-muted cursor-not-allowed"
          )}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
