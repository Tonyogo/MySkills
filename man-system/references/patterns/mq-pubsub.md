# Asynchronous Messaging & Event Mesh Patterns

This document defines target file matchers, code search patterns, and common failure points across message queues (Kafka, RabbitMQ, RocketMQ, NATS, Dapr Pub/Sub, MQTT).

---

## 1. File Matcher Globs (for `find_by_name`)
- **Dapr Subscriptions**: `**/components/**/*.yaml`, `**/*subscription*.yaml`
- **Listener / Consumer Classes**: `**/*Listener*.{java,kt,go}`, `**/*Consumer*.{java,go,py}`, `**/*Subscriber*.{java,go,py}`
- **Publisher / Producer Classes**: `**/*Producer*.{java,go,py}`, `**/*Publisher*.{java,go,py}`, `**/*Event*.{java,go,py}`

---

## 2. Code Search Regular Expressions (for `grep_search`)

### A. Kafka & RocketMQ
- **Kafka Publishers**: `kafkaTemplate\.send\s*\(`, `Producer\.send\s*\(`, `produce\s*\(`
- **Kafka Consumers**: `@KafkaListener\s*\(`, `consumer\.subscribe\s*\(`, `\.ReadMessage\s*\(`
- **RocketMQ Publishers**: `DefaultMQProducer\.send\s*\(`, `rocketMQTemplate\.syncSend\s*\(`
- **RocketMQ Consumers**: `@RocketMQMessageListener\s*\(`, `MessageListenerConcurrently`

### B. RabbitMQ & AMQP
- **RabbitMQ Publishers**: `rabbitTemplate\.(convertAndSend|send)\s*\(`, `channel\.basicPublish\s*\(`
- **RabbitMQ Consumers**: `@RabbitListener\s*\(`, `channel\.basicConsume\s*\(`

### C. NATS & NATS JetStream
- **NATS Publishers**: `(nc|js)\.Publish\s*\(\s*["'](?P<topic>[^"']+)["']`, `JetStream\.Publish`
- **NATS Subscribers**: `(nc|js)\.(Subscribe|QueueSubscribe)\s*\(\s*["'](?P<topic>[^"']+)["']`

### D. Dapr Pub/Sub & CloudEvents
- **Publishers**: `(client|dapr)\.(publish_event|PublishEvent)\s*\(\s*["'](?P<pubsub>[^"']+)["'],\s*["'](?P<topic>[^"']+)["']`
- **Subscribers**: `@app\.subscribe\s*\(`, `@dapr_app\.subscribe\s*\(`, `topic:\s*["'](?P<topic>[^"']+)["']`

### E. MQTT / Redis Streams
- **MQTT**: `client\.publish\s*\(`, `@MqttComponent`, `paho\.Client`
- **Redis PubSub / Streams**: `redisTemplate\.convertAndSend\s*\(`, `XADD`, `XREADGROUP`

---

## 3. MQ / Event Layer Failure Checklist (Phase 4 SOP)
1. **Topic / Channel Name Discrepancy**: Are producer and consumer topic names mismatched due to env prefixes (e.g. `dev.`, `prod.`)?
2. **Payload Serialization / Schema Evolution**: Is the consumer failing to unmarshal JSON/Protobuf due to unexpected field types?
3. **Consumer ACK / Dead Letter Queue**: Was the message acknowledged before processing completed or discarded to DLQ?
4. **Idempotency Check Collision**: Did the consumer de-duplication check falsely mark the message as already processed?
5. **Partition Key & Ordering**: Is message out-of-order execution breaking a state machine dependency?
