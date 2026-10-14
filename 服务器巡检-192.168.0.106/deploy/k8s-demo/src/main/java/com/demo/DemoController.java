package com.demo;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 验证用接口。
 *
 * <p>设计要点：每个接口都返回"真实探测结果"而不是写死的 200，
 * 这样在 k3s 里一调就知道"业务起来了没 / 能不能连上 Docker 中间件"。
 */
@RestController
@RequestMapping("/api")
public class DemoController {

    private static final Logger log = LoggerFactory.getLogger(DemoController.class);

    private final JdbcTemplate jdbc;
    private final StringRedisTemplate redis;

    public DemoController(JdbcTemplate jdbc, StringRedisTemplate redis) {
        this.jdbc = jdbc;
        this.redis = redis;
    }

    /** 存活/就绪：不依赖任何外部组件，保证能被 K8s 探针安全调用。 */
    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("status", "UP");
        m.put("service", "demo-api");
        m.put("pod", System.getenv().getOrDefault("HOSTNAME", "unknown"));
        m.put("time", LocalDateTime.now().toString());
        return m;
    }

    /** 回显：验证 Ingress 路由 / 参数透传是否正确（看 pod 字段就知道打到哪个副本）。 */
    @GetMapping("/echo/{msg}")
    public Map<String, Object> echo(@PathVariable String msg) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("echo", msg);
        m.put("pod", System.getenv().getOrDefault("HOSTNAME", "unknown"));
        return m;
    }

    /** 探测 MySQL（对应 Docker 里的 3306）。 */
    @GetMapping("/db")
    public Map<String, Object> db() {
        Map<String, Object> m = new LinkedHashMap<>();
        try {
            Integer one = jdbc.queryForObject("SELECT 1", Integer.class);
            String version = jdbc.queryForObject("SELECT VERSION()", String.class);
            m.put("mysql", "OK");
            m.put("select1", one);
            m.put("version", version);
        } catch (Exception e) {
            log.warn("MySQL 探测失败", e);
            m.put("mysql", "FAIL");
            m.put("error", e.getClass().getSimpleName() + ": " + e.getMessage());
        }
        m.put("pod", System.getenv().getOrDefault("HOSTNAME", "unknown"));
        return m;
    }

    /** 探测 Redis（对应 Docker 里的 6379）：写一个带 TTL 的计数器。 */
    @GetMapping("/redis")
    public Map<String, Object> redis() {
        Map<String, Object> m = new LinkedHashMap<>();
        try {
            Long n = redis.opsForValue().increment("demo:counter");
            redis.expire("demo:counter", 5, TimeUnit.MINUTES);
            m.put("redis", "OK");
            m.put("counter", n);
        } catch (Exception e) {
            log.warn("Redis 探测失败", e);
            m.put("redis", "FAIL");
            m.put("error", e.getClass().getSimpleName() + ": " + e.getMessage());
        }
        m.put("pod", System.getenv().getOrDefault("HOSTNAME", "unknown"));
        return m;
    }
}
