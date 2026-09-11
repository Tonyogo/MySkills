# Cross-Service Call & Communication Pattern Index

This document maps full-stack communication layers and tech stacks to their corresponding pattern reference files in `./patterns/`.

## Pattern File Routing Matrix

| Communication Paradigm / Tech Stack | Reference Pattern File |
| :--- | :--- |
| **Frontend UI / Router / API Fetchers / Micro-Frontends** | [`./patterns/fe-router-api.md`](./patterns/fe-router-api.md) |
| **Synchronous REST / HTTP Controllers / Feign / Dubbo** | [`./patterns/http-rest.md`](./patterns/http-rest.md) |
| **gRPC Services / Protocol Buffers** | [`./patterns/grpc-proto.md`](./patterns/grpc-proto.md) |
| **Asynchronous MQ / PubSub / Event Mesh** | [`./patterns/mq-pubsub.md`](./patterns/mq-pubsub.md) |

## Usage Rule for Full-Stack Analysis
When performing Phase 3 (Cross-Layer Call Chain Tracing) of the SOP pipeline, read only the specific pattern files relevant to the active stack identified in `service-map.md` to conserve context window tokens.
