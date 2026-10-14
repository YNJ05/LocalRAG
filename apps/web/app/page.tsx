"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

const API =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

type Source = {
  source_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  excerpt: string;
  score: number;
};

type DocInfo = {
  id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  status: string;
};

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
};

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("localrag_session") || "";
}

function setSessionId(sid: string) {
  if (typeof window !== "undefined") {
    sessionStorage.setItem("localrag_session", sid);
  }
}

function clearSessionId() {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem("localrag_session");
  }
}

// ── Markdown Component (Monochrome & Clean) ──────────────────────────────────
function MarkdownView({ content }: { content: string }) {
  if (!content) return null;

  const parts: React.ReactNode[] = [];
  const lines = content.split("\n");
  let inCode = false;
  let codeBuffer: string[] = [];
  let codeLang = "";
  let paragraphBuffer: string[] = [];

  const flushParagraph = () => {
    if (paragraphBuffer.length === 0) return;
    const text = paragraphBuffer.join("\n");
    paragraphBuffer = [];

    const pLines = text.split("\n");
    let currentList: string[] = [];
    let isOrdered = false;

    const flushList = () => {
      if (currentList.length === 0) return;
      if (isOrdered) {
        parts.push(
          <ol key={`ol-${parts.length}`} className="chat-ol">
            {currentList.map((item, idx) => (
              <li key={idx}>{renderInline(item)}</li>
            ))}
          </ol>
        );
      } else {
        parts.push(
          <ul key={`ul-${parts.length}`} className="chat-ul">
            {currentList.map((item, idx) => (
              <li key={idx}>{renderInline(item)}</li>
            ))}
          </ul>
        );
      }
      currentList = [];
    };

    for (let i = 0; i < pLines.length; i++) {
      const line = pLines[i];
      const trimmed = line.trim();

      if (trimmed.startsWith("### ")) {
        flushList();
        parts.push(
          <h3 key={`h3-${parts.length}`} className="chat-h3">
            {renderInline(trimmed.slice(4))}
          </h3>
        );
        continue;
      }
      if (trimmed.startsWith("## ")) {
        flushList();
        parts.push(
          <h2 key={`h2-${parts.length}`} className="chat-h2">
            {renderInline(trimmed.slice(3))}
          </h2>
        );
        continue;
      }
      if (trimmed.startsWith("# ")) {
        flushList();
        parts.push(
          <h1 key={`h1-${parts.length}`} className="chat-h1">
            {renderInline(trimmed.slice(2))}
          </h1>
        );
        continue;
      }
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        if (isOrdered) flushList();
        isOrdered = false;
        currentList.push(trimmed.slice(2));
        continue;
      }
      const numMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
      if (numMatch) {
        if (!isOrdered && currentList.length > 0) flushList();
        isOrdered = true;
        currentList.push(numMatch[2]);
        continue;
      }

      flushList();
      if (trimmed) {
        parts.push(
          <p key={`p-${parts.length}`} className="chat-p">
            {renderInline(line)}
          </p>
        );
      }
    }
    flushList();
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("```")) {
      if (inCode) {
        inCode = false;
        const codeText = codeBuffer.join("\n");
        codeBuffer = [];
        parts.push(
          <CodeBlock
            key={`code-${parts.length}`}
            code={codeText}
            language={codeLang}
          />
        );
      } else {
        flushParagraph();
        inCode = true;
        codeLang = line.slice(3).trim();
      }
    } else if (inCode) {
      codeBuffer.push(line);
    } else {
      paragraphBuffer.push(line);
    }
  }

  if (inCode && codeBuffer.length > 0) {
    parts.push(
      <CodeBlock
        key={`code-${parts.length}`}
        code={codeBuffer.join("\n")}
        language={codeLang}
      />
    );
  } else {
    flushParagraph();
  }

  return <div className="chat-markdown">{parts}</div>;
}

function renderInline(text: string): React.ReactNode {
  const tokens = text.split(/(\[S\d+\]|\*\*.*?\*\*|`.*?`)/g);

  return tokens.map((token, idx) => {
    if (token.startsWith("[S") && token.endsWith("]")) {
      return (
        <span key={idx} className="citation-tag">
          {token}
        </span>
      );
    }
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={idx}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return (
        <code key={idx} className="chat-inline-code">
          {token.slice(1, -1)}
        </code>
      );
    }
    return token;
  });
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-container">
      <div className="code-header">
        <span className="code-language">{language || "code"}</span>
        <button className="code-copy-btn" onClick={handleCopy}>
          {copied ? "Copied" : "Copy code"}
        </button>
      </div>
      <pre className="code-content">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// ── Main Page Component ──────────────────────────────────────────────────────
export default function Home() {
  const [sessionId, setSession] = useState("");
  const [documents, setDocuments] = useState<DocInfo[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [asking, setAsking] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Session initialization
  useEffect(() => {
    const existing = getSessionId();
    if (existing) {
      setSession(existing);
      fetch(`${API}/session/refresh`, {
        method: "POST",
        headers: { "X-Session-Id": existing },
      })
        .then(async (r) => {
          if (!r.ok) {
            clearSessionId();
            await createSession();
            return;
          }
          await loadDocuments(existing);
        })
        .catch(() => createSession());
    } else {
      createSession();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function createSession() {
    try {
      const res = await fetch(`${API}/session`, { method: "POST" });
      if (!res.ok) throw new Error("Session creation failed");
      const data = await res.json();
      setSession(data.session_id);
      setSessionId(data.session_id);
      await loadDocuments(data.session_id);
    } catch {
      setUploadStatus("Connection error");
    }
  }

  async function loadDocuments(sid: string) {
    try {
      const res = await fetch(`${API}/documents`, {
        headers: { "X-Session-Id": sid },
      });
      if (res.ok) {
        const docs = await res.json();
        setDocuments(docs);
      }
    } catch {
      // ignore
    }
  }

  async function processUpload(file: File) {
    if (!file || !sessionId) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadStatus("Only PDF files allowed");
      return;
    }

    setUploading(true);
    setUploadStatus(`Uploading ${file.name}...`);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API}/documents`, {
        method: "POST",
        headers: { "X-Session-Id": sessionId },
        body: form,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadStatus("");
        await loadDocuments(sessionId);
      } else {
        setUploadStatus(data.detail || "Upload failed");
      }
    } catch {
      setUploadStatus("Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleFileInputChange() {
    const file = fileInputRef.current?.files?.[0];
    if (file) processUpload(file);
  }

  async function handleDeleteDoc(docId: string, filename: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!sessionId) return;
    if (!confirm(`Delete ${filename}?`)) return;

    try {
      await fetch(`${API}/documents/${docId}`, {
        method: "DELETE",
        headers: { "X-Session-Id": sessionId },
      });
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      if (selectedDocId === docId) setSelectedDocId(null);
    } catch {
      // ignore
    }
  }

  async function handleAsk(promptText?: string) {
    const textToSend = (promptText || question).trim();
    if (!textToSend || !sessionId || asking) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      content: textToSend,
    };

    const assistantMessage: Message = {
      id: `msg-${Date.now()}-assistant`,
      role: "assistant",
      content: "",
      streaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setQuestion("");
    setAsking(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "24px";
    }

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          question: textToSend,
          document_id: selectedDocId || undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          last.content = data.detail || "Request failed";
          last.streaming = false;
          return updated;
        });
        setAsking(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let sources: Source[] = [];
      let buffer = "";
      let currentEvent = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const data = line.slice(6).replace(/\r$/, "");

              if (currentEvent === "sources") {
                try {
                  sources = JSON.parse(data);
                } catch {
                  // ignore
                }
              } else if (currentEvent === "token") {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  last.content += data;
                  return [...updated];
                });
              } else if (currentEvent === "done") {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  last.streaming = false;
                  last.sources = sources;
                  return [...updated];
                });
              } else if (currentEvent === "error") {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  last.content += data;
                  last.streaming = false;
                  return [...updated];
                });
              }
              currentEvent = "";
            }
          }
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.streaming) {
          last.streaming = false;
          last.sources = sources;
        }
        return [...updated];
      });
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        last.content = "Failed to connect to local AI service.";
        last.streaming = false;
        return updated;
      });
    } finally {
      setAsking(false);
    }
  }

  function handleFormSubmit(e: FormEvent) {
    e.preventDefault();
    handleAsk();
  }

  async function handleNewChat() {
    if (!sessionId) return;
    setMessages([]);
    setSelectedDocId(null);
  }

  function handleTextareaInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setQuestion(e.target.value);
    const el = e.target;
    el.style.height = "24px";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  }

  const activeDocName = selectedDocId
    ? documents.find((d) => d.id === selectedDocId)?.filename
    : null;

  const hasMessages = messages.length > 0;

  return (
    <div className="chatgpt-layout">
      {/* ── Left Sidebar (ChatGPT-like) ────────────────────────────────────── */}
      <aside className={`chatgpt-sidebar ${sidebarOpen ? "open" : "closed"}`}>
        {/* Sidebar Top: Logo + Toggle */}
        <div className="sidebar-top">
          <div className="sidebar-header-left">
            <span className="app-title">LocalRAG</span>
          </div>
          <button
            className="icon-btn"
            onClick={() => setSidebarOpen(false)}
            title="Close sidebar"
          >
            ✕
          </button>
        </div>

        {/* New Chat Button */}
        <div className="sidebar-nav-item" onClick={handleNewChat}>
          <span className="nav-plus">+</span>
          <span className="nav-label">New chat</span>
        </div>

        {/* Upload Button */}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          onChange={handleFileInputChange}
          style={{ display: "none" }}
        />
        <div
          className="sidebar-nav-item"
          onClick={() => fileInputRef.current?.click()}
        >
          <span className="nav-plus">↑</span>
          <span className="nav-label">
            {uploading ? "Uploading PDF..." : "Upload document"}
          </span>
        </div>

        {uploadStatus && <div className="sidebar-alert">{uploadStatus}</div>}

        {/* Documents / Knowledge Base List */}
        <div className="sidebar-section-title">
          <span>Documents</span>
          <span>{documents.length}</span>
        </div>

        <div className="sidebar-history-list">
          {/* All documents option */}
          <div
            className={`history-item ${selectedDocId === null ? "active" : ""}`}
            onClick={() => setSelectedDocId(null)}
          >
            <span className="history-text">All documents</span>
          </div>

          {documents.map((doc) => {
            const isSelected = selectedDocId === doc.id;
            return (
              <div
                key={doc.id}
                className={`history-item ${isSelected ? "active" : ""}`}
                onClick={() => setSelectedDocId(isSelected ? null : doc.id)}
                title={doc.filename}
              >
                <span className="history-text">{doc.filename}</span>
                <button
                  className="history-delete"
                  onClick={(e) => handleDeleteDoc(doc.id, doc.filename, e)}
                  title="Delete document"
                >
                  ×
                </button>
              </div>
            );
          })}

          {documents.length === 0 && (
            <div className="sidebar-empty">
              <span>No documents yet. Click Upload document above.</span>
            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <div className="user-profile-row">
            <div className="user-avatar-circle">L</div>
            <div className="user-profile-info">
              <span className="user-profile-name">Local Session</span>
              <span className="user-profile-plan">
                {sessionId ? sessionId.slice(0, 8) : "offline"}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ────────────────────────────────────────────────── */}
      <main className="chatgpt-main">
        {/* Top Navbar */}
        <header className="chatgpt-header">
          <div className="header-left">
            {!sidebarOpen && (
              <button
                className="icon-btn-header"
                onClick={() => setSidebarOpen(true)}
                title="Open sidebar"
              >
                ☰
              </button>
            )}
            <span className="chatgpt-header-title">
              {activeDocName ? `LocalRAG • ${activeDocName}` : "LocalRAG"}
            </span>
          </div>
          {hasMessages && (
            <button className="header-new-btn" onClick={handleNewChat}>
              New chat
            </button>
          )}
        </header>

        {/* Central Chat View */}
        <div className="chatgpt-body">
          {!hasMessages ? (
            /* Empty State: exactly like ChatGPT screenshot */
            <div className="chatgpt-hero">
              <h1 className="hero-headline">What's on your mind today?</h1>

              <div className="hero-input-container">
                <form className="hero-input-box" onSubmit={handleFormSubmit}>
                  <button
                    type="button"
                    className="hero-attach-btn"
                    onClick={() => fileInputRef.current?.click()}
                    title="Upload PDF document"
                  >
                    +
                  </button>
                  <textarea
                    ref={textareaRef}
                    value={question}
                    onChange={handleTextareaInput}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      documents.length === 0
                        ? "Upload a PDF document or ask a question..."
                        : activeDocName
                        ? `Ask about ${activeDocName}...`
                        : "Ask LocalRAG..."
                    }
                    rows={1}
                  />
                  <button
                    type="submit"
                    className="hero-send-btn"
                    disabled={asking || !question.trim()}
                    title="Send message"
                  >
                    ↑
                  </button>
                </form>
              </div>

              {documents.length > 0 && (
                <div className="hero-doc-tags">
                  <span className="hero-doc-tag-label">Active knowledge:</span>
                  {documents.map((d) => (
                    <span
                      key={d.id}
                      className={`hero-doc-chip ${selectedDocId === d.id ? "selected" : ""}`}
                      onClick={() =>
                        setSelectedDocId(selectedDocId === d.id ? null : d.id)
                      }
                    >
                      {d.filename}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* Messages Conversation Stream */
            <div className="chatgpt-conversation">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`chat-message-row ${msg.role === "user" ? "user" : "assistant"}`}
                >
                  <div className="chat-message-container">
                    {msg.role === "user" ? (
                      <div className="user-message-bubble">
                        <p>{msg.content}</p>
                      </div>
                    ) : (
                      <div className="assistant-message-content">
                        {msg.content ? (
                          <MarkdownView content={msg.content} />
                        ) : msg.streaming ? (
                          <div className="streaming-cursor-text">Thinking...</div>
                        ) : null}

                        {/* Citations / Sources */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div className="chat-sources">
                            <span className="sources-label">Sources:</span>
                            <div className="sources-list">
                              {msg.sources.map((s) => (
                                <details key={s.source_id} className="source-item">
                                  <summary>
                                    [{s.source_id}] {s.filename} (p. {s.page_number})
                                  </summary>
                                  <div className="source-excerpt-text">
                                    {s.excerpt}
                                  </div>
                                </details>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Input Dock (visible when messages exist) */}
        {hasMessages && (
          <div className="bottom-dock-wrapper">
            <form className="bottom-dock-box" onSubmit={handleFormSubmit}>
              <button
                type="button"
                className="hero-attach-btn"
                onClick={() => fileInputRef.current?.click()}
                title="Upload PDF document"
              >
                +
              </button>
              <textarea
                ref={textareaRef}
                value={question}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Ask LocalRAG..."
                rows={1}
              />
              <button
                type="submit"
                className="hero-send-btn"
                disabled={asking || !question.trim()}
                title="Send message"
              >
                ↑
              </button>
            </form>
            <div className="bottom-dock-footer">
              <span>LocalRAG runs offline. Output generated from local models.</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
