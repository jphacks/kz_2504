import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import ErrorBoundary from "./components/ErrorBoundary";

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("Root element #root not found");
}

// Debug: trace programmatic navigations to find unexpected redirects
// (temporary helper — remove after debugging)
(function () {
  try {
    const wrap = (name: "pushState" | "replaceState") => {
      const orig = (window.history as any)[name];
      (window.history as any)[name] = function (...args: any[]) {
        try {
          // args[0] is state, args[2] is the url
          const url = args[2];
          console.groupCollapsed(`[nav-debug] history.${name} ->`, url);
          console.trace();
          console.groupEnd();
        } catch (e) {
          // noop
        }
        return orig.apply(this, args);
      };
    };
    wrap("pushState");
    wrap("replaceState");
    window.addEventListener("popstate", () => {
      try {
        console.groupCollapsed("[nav-debug] popstate event");
        console.trace();
        console.groupEnd();
      } catch {}
    });
  } catch (e) {
    // ignore
  }
})();

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
