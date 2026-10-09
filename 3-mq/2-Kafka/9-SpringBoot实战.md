---
title: Kafka SpringBoot 实战
tags: [MQ, Kafka, SpringBoot, 实战, 代码]
status: 进行中
created: 2026-10-09
---

# 🧩 八、Spring Boot 集成 Kafka 实战

> 本篇是**能直接抄进项目**的落地手册：依赖、配置、发送、消费、异常与重试、死信、事务，以及那些"配置看起来没问题、上线才发现踩坑"的细节。
> 关联：[[1-Kafka总览]]、[[3-生产者原理]]（参数原理）、[[4-消费者与Rebalance]]（位移与 rebalance）、[[6-事务与Exactly-Once]]（事务原理）。

---

## 一、依赖与版本对应

```xml
<!-- Spring Boot 3.x 项目 -->
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>
    <!-- 版本由 spring-boot-dependencies 统一管理，无需手写 -->
</dependency>
```

| Spring Boot | spring-kafka | kafka-clients | JDK |
|---|---|---|---|
| 2.7 / 2.8 | 2.8 / 2.9 | 3.x | 8+ |
| 3.0 ~ 3.2 | 3.0 ~ 3.2 | 3.3 ~ 3.6 | **17+** |
| 3.3 / 3.4 | 3.2 / 3.3 | 3.7 / 3.8 | 17+ |
| 4.0 | 4.0 | 4.x | 17+ |

> [!warning] 别手动指定 kafka-clients 版本
> `spring-kafka` 通过 `spring-boot-dependencies` 锁定了兼容的 `kafka-clients` 版本。手写 `<version>` 极易造成客户端与服务端（或 Spring Kafka 内部 API）不兼容。要升级就升 Spring Boot 版本。

---

## 二、最小可用配置

```yaml
spring:
  kafka:
    bootstrap-servers: kafka1:9092,kafka2:9092,kafka3:9092
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
      acks: all                          # 可靠性基线
      retries: 3
      properties:
        enable.idempotence: true         # 幂等生产者，防重防乱序
        max.in.flight.requests.per.connection: 5
        linger.ms: 20                    # 攒批，换吞吐
        batch.size: 32768
        compression.type: lz4
    consumer:
      group-id: order-service
      auto-offset-reset: earliest
      enable-auto-commit: false          # 关闭自动提交，改手动/容器提交
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      max-poll-records: 200              # 单次拉取条数，配合处理耗时
      properties:
        spring.json.trusted.packages: com.example.dto
        isolation.level: read_committed  # 需要事务语义时
    listener:
      ack-mode: manual_immediate         # 手动提交，见 §6
      concurrency: 3                     # 并发消费者数（≤ 分区数）
```

> [!tip] 三个最容易漏的配置
> 1. `enable-auto-commit: false` —— 自动提交在"处理完之前"就提交了位移，进程崩溃即**丢消息**。
> 2. `spring.json.trusted.packages` —— 不配会反序列化失败（安全限制），JsonDeserializer 必备。
> 3. `listener.ack-mode` —— 决定位移提交时机，默认 `BATCH` 与直觉不符（见 §6）。

---

## 三、发送消息

### 3.1 基础与异步回调

```java
@Service
@RequiredArgsConstructor
public class OrderEventProducer {

    private final KafkaTemplate<String, Object> kafkaTemplate;

    /** 以订单号为 key —— 保证同一订单的事件落同一分区，从而分区内有序 */
    public void sendOrderCreated(OrderCreatedEvent event) {
        kafkaTemplate.send("order-events", event.getOrderId(), event)
            .whenComplete((result, ex) -> {
                if (ex != null) {
                    // 必须处理！否则消息静默丢失
                    log.error("send failed, orderId={}", event.getOrderId(), ex);
                    // 落本地重试表 / 告警 / 补偿
                } else {
                    var meta = result.getRecordMetadata();
                    log.debug("sent ok partition={} offset={}",
                              meta.partition(), meta.offset());
                }
            });
    }
}
```

> [!danger] 异步发送不处理回调 = 静默丢消息
> `send()` 返回 `CompletableFuture`，异常**不会**抛到调用方。业务代码里只 `send()` 不处理回调，是最常见的隐性丢消息源头。要么处理回调，要么改用同步发送（见下）。

### 3.2 同步发送（强一致场景）

```java
public void sendSync(String topic, String key, Object value) {
    try {
        // get() 会阻塞直到 broker 确认，抛异常即失败
        kafkaTemplate.send(topic, key, value).get(3, TimeUnit.SECONDS);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new IllegalStateException("interrupted while sending", e);
    } catch (ExecutionException | TimeoutException e) {
        throw new KafkaSendException("send failed: " + topic, e);
    }
}
```

| 方式 | 吞吐 | 可靠性 | 适用 |
|---|---|---|---|
| 异步 + 回调 | 高 | 依赖回调实现 | **绝大多数场景** |
| 同步 `.get()` | 低（每次等 RTT） | 直观，失败即异常 | 强一致、低频、需要立即确认 |

### 3.3 跨分区原子写（事务）

```java
@Bean
public KafkaTransactionManager<String, Object> kafkaTransactionManager(
        ProducerFactory<String, Object> pf) {
    return new KafkaTransactionManager<>(pf);
}

@Transactional("kafkaTransactionManager")
public void sendAtomically(String orderId, OrderCreatedEvent created,
                           OrderPaidEvent paid) {
    kafkaTemplate.send("order-events", orderId, created);
    kafkaTemplate.send("order-events", orderId, paid);   // 要么都成功，要么都回滚
}
```

> 事务原理、`transactional.id`、fencing 与 LSO 的代价见 [[6-事务与Exactly-Once]]。注意：**跨到数据库就不是事务了**，Kafka 事务只覆盖 Kafka 内部写入。

---

## 四、消费消息

### 4.1 基础监听

```java
@Component
@Slf4j
public class OrderEventConsumer {

    @KafkaListener(
        topics = "order-events",
        groupId = "order-service",
        concurrency = "3"          // 3 个消费线程 = 3 个 Consumer
    )
    public void onMessage(ConsumerRecord<String, OrderCreatedEvent> record,
                          Acknowledgment ack) {
        try {
            orderService.handle(record.value());
            ack.acknowledge();          // 业务成功后才提交位移
        } catch (Exception e) {
            log.error("handle failed, offset={}", record.offset(), e);
            // 不 acknowledge → 触发重试/死信（见 §5）
            throw e;                    // 必须抛出，容器才能感知失败
        }
    }
}
```

### 4.2 批量消费

```java
@Bean
public ConcurrentKafkaListenerContainerFactory<String, Object> batchFactory(
        ConsumerFactory<String, Object> cf) {
    var factory = new ConcurrentKafkaListenerContainerFactory<String, Object>();
    factory.setConsumerFactory(cf);
    factory.setBatchListener(true);                    // 开启批量
    factory.setConcurrency(3);
    factory.getContainerProperties().setAckMode(
        ContainerProperties.AckMode.MANUAL_IMMEDIATE);
    return factory;
}

@KafkaListener(topics = "order-events", containerFactory = "batchFactory")
public void onBatch(List<ConsumerRecord<String, OrderCreatedEvent>> records,
                    Acknowledgment ack) {
    orderService.handleBatch(records.stream().map(ConsumerRecord::value).toList());
    ack.acknowledge();      // 整批成功才提交（批内一条失败会整批重放）
}
```

> [!warning] 批量消费的取舍
> 批量 + 手动提交能显著提高吞吐，但**批内一条失败会导致整批重放**，对幂等要求更高。若业务无法容忍整批重放，请退化为单条消费，或在批内自行捕获并记录失败明细（部分成功不可回滚）。

### 4.3 手动分配分区 / 从指定位移消费

```java
@KafkaListener(topicPartitions = @TopicPartition(
        topic = "order-events",
        partitionOffsets = @PartitionOffset(partition = "0", initialOffset = "0")))
public void onPartitionZero(ConsumerRecord<String, OrderCreatedEvent> record) {
    // 常用于：指定分区重放、数据修复、按分区灰度
}
```

### 4.4 `concurrency` 怎么定

| 原则 | 说明 |
|---|---|
| `concurrency ≤ 分区数` | 超出部分**空转**（不报错但不消费） |
| 与处理类型匹配 | CPU 密集 ≈ 核数；IO 密集可适当放大 |
| 单实例视角 | `concurrency` 是**每个应用实例**的线程数，总并行度 = 实例数 × concurrency，仍受分区数封顶 |

---

## 五、异常处理：重试与死信

### 5.1 默认行为

`DefaultErrorHandler` 默认**重试 9 次**（间隔 1s，可配 backoff），仍失败则**记录日志并跳过**（提交位移继续往下走）——这往往是"消息悄悄没了"的原因。

### 5.2 配置重试 + 死信 Topic（推荐）

```java
@Bean
public DefaultErrorHandler errorHandler(KafkaTemplate<String, Object> template) {
    // 重试 3 次，间隔 1s
    var backOff = new FixedBackOff(1000L, 3L);

    // 重试耗尽后投递到死信 topic: order-events.DLT
    var recoverer = new DeadLetterPublishingRecoverer(template,
        (record, ex) -> new TopicPartition(record.topic() + ".DLT", record.partition()));

    var handler = new DefaultErrorHandler(recoverer, backOff);

    // 这些异常不重试，直接进死信（重试也没意义）
    handler.addNotRetryableExceptions(
        DeserializationException.class,
        IllegalArgumentException.class);

    return handler;
}

@Bean
public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory(
        ConsumerFactory<String, Object> cf, DefaultErrorHandler errorHandler) {
    var factory = new ConcurrentKafkaListenerContainerFactory<String, Object>();
    factory.setConsumerFactory(cf);
    factory.setCommonErrorHandler(errorHandler);   // 关键：挂上去
    return factory;
}
```

| 策略 | 行为 | 适用 |
|---|---|---|
| 默认 | 重试 9 次后**跳过** | 仅适合可丢消息 |
| 重试 + DLT | 重试耗尽后转死信，**不丢** | **生产推荐** |
| 无限重试（`FixedBackOff(ms, UNLIMITED)`） | 阻塞该分区直到成功 | 强顺序且不容丢失，需配告警 |

> [!tip] 死信 Topic 的三个配套
> ① 死信 Topic 的**分区数要与源 Topic 一致**（`DeadLetterPublishingRecoverer` 默认按原分区投递，分区数不足会落到可用分区）；② 死信要有人看——配监控与告警；③ 死信消息带上原始异常与重试次数（用 Header 记录）便于定位。

---

## 六、位移提交：`ack-mode` 必须搞清楚

`spring.kafka.listener.ack-mode` 决定"什么时候提交位移"，这是**最容易被误解**的配置：

| AckMode | 提交时机 | 风险 |
|---|---|---|
| `RECORD` | 每条记录处理完后提交 | 频繁提交，吞吐低 |
| `BATCH`（**默认**） | 本轮 `poll()` 的所有记录都处理完后提交 | 与直觉相符但依赖"监听器不抛异常" |
| `TIME` | 按 `ackTime` 周期提交 | 崩溃可能丢一批 |
| `COUNT` | 累计 N 条提交 | 同上 |
| `COUNT_TIME` | 条数或时间任一满足 | 同上 |
| `MANUAL` | 调用 `acknowledge()` 后，**下次 poll 时**提交 | 提交有延迟 |
| `MANUAL_IMMEDIATE` | 调用 `acknowledge()` 后**立即**提交 | 提交频繁，但语义最清晰 |

> [!important] MANUAL 与 MANUAL_IMMEDIATE 的区别
> `MANUAL` 只是把位移**记账**，真正提交发生在**下一次 `poll()`**；`MANUAL_IMMEDIATE` 则当场调用 `commitSync`。
> 要"处理成功即落地"的语义，选 **`MANUAL_IMMEDIATE`**；要减少提交开销、能接受一点延迟窗口，选 `MANUAL`。
> 无论哪种，**都不应该在业务处理前提交**——那等于 at-most-once。

---

## 七、Rebalance 与位移治理

```java
@Bean
public ConsumerFactory<String, Object> consumerFactory(KafkaProperties props) {
    var cf = new DefaultKafkaConsumerFactory<>(props.buildConsumerProperties(null));

    // 分区被回收前提交位移，减少重复消费
    cf.addListener(new ConsumerRebalanceListener() {
        @Override
        public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
            // 若用容器管理位移，Spring 会代为提交；此处用于释放资源/刷缓冲
            log.warn("partitions revoked: {}", partitions);
        }
        @Override
        public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
            log.warn("partitions assigned: {}", partitions);
        }
    });
    return cf;
}
```

减少 Rebalance 的工程手段（原理见 [[4-消费者与Rebalance]]）：

| 手段 | 做法 | 效果 |
|---|---|---|
| 拉长处理窗口 | 调大 `max.poll.interval.ms` | 避免"处理太慢被踢" |
| 减少单批条数 | 调小 `max-poll-records` | 缩短单轮处理时间 |
| 异步化处理 | 拉取与处理解耦（注意位移语义） | 保持 `poll` 心跳及时 |
| 静态成员 | `group.instance.id` 唯一固定 | 重启不触发 rebalance |
| 协作式分配 | `partition.assignment.strategy=CooperativeStickyAssignor` | 不必全量 STW |

> [!warning] 处理逻辑异步化的陷阱
> 把 `poll` 到的消息丢给线程池后**立刻提交位移**，等价于 at-most-once：任务还没跑完，进程崩溃就丢了。正确做法是"任务完成后回传再提交"，或采用"拉取线程只负责拉、处理后按分区顺序提交"的模型，并严格处理各分区位移的**连续性**。

---

## 八、可靠性配置基线（生产 Checklist）

| 环节 | 配置 | 作用 |
|---|---|---|
| 生产 | `acks=all` | 等 ISR 全部确认 |
| 生产 | `enable.idempotence=true` | 防重、防乱序 |
| 生产 | `retries` + `delivery.timeout.ms` | 重试到底，且总时长可控 |
| 生产 | 回调必处理 / 同步发送 | 失败可见 |
| Broker | `replication.factor=3`、`min.insync.replicas=2` | 容忍 1 副本故障仍可写 |
| Broker | `unclean.leader.election.enable=false` | 不用可能落后的副本当 leader |
| Broker | `auto.create.topics.enable=false` | 防手误创建错误分区数的 Topic |
| 消费 | `enable-auto-commit=false` | 位移由业务决定 |
| 消费 | `ack-mode=MANUAL_IMMEDIATE` | 处理成功才提交 |
| 消费 | 重试 + 死信 | 不静默丢消息 |
| 业务 | **幂等处理** | Kafka 只能 at-least-once，重复必须靠业务兜底 |

> [!abstract] 一句话记住
> **Kafka 侧做到 at-least-once 是工程能力问题，做到"不重复"是业务能力问题。**

---

## 九、常见坑速查

| 坑 | 现象 | 正解 |
|---|---|---|
| 异步 `send` 不管回调 | 消息静默丢失，日志无异常 | 处理 `whenComplete` 或改同步 |
| 自动提交位移 | 崩溃后消息丢失 | `enable-auto-commit=false` + 手动提交 |
| 先提交后处理 | 处理失败但位移已提交 → 丢 | **处理成功后再 `acknowledge()`** |
| `JsonDeserializer` 未配信任包 | 反序列化报错 | 配 `spring.json.trusted.packages` |
| `concurrency` > 分区数 | 有线程空转，以为配置生效了 | 并发数不超过分区数，或先扩分区 |
| 处理耗时 > `max.poll.interval.ms` | 频繁 rebalance、重复消费激增 | 调大该参数或减少 `max-poll-records` |
| 监听器吞异常不抛 | 失败被当成功，位移照提交 | **必须抛出**，交给 ErrorHandler |
| 批量消费部分失败 | 整批重放，重复量大 | 保证幂等，或改单条消费 |
| 事务 Topic 与普通消费混用 | 读到未提交数据 | 消费者设 `isolation.level=read_committed` |
| 用 `@Transactional` 混数据库事务 | 以为原子，其实不一致 | 需业务补偿/本地消息表（见 [[6-事务与Exactly-Once]]） |

---

## 十、动手验证

```bash
# 1) 消费者组与 Lag（验证 §7 的并发与 Lag）
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group order-service

# 2) 重置位移（修复数据时常用；需先停掉消费者）
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group order-service --topic order-events \
  --reset-offsets --to-earliest --execute

# 3) 查看死信 Topic 是否真的收到了消息
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic order-events.DLT --from-beginning \
  --property print.headers=true
```

**建议的自测项**：
- [ ] 制造一次业务异常，确认消息进了 `.DLT` 而不是被跳过
- [ ] 处理中 kill -9 进程，重启确认**没有丢消息**（可能重复，验证幂等）
- [ ] 把 `concurrency` 调到大于分区数，观察是否真的有空转
- [ ] 消费端从 `earliest` 重放，确认业务幂等生效

---
> 上一篇 → [[8-性能优化与高吞吐原理]] ｜ 下一篇 → [[10-面试高频题]]
