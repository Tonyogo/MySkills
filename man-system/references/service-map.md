# Full-Stack Service Map Index (Preset Reference & Template)

> **Note**: This index serves as the default architecture reference (Yogo Fleet & Platform) and template for the `man-system` skill.
> **Auto-update command**: `python3 <skill_dir>/scripts/scan_services.py <workspace_dir> -o <target_service_map_path>`
> **Last updated**: 2026-08-26

---

## 🌐 1. Frontend Applications & Micro-Frontends (`fe-spf/`)

### Micro-Frontend Shell & Base Frameworks
- **`robot-main-app`**: Parent `qiankun` micro-frontend shell. Orchestrates sub-apps, manages auth, navigation, and global layout.
- **`yogo-lib`**: Shared UI component and service library (`@yogo/robot-component`, `@yogo/web-component`, `@yogo/meteor-service`).
- **`yogo-i18n`**: Internationalization scanning and translation toolchain.

### Admin & Operations Terminals
- **`ibuilding-admin`**: Central Smart Building / Operations Management panel (React 17, Vite, AntD v5, MobX).
- **`ispace-admin`**: Property management dashboard for iSpace line.
- **`web-espace` / `web-moss` / `web-babata`**: Custom corporate workspaces and business intelligence dashboards.

### Cockpit & 3D Visualization
- **`yogo-eye`**: 3D Robot fleet monitoring cockpit (React, Redux, Three.js).
- **`lucky-clover` & `lucky-clover-controller`**: Digital twin screen & physical asset controller.
- **`slime`**: Shared 2D canvas & floorplan mapping engine core.

### Map & Scanning Tools (Chur Series)
- **`chur` / `chur-pc` / `chur-robot`**: Lidar map collection, pathing editor, and visualization framework.
- **`desktop-groot-chur` / `micro-app-groot-chur`**: Electronic map scanning and grid editors.

### Dispatch & Field Workbenches (Groot & Lucy Series)
- **`micro-groot`**: Operational terminal interface base app.
- **`micro-app-groot-imp` / `micro-app-implement`**: Technician deployment and site calibration assistant.
- **`wx-groot-blacknight` / `jarvis-blackknight`**: Field installation & hardware calibrator workbench.
- **`lucy` / `lucy-ui` / `lucy-wx`**: Delivery & dispatching terminals (Web, Mini-Program for security/courier).

### Customer & Storefront Apps
- **`customer-app`**: WeChat Mini-Program for parcel delivery, pickup, and tracking.
- **`shop-app` / `mobile-app-shop`**: Merchant order & menu management terminals.
- **`takeaway-ui` / `rider-app` / `wx-delivery`**: Express takeaway delivery and courier interfaces.

### On-Robot OS & Screens
- **`luna-app` / `luna2-app`**: Interactive touchscreen UI mounted on physical robots.
- **`robot-app-os` / `robot-app-selfcheck` / `robot-app-setpoints`**: Native client overlays, diagnosis tools, and setpoint calibrators.

---

## 🚪 2. Gateways & BFF Layer (`cloud/` & `yogosystem/`)

- **`jarvis-dobby-api`**: Modern FastAPI BFF service. Handles API dispatch, WebSocket feeds, log queries, and proxies unhandled routes via Dapr (`gw_proxy`).
- **`jarvis-dobby`**: Legacy Python `gosau` BFF service with Go proxy gateway (`gateway/jarvis-dobby-gw`).
- **`app-openapi`**: Cloud public OpenAPI Gateway for third-party client integrations.
- **`app-gw`**: Gateway proxy module routing traffic between cloud REST/gRPC handlers.

---

## ⚙️ 3. Core Backend Microservices

### Cloud Business Layer (`cloud/`)
- **`young`**: Flagship Go microservice built on DDD + Clean Architecture (Huma v2 / Chi v5 + pgx/sqlc). Domains: Site (topology), Delivery (task execution), Unit (robot trackers), Schedule.
- **`app-dispatch` / `app-delivery`**: Takeaway dispatching pipeline and order delivery queues.
- **`app-user`**: User management, staff records, RBAC permissions, and WeChat OAuth authentication.
- **`app-pay`**: Payment checkout, payment gateway integration, and refund handling.
- **`app-shop` / `app-mall`**: Merchant store registration, catalogs, shopping carts, and promotional coupons.
- **`notification`**: SMS, WeChat template messages, and email notification gateway.
- **`adam`**: Long-running cloud transaction task scheduler.
- **`app-event`**: Audit trail and cloud event logs repository.

### Smart Platform Foundation / Fleet Core (`yogosystem/`)
- **`jarvis-unit`**: Core Python FastAPI scheduling engine. Resolves robot routes, command lifecycles, and fleet state.
- **`jarvis-site`**: Building topology, floorplans, elevator integration endpoints, and location anchors.
- **`jarvis-cmdb`**: Asset catalog managing robot serial numbers, specifications, and lifecycle states.
- **`jarvis-auth`**: Central IoT authentication and device certificate manager.
- **`jarvis-algorithm`**: Path planning, costmaps, and navigation math engine (C++ / OpenCV binaries via Conan).
- **`jarvis-geo`**: Coordinates transforms, geofencing, and virtual barrier calculations.
- **`jarvis-alarm`**: Anomalies & alert dispatcher subscribing to telemetry streams.
- **`jarvis-ticket`**: Operations trouble ticketing and maintenance scheduling.

---

## 🔌 4. Device & IoT Integration Layer (`yogosystem/`)

- **`xiot-server`**: High-throughput Go gateway & TCP/WebSocket broker interfacing with physical hardware. Includes Java Spring Boot subproject for elevator protocol integration.
- **`xthings-server` / `jarvis-things`**: Hardware telemetry translators converting device messages to standard Dapr representations.
- **`jarvis-codec`**: Custom network datagram binary encoder/decoder.
- **`jarvis-agent`**: Client daemon running directly on the robot's local x86/ARM PC.

---

## 📨 5. Distributed Event Mesh & Communication Topology

- **Dapr Pub/Sub (Business Events)**:
  - Component topics: `site-report-events`, `things-report-unit-metrics`, `things-report-unit-events`, `alarm-report`, `simcard-report-events`.
  - Used for decoupled inter-service notifications (e.g. state transitions, payments, alarms).
- **NATS / NATS JetStream (High-Frequency IoT Streams)**:
  - Sub-millisecond telemetry, sensor streams, path calibration, and obstacle avoidance signals.
- **Kafka (Audit Logs & Analytics)**:
  - Auditable transaction logs (`app-event`), BI data pipelines (`jarvis-bi`), and failure anomaly tracking (`jarvis-alarm`).
