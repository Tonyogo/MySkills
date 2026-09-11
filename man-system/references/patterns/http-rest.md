# Synchronous HTTP/REST, RPC & Gateway Routing Patterns

This document defines target file matchers, code search patterns, and common failure points across synchronous HTTP controllers, RPC frameworks, gateway routing, and database transactions.

---

## 1. File Matcher Globs (for `find_by_name`)
- **Controllers & Handlers**: `**/*Controller*.{java,kt,go,cs}`, `**/handler*/**/*.{go,py,ts}`, `**/routes/**/*.{py,js,ts}`
- **RPC & Feign Clients**: `**/*Client*.{java,go,py}`, `**/*Service*.{java,go,py}`, `**/*Dubbo*.{java,go}`
- **Gateway Route Configs**: `application*.{yml,yaml,properties}`, `**/routes.json`, `**/nginx*.conf`, `**/kong*.yaml`
- **Database / DAO / Repository**: `**/*Repository*.{java,go}`, `**/*Mapper*.{java,xml}`, `**/*dao*/**/*.{go,py}`

---

## 2. Code Search Regular Expressions (for `grep_search`)

### A. Controller API Endpoints
- **Java Spring Boot / MVC**:
  - All Mapping annotations: `@(Get|Post|Put|Delete|Patch|Request)Mapping`
  - Explicit path regex: `@(Get|Post|Put|Delete|Patch|Request)Mapping\s*(\(\s*(value\s*=\s*|path\s*=\s*)?["'](?P<path>[^"']+)["'])?`
- **Python FastAPI / Flask / Django**:
  - FastAPI / Flask: `@(app|router)\.(get|post|put|delete|patch)\s*\(\s*["'](?P<path>[^"']+)["']`
  - Django: `path\s*\(\s*["'](?P<path>[^"']+)["']`
- **Go Chi / Gin / Fiber / Echo / Huma**:
  - Gin / Chi / Echo: `\.(GET|POST|PUT|DELETE|PATCH|Get|Post|Put|Delete)\s*\(\s*["'](?P<path>[^"']+)["']`
  - Huma (v2): `huma\.Register\s*\(` or `huma\.Operation`
- **Node.js Express / NestJS**:
  - Express: `(app|router)\.(get|post|put|delete|patch)\s*\(\s*["'](?P<path>[^"']+)["']`
  - NestJS: `@(Controller|Get|Post|Put|Delete|Patch)\s*\(`
- **Rust (Axum / Actix-web)**:
  - Axum: `\.route\s*\(\s*["'](?P<path>[^"']+)["']`
  - Actix: `#\[(get|post|put|delete)\s*\(\s*["'](?P<path>[^"']+)["']`

### B. Inter-Service RPC & Declarative Clients
- **Dubbo RPC (Java / Go)**:
  - Java: `@DubboReference`, `@DubboService`, `<dubbo:reference`
  - Go: `config\.SetConsumerService\(` or `hessian\.RegisterPOJO\(`
- **Spring Cloud OpenFeign**:
  - `@FeignClient\s*\(\s*(value\s*=\s*|name\s*=\s*)?["'](?P<name>[^"']+)["']`
- **Dapr Direct Service Invocation**:
  - `invoke_method\s*\(` or `InvokeMethod\s*\(`
- **HTTP Client Instances**:
  - Go Resty / http: `http\.NewRequest\s*\(`, `resty\.(New|R)\s*\(`
  - Python HTTPX / Requests: `httpx\.(AsyncClient|Client)`, `requests\.(get|post|put|delete)`

### C. Gateway Routing & Path Rewrites
- **Spring Cloud Gateway**:
  - Predicate: `Path\s*=\s*(?P<path>[^\n]+)`
  - Rewrite: `RewritePath\s*=`
- **Nginx / Ingress / Envoy**:
  - `location\s+(?P<path>[^\s{]+)`

### D. DB Transactions & Locking
- **Java (Spring / JPA / MyBatis)**: `@Transactional`, `TransactionTemplate`, `rollbackFor`
- **Go (GORM / pgx / sqlc)**: `\.Begin\(`, `\.Commit\(`, `\.Rollback\(`
- **Python (SQLAlchemy / Django)**: `session\.commit\(`, `@transaction\.atomic`
- **Distributed Locks (Redis / Redisson)**: `redissonClient\.getLock\(`, `\.SetNX\(`, `opsForValue\(\)\.setIfAbsent`

---

## 3. Backend Layer Failure Checklist (Phase 4 SOP)
1. **Routing & Filter Mismatches**: Is the gateway stripping auth tokens or failing rewrite path rules?
2. **RPC Timeout / Fallback**: Is Dubbo/Feign client timing out without logging stack trace?
3. **Database Transaction Rollback**: Did a downstream error cause silent rollback without throwing HTTP 500?
4. **State Machine Deadlock**: Is the entity status check (e.g. `order.status == PENDING`) preventing the update?
5. **Distributed Lock Timeout**: Did `SetNX` fail to acquire lock or expire prematurely?
