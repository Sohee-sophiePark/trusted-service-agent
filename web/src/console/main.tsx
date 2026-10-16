import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ConsoleApp from "./ConsoleApp";
import "../index.css";

createRoot(document.getElementById("root")!).render(<StrictMode><ConsoleApp /></StrictMode>);
