import { HttpAgent } from "@ag-ui/client";
import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { AccountInfo } from "@azure/msal-browser";
import { EntraAuth, SignInRequiredError } from "./auth";
import { ApiError, errorMessage, responseError } from "./errors";

type ChatMessage = { id: string; role: "user" | "assistant"; text: string };

export default function App({ auth, endpoint }: { auth: EntraAuth; endpoint: string }) {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [resumeId, setResumeId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [revision, setRevision] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const agentRef = useRef<HttpAgent | null>(null);
  const stoppingRef = useRef(false);
  const requestPending = useRef(false);

  function disconnect() {
    agentRef.current?.abortRun();
    setSessionId("");
    setRevision(null);
    setMessages([]);
    setDraft("");
    setResumeId("");
    setNotice("");
  }

  function showError(error: unknown, fallback: string) {
    if (error instanceof SignInRequiredError) {
      setAuthRequired(true);
      setNotice(error.message);
    } else if (error instanceof ApiError) {
      setNotice(error.message);
    } else {
      // Do not display raw identity-provider errors or token responses.
      setNotice(fallback);
    }
  }

  async function signIn() {
    if (authBusy || requestPending.current) return;
    setAuthBusy(true);
    setNotice("");
    try {
      const signedIn = await auth.signIn();
      // A different signed-in user must never inherit another user's visible session.
      if (signedIn.homeAccountId !== account?.homeAccountId) disconnect();
      setAccount(signedIn);
      setAuthRequired(false);
    } catch {
      setNotice("Sign-in did not complete. Try again and allow the Microsoft sign-in popup.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function signOut() {
    if (!account || busy || requestPending.current) return;
    const signedOut = account;
    disconnect();
    setAccount(null);
    setAuthRequired(false);
    setAuthBusy(true);
    try {
      await auth.signOut(signedOut);
    } catch {
      setNotice("Local sign-in was cleared. Microsoft sign-out did not complete; close the tab if you are finished.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function headers() {
    if (!account || authRequired) throw new SignInRequiredError();
    return { Authorization: `Bearer ${await auth.getAccessToken(account)}` };
  }

  async function connect(event?: FormEvent) {
    event?.preventDefault();
    setNotice("");
    if (!account || authRequired || authBusy || requestPending.current) return;
    requestPending.current = true;
    setConnecting(true);
    try {
      const authorization = await headers();
      if (resumeId.trim()) {
        const response = await fetch(`${endpoint}/sessions/${encodeURIComponent(resumeId.trim())}`, {
          headers: authorization,
        });
        if (!response.ok) throw await responseError(response);
        const status = await response.json();
        setSessionId(status.session_id);
        setRevision(status.revision);
        setResumeId("");
        setNotice("Session resumed. Earlier messages are not loaded into this UI yet.");
      } else {
        const response = await fetch(`${endpoint}/sessions`, { method: "POST", headers: authorization });
        if (!response.ok) throw await responseError(response);
        const session = await response.json();
        setSessionId(session.session_id);
        setRevision(session.revision);
        setResumeId("");
        setMessages([]);
        setNotice("New session ready.");
      }
    } catch (error) {
      showError(error, "Could not connect. Confirm that your account has access and the agent API is available.");
    } finally {
      requestPending.current = false;
      setConnecting(false);
    }
  }

  async function send(event?: FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || busy || !sessionId || !account || authRequired || authBusy || requestPending.current) return;
    requestPending.current = true;
    setBusy(true);
    stoppingRef.current = false;
    let authorization: { Authorization: string };
    try {
      authorization = await headers();
    } catch (error) {
      requestPending.current = false;
      setBusy(false);
      showError(error, "Could not renew your sign-in. Try signing in again.");
      return;
    }
    if (stoppingRef.current) {
      requestPending.current = false;
      setBusy(false);
      setNotice("Response stopped.");
      return;
    }

    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    const runId = crypto.randomUUID();
    setDraft("");
    setNotice("");
    setMessages((current) => [
      ...current,
      { id: userId, role: "user", text },
      { id: assistantId, role: "assistant", text: "" },
    ]);
    setBusy(true);

    const agent = new HttpAgent({ url: `${endpoint}/ag-ui`, headers: authorization });
    agentRef.current = agent;
    stoppingRef.current = false;
    const stream = agent.run({
      threadId: sessionId,
      runId,
      messages: [{ id: userId, role: "user", content: text }],
      tools: [],
      context: [],
    });
    stream.subscribe({
      next: (event) => {
        if (event.type === "TEXT_MESSAGE_CONTENT") {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId ? { ...message, text: message.text + event.delta } : message,
            ),
          );
        } else if (event.type === "RUN_FINISHED") {
          const result = event.result as { revision?: number } | undefined;
          if (typeof result?.revision === "number") setRevision(result.revision);
          setNotice("Response complete.");
        } else if (event.type === "RUN_ERROR") {
          const message = errorMessage(event.code);
          setNotice(message);
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId && !item.text ? { ...item, text: message } : item,
            ),
          );
        }
      },
      error: () => {
        const message = stoppingRef.current
          ? "Response stopped. Uncommitted conversation changes were discarded."
          : "Connection interrupted. You can resume this session later.";
        setNotice(message);
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId && !item.text ? { ...item, text: message } : item,
          ),
        );
        setBusy(false);
        requestPending.current = false;
        agentRef.current = null;
      },
      complete: () => {
        setBusy(false);
        stoppingRef.current = false;
        agentRef.current = null;
        requestPending.current = false;
      },
    });
  }

  function stop() {
    stoppingRef.current = true;
    agentRef.current?.abortRun();
    setNotice("Stopping the active response…");
  }

  async function resetSession() {
    if (!sessionId || authBusy || requestPending.current || authRequired) return;
    requestPending.current = true;
    setBusy(true);
    agentRef.current?.abortRun();
    try {
      const response = await fetch(`${endpoint}/sessions/${encodeURIComponent(sessionId)}/reset`, {
        method: "POST",
        headers: await headers(),
      });
      if (!response.ok) throw await responseError(response);
      const result = await response.json();
      setRevision(result.revision);
      setMessages([]);
      setNotice("Conversation history cleared. Usage limits have not been reset.");
    } catch (error) {
      showError(error, "Could not clear the conversation. Check your access and try again.");
    } finally {
      requestPending.current = false;
      setBusy(false);
    }
  }

  async function copySessionId() {
    try {
      await navigator.clipboard.writeText(sessionId);
      setNotice("Session ID copied.");
    } catch {
      setNotice("Clipboard access is unavailable in this browser.");
    }
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  }

  return (
    <main className="app-shell">
      <aside className="rail" aria-label="Product navigation">
        <div className="brand-mark" aria-hidden="true">ab</div>
        <div className="rail-spacer" />
        <span className="rail-dot active" title="Movie guide" />
        <span className="rail-label">GUIDE</span>
        <div className="rail-spacer" />
        <span className="rail-foot">v0.1</span>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="breadcrumb"><span>AGENT BONES</span><i>/</i><strong>Movie guide</strong></div>
          <div className="session-actions">
          {account && <span>{account.name || account.username}</span>}
          {account && <button className="quiet-button" onClick={signOut} disabled={busy || authBusy || connecting}>Sign out</button>}
          <div className={`connection-pill ${sessionId ? "connected" : ""}`}>
            <span />{sessionId ? "SESSION ACTIVE" : "NOT CONNECTED"}
          </div>
          </div>
        </header>

        {!sessionId ? (
          <section className="connect-wrap">
            <div className="intro-kicker"><span className="sparkle">✳</span> YOUR PERSONAL MOVIE COMPANION</div>
            <h1>Find your next<br /><em>favorite story.</em></h1>
            <p className="intro-copy">Ask for recommendations, explore films, or find the right movie for tonight. Your conversation stays in your private session.</p>

            <form className="connect-card" onSubmit={connect}>
              <div className="card-heading"><div><span className="eyebrow">GET STARTED</span><h2>Connect to your agent</h2></div><span className="lock-icon">⌑</span></div>
              <p className="field-hint">Sign in with your organization’s Microsoft account to access your agent.</p>
              {(!account || authRequired) && <button className="primary-button connect-button" type="button" onClick={signIn} disabled={authBusy}>
                {authBusy ? "Signing in…" : authRequired ? "Sign in again" : "Sign in with Microsoft"}<span>↗</span>
              </button>}
              {account && !authRequired && <p className="field-hint">Signed in as {account.name || account.username}.</p>}
              <details className="resume-details">
                <summary>Resume an existing session</summary>
                <label htmlFor="session-id">Session ID</label>
                <input id="session-id" value={resumeId} onChange={(event) => setResumeId(event.target.value)} placeholder="Optional session UUID" />
              </details>
              {account && !authRequired && <button className="primary-button connect-button" type="submit" disabled={connecting || authBusy}>{connecting ? "Connecting…" : "Connect"} <span>↗</span></button>}
              {notice && <p className="notice" role="status">{notice}</p>}
            </form>
            <p className="privacy-note"><span>◈</span> Protected by your organization’s access policy</p>
          </section>
        ) : (
          <section className="chat-layout">
            <div className="conversation-heading">
              <div>
                <div className="intro-kicker"><span className="sparkle">✳</span> MOVIE GUIDE</div>
                <h1>Your next<br /><em>great watch.</em></h1>
              </div>
              <div className="session-actions">
                <span className="revision">REV {revision ?? 0}</span>
                <button className="quiet-button" onClick={copySessionId}>Copy session ID</button>
                <button className="quiet-button" onClick={resetSession} disabled={busy || authRequired || authBusy}>Clear chat</button>
                <button className="quiet-button" onClick={disconnect} disabled={busy || authBusy}>Disconnect</button>
              </div>
            </div>
            <div className="messages" aria-live="polite" aria-label="Conversation">
              {messages.length === 0 ? (
                <div className="welcome-card">
                  <span className="welcome-symbol">✳</span>
                  <p className="eyebrow">A GOOD PLACE TO START</p>
                  <h2>What are you in the mood for?</h2>
                  <div className="suggestions">
                    {["A clever, feel-good comedy", "Something like Arrival", "A great film under two hours"].map((item) => (
                      <button key={item} onClick={() => setDraft(item)}>{item}<span>↗</span></button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <article key={message.id} className={`message ${message.role}`}>
                    <div className="message-avatar">{message.role === "assistant" ? "✳" : "Y"}</div>
                    <div className="message-body">
                      <div className="message-meta">{message.role === "assistant" ? "MOVIE GUIDE" : "YOU"}</div>
                      <p>{message.text || (busy ? <span className="thinking">Thinking<span>.</span><span>.</span><span>.</span></span> : "")}</p>
                    </div>
                  </article>
                ))
              )}
            </div>
            <form className="composer" onSubmit={send}>
              <textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onComposerKeyDown} placeholder="Tell me what you’d like to watch…" rows={2} disabled={busy || authRequired || authBusy} aria-label="Message the movie guide" />
              <div className="composer-footer">
                <span>ENTER TO SEND <i>·</i> SHIFT + ENTER FOR A NEW LINE</span>
                {busy ? <button className="stop-button" type="button" onClick={stop}>Stop response <span>■</span></button> : <button className="send-button" type="submit" disabled={!draft.trim() || authRequired || authBusy}>Send <span>↗</span></button>}
              </div>
            </form>
            <div className="chat-footer"><span>Session <code>{sessionId.slice(0, 8)}…{sessionId.slice(-4)}</code></span><span>Responses may be imperfect. Check details before you decide.</span></div>
            {notice && <p className="notice chat-notice" role="status">{notice}</p>}
            {authRequired && <button className="primary-button" onClick={signIn} disabled={authBusy}>{authBusy ? "Signing in…" : "Sign in again"}</button>}
          </section>
        )}
      </section>
    </main>
  );
}
