import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { MethodologyPage } from "./MethodologyPage";
import "./styles.css";

const page = window.location.pathname === "/metodologia" ? <MethodologyPage /> : <App />;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>{page}</React.StrictMode>
);
