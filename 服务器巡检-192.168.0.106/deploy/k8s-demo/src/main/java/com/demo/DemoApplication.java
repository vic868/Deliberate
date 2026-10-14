package com.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

/**
 * demo-api 启动类。
 *
 * <p>这是一个"最小但完整"的 Spring Boot 业务服务，唯一目的是验证 106 上的两件事：
 * <ol>
 *   <li>无状态业务能不能顺利跑在 k3s 里（Deployment + 探针 + 优雅停机）；</li>
 *   <li>k3s 里的业务 Pod 能不能通过 Endpoints（而不是 127.0.0.1）连上宿主机 Docker 里的 MySQL/Redis。</li>
 * </ol>
 */
@SpringBootApplication
@ConfigurationPropertiesScan
public class DemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
