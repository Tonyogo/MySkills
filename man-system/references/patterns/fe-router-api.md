# Frontend Communication, Routing & Micro-Frontend Patterns

This document defines target file matchers, code search patterns, and common failure points across frontend stacks (React, Vue, Angular, Qiankun, Wujie, Single-Spa, Vite, Webpack).

---

## 1. File Matcher Globs (for `find_by_name`)
- **API Definition / Request Files**: `**/api/**/*.{ts,js}`, `**/services/**/*.{ts,js}`, `**/request*.{ts,js}`, `**/client*.{ts,js}`
- **Router Configs**: `**/router*/**/*.{ts,js,vue,tsx}`, `**/routes/**/*.{ts,js,tsx}`, `**/App.{vue,tsx,jsx}`
- **Micro-Frontend Configs**: `**/micro*.{ts,js}`, `**/qiankun*.{ts,js}`, `**/wujie*.{ts,js}`, `**/federation*.{ts,js}`
- **Proxy & Environment Configs**: `vite.config.*`, `vue.config.*`, `webpack.*.js`, `.env*`

---

## 2. Code Search Regular Expressions (for `grep_search`)

### A. HTTP API Requests & Data Fetching
- **Axios Methods**:
  - Pattern: `axios\.(get|post|put|delete|patch)\s*\(\s*['"`](.*?)['"`]`
  - Instance creation: `axios\.create\s*\(\s*\{`
- **Native Fetch**:
  - Pattern: `fetch\s*\(\s*['"`](.*?)['"`]`
- **Data Fetching Hooks / Stores (TanStack Query / SWR / Redux Toolkit / Pinia / Zustand)**:
  - TanStack Query: `useQuery\s*\(\s*\{?` or `useMutation\s*\(\s*\{?`
  - SWR: `useSWR\s*\(\s*['"`](.*?)['"`]`
  - Redux Toolkit: `createAsyncThunk\s*\(\s*['"`](.*?)['"`]`
  - Pinia / Vue Action: `actions:\s*\{` or `async\s+function\s+\w+`

### B. Router Navigation & Micro-Frontends
- **Micro-Frontend Orchestration**:
  - Qiankun / Single-spa: `registerMicroApps\s*\(`, `loadMicroApp\s*\(`, `start\s*\(`
  - Wujie: `setupApp\s*\(`, `<WujieVue`, `<WujieReact`
- **Routing & Page Jump**:
  - React Router: `<Route\s+[^>]*path=['"`](.*?)['"`]`, `useNavigate\s*\(`, `history\.push\s*\(`
  - Vue Router: `router\.(push|replace)\s*\(`, `path:\s*['"`](.*?)['"`]`
  - Next.js / Nuxt: `router\.push\s*\(`, `navigateTo\s*\(`, `definePageMeta\s*\(`

### C. Proxy & BaseURL Configurations
- **Dev Server Proxies**:
  - Pattern: `proxy:\s*\{` or `['"`]/api['"`]:\s*\{`
- **BaseURL Configurations**:
  - Pattern: `baseURL:\s*` or `(process\.env|import\.meta\.env)\.\w+`

---

## 3. Frontend Layer Failure Checklist (Phase 4 SOP)
1. **Form / Event Triggers**: Is `preventDefault()` missing or is form validation blocking before dispatch?
2. **Payload Serialization**: Are object keys mapped correctly to backend DTO / CamelCase vs SnakeCase?
3. **Auth & Headers**: Is JWT Token or Tenant ID attached to the Axios request interceptor?
4. **Promise Rejection**: Is there an unhandled `.catch()` or silent `try-catch` swallowing network errors?
5. **Micro-Frontend Isolation**: Are styles or global variables leaking between child and parent applications?
