# gRPC Services & Protocol Buffer Patterns

This document defines target file matchers, code search patterns, and common failure points across gRPC services and Protobuf definitions.

---

## 1. File Matcher Globs (for `find_by_name`)
- **Proto Schema Files**: `**/*.proto`
- **Generated Java Stubs**: `**/*Grpc.java`, `**/*OuterClass.java`
- **Generated Go Stubs**: `**/*_grpc.pb.go`, `**/*.pb.go`
- **Generated Python Stubs**: `**/*_pb2.py`, `**/*_pb2_grpc.py`
- **Generated TypeScript / C++ Stubs**: `**/*_pb.d.ts`, `**/*.pb.h`, `**/*.pb.cc`

---

## 2. Code Search Regular Expressions (for `grep_search`)

### A. Protocol Buffer Schema Definitions
- **Service & RPC Definitions**:
  - Service: `service\s+(?P<service>\w+)\s*\{`
  - RPC: `rpc\s+(?P<rpc>\w+)\s*\(\s*(?P<req>\w+)\s*\)\s*returns\s*\(\s*(?P<resp>\w+)\s*\)`

### B. Generated gRPC Client & Server Stubs
- **Java**:
  - Client Stub: `(?P<service>\w+)Grpc\.new(Blocking|Future|Async)?Stub\s*\(`
  - Server Base: `extends\s+(?P<service>\w+)ImplBase`
- **Go**:
  - Client Stub: `New(?P<service>\w+)Client\s*\(`
  - Server Registration: `Register(?P<service>\w+)Server\s*\(`
- **Python**:
  - Client Stub: `(?P<service>\w+)Stub\s*\(`
  - Server Registration: `add_(?P<service>\w+)Servicer_to_server\s*\(`
- **Node.js**:
  - Client Stub: `new\s+(?P<service>\w+)Client\s*\(`

---

## 3. gRPC Layer Failure Checklist (Phase 4 SOP)
1. **Schema Mismatch**: Has a proto field number or type changed without rebuilding generated stubs?
2. **Status Code Handling**: Is `grpc.StatusCode.DEADLINE_EXCEEDED` or `UNAVAILABLE` caught and logged?
3. **Metadata / Interceptor Stripping**: Are trace IDs or auth metadata forwarded in `Metadata` / `Context`?
4. **Channel Connection**: Is the client channel properly initialized with pooling or keepalive pings?
