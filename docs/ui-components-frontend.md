# UI Component Inventory (Quick Scan)

_Component roots inspected: `frontend/app/components` and nested feature folders._

| Component | Category | Notes |
| --- | --- | --- |
| `LayoutWrapper` | Layout | Shell that wires navigation + auth guard |
| `Navigation` | Navigation | Likely renders sidebar/topbar links for Admin vs User |
| `ProtectedRoute` | Access Control | Wraps children & checks `AuthContext` |
| `PredictionStatusBanner` | KPI/Status | Surface-level indicator of latest AI batch health |
| `NewsImpact` | Data Visualization | Summaries AI commentary for top tickers |
| `evaluations/MetricBreakdownChart` | Chart | Renders evaluation metrics via Recharts |
| `evaluations/StockPerformanceTable` | Table | Comparison of stocks/time windows |

**Global Styling**
- Tailwind via `globals.css` + `tailwind.config.ts` (not shown) for utility classes.
- Iconography: `lucide-react` for consistent line icons.

**Next.js App Router Layouts**
- Route folders: `predictions`, `stocks`, `admin`, `ab-test`, `ab-config`, `login` each with page-level components.
- Shared context under `contexts/AuthContext.tsx` ensures SSR-safe session hydration.

Action: Define component-level props & skeleton states so API latency doesn’t break layout when deployed over WAN.
