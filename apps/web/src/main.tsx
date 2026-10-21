import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import { EntraAuth, readWebConfig } from "./auth";

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(<p role="status">Preparing sign-in…</p>);

async function start() {
  try {
    const config = readWebConfig(import.meta.env, window.location.origin);
    const auth = new EntraAuth(config);
    await auth.initialize();
    root.render(<React.StrictMode><App auth={auth} endpoint={config.endpoint} /></React.StrictMode>);
  } catch (error) {
    root.render(<main><h1>Sign-in unavailable</h1><p role="alert">{
      error instanceof Error && error.message.startsWith("Entra sign-in is not configured")
        ? error.message : "Check the web app's authentication and API configuration, then reload."
    }</p></main>);
  }
}

void start();
