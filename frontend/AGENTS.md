# Frontend instructions

## Stack

React + TypeScript + Vite; API base configuration: `VITE_API_BASE_URL`, default same-origin `/api/v1`; Vite proxy to loopback backend port 8170, frontend dev port 5177.

Use a shared API client for base URL, headers/auth, timeout, response normalization, and errors. Keep UI pages, reusable components, and API modules understandable; add state management only when shared state calls for it. Cover loading, empty, validation, and failed-request states. Keep API types and calls synchronized with backend contracts.

Run `npm run build` (including TypeScript checking) for touched code. Do not embed secrets in browser code or claim a backend integration passed without exercising it.

Read root AGENTS, docs/API_CONTRACT.md and PRODUCT_UX.md first. All data from API; no business arrays embedded in UI. Decimal strings may be converted for chart display only, never for authoritative aggregation. Preserve null/zero and signed delta distinctions. Current navigation is three core management pages plus 来源与专题, which retains the old five-page workspace. Use Chinese, keyboard labels and responsive states. Data source/version/time badges remain visible. Never link a historical aggregate to synthetic detail without switching pages and explicit synthetic badge. For overview structure and rule conclusions, read docs/OVERVIEW_STRUCTURE_RULES.md; never sum turnover, recompute official shares or generate business conclusions in the browser.
