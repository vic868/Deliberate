# Logback 集成 Spring Boot 完整步骤

## 一、背景说明

Spring Boot 默认使用 **Logback** 作为日志实现框架，无需额外添加依赖。`spring-boot-starter-web` 或 `spring-boot-starter` 中已经传递引入了 `logback-classic`。

当前项目环境：
- Spring Boot：**4.1.1**
- Java：**17**
- 构建工具：**Maven**
- Logback 版本：由 Spring Boot Parent POM 管理（当前为 1.5.x+）

---

## 二、依赖确认

打开 `pom.xml`，确保有以下 starter（任意一个即可传递引入 logback）：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>
```

如果项目排除了 logback 或使用了其他日志框架（如 log4j2），需要显式加入：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-logging</artifactId>
</dependency>
```

---

## 三、配置文件放置

### 3.1 文件名约定

Spring Boot 会按以下优先级自动加载 logback 配置文件：

| 优先级 | 文件路径 | 说明 |
|-------|---------|------|
| 1 | `classpath:logback-test.xml` | 仅测试环境生效 |
| 2 | `classpath:logback.xml` | 默认配置文件 |
| 3 | `classpath:logback-spring.xml` | 推荐，支持 Spring Profile |

### 3.2 推荐使用 `logback-spring.xml`

`logback-spring.xml` 相比 `logback.xml` 有以下增强能力：

- 支持 `<springProfile>` 标签按环境（dev / prod）切换配置
- 支持 `<springProperty>` 从 `application.yml` 中读取变量
- 支持 Spring Boot 的彩色控制台输出（`<conversionRule conversionWord="clr">`）

### 3.3 当前项目配置

配置文件位于：`src/main/resources/Spring-logback.xml`

> 注意：文件名 `Spring-logback.xml` 不是 Spring Boot 自动识别的名称，需要在 `application.yml` 中显式指定。

### 3.4 指定配置文件位置

在 `application.yml`（或 `application.properties`）中添加：

**YAML 格式：**
```yaml
logging:
  config: classpath:Spring-logback.xml
```

**Properties 格式：**
```properties
logging.config=classpath:Spring-logback.xml
```

---

## 四、配置文件核心结构

### 4.1 整体结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration scan="true" scanPeriod="60 seconds">

    <!-- 1. 属性定义 -->
    <property name="..." value="..." />

    <!-- 2. Appender 定义（输出目标） -->
    <appender name="STDOUT" class="...">...</appender>
    <appender name="FILE_ALL" class="...">...</appender>
    <appender name="FILE_ERROR" class="...">...</appender>

    <!-- 3. Logger 定义（包级别控制） -->
    <logger name="org.springframework" level="ERROR" />
    <logger name="com.example.myapp" level="DEBUG" />

    <!-- 4. Root Logger（全局兜底） -->
    <root level="INFO">
        <appender-ref ref="STDOUT" />
        <appender-ref ref="FILE_ALL" />
    </root>

</configuration>
```

### 4.2 属性定义

```xml
<!-- 从 application.yml 读取，带默认值兜底 -->
<springProperty scope="context" name="LOG_HOME"
                source="logging.path"
                defaultValue="data/logs" />

<!-- 硬编码属性 -->
<property name="LOG_PREFIX" value="myapp" />
<property name="LOG_CHARSET" value="UTF-8" />
<property name="MAX_FILE_SIZE" value="50MB" />
<property name="MAX_HISTORY" value="30" />
<property name="TOTAL_SIZE_CAP" value="5GB" />
```

### 4.3 滚动策略（推荐 SizeAndTimeBasedRollingPolicy）

```xml
<rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
    <!-- 滚动文件命名规则，%d 日期，%i 同日序号 -->
    <fileNamePattern>${LOG_DIR}/all_${LOG_PREFIX}.%d{yyyyMMdd}.%i.log</fileNamePattern>
    <!-- 单个文件最大大小 -->
    <maxFileSize>${MAX_FILE_SIZE}</maxFileSize>
    <!-- 保留天数 -->
    <maxHistory>${MAX_HISTORY}</maxHistory>
    <!-- 所有日志文件总大小上限，防止磁盘写满 -->
    <totalSizeCap>${TOTAL_SIZE_CAP}</totalSizeCap>
</rollingPolicy>
```

> 旧版写法 `TimeBasedRollingPolicy` + `SizeAndTimeBasedFNATP` 已废弃，统一用上面的 `SizeAndTimeBasedRollingPolicy`。

### 4.4 Encoder vs Layout

**推荐使用 `<encoder>` 而非 `<layout>`：**

```xml
<!-- 推荐：encoder 是 layout 的升级，内置 charset 和 byte array 处理 -->
<encoder>
    <charset>${LOG_CHARSET}</charset>
    <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
</encoder>

<!-- 不推荐：layout 没有 charset 能力 -->
<layout class="ch.qos.logback.classic.PatternLayout">
    <pattern>...</pattern>
</layout>
```

### 4.5 日志格式占位符

| 占位符 | 含义 | 示例输出 |
|-------|------|---------|
| `%d` 或 `%date` | 时间 | `2026-10-06 14:30:00.123` |
| `%level` 或 `%p` | 日志级别 | `INFO` / `ERROR` |
| `%thread` 或 `%t` | 线程名 | `http-nio-8080-exec-1` |
| `%logger{n}` 或 `%c{n}` | Logger 名称，n 控制长度 | `c.e.myapp.controller.UserC` |
| `%msg` 或 `%m` | 日志消息 | `用户登录成功` |
| `%n` | 换行符 | 平台自适应 |
| `%X{key}` | MDC 中的变量 | `requestUUID` |
| `${HOSTNAME}` | 主机名 | `my-server-01` |
| `%highlight{...}` | 彩色输出（仅控制台） | 带 ANSI 颜色 |

### 4.6 按级别过滤

```xml
<filter class="ch.qos.logback.classic.filter.LevelFilter">
    <level>ERROR</level>
    <OnMismatch>DENY</OnMismatch>
    <OnMatch>ACCEPT</OnMatch>
</filter>
```

`OnMismatch` 可选值：
- `DENY` — 非 ERROR 级别直接丢弃（推荐用于 ERROR 专用文件）
- `NEUTRAL` — 继续传递给下一个 appender

### 4.7 Spring Profile 切换

```xml
<configuration>

    <springProfile name="dev">
        <root level="DEBUG">
            <appender-ref ref="STDOUT" />
        </root>
    </springProfile>

    <springProfile name="prod">
        <root level="INFO">
            <appender-ref ref="FILE_ALL" />
            <appender-ref ref="FILE_ERROR" />
        </root>
    </springProfile>

</configuration>
```

启动时指定 profile：
```bash
java -jar app.jar --spring.profiles.active=dev
```

### 4.8 热更新

```xml
<configuration scan="true" scanPeriod="60 seconds">
    <!-- 修改 logback-spring.xml 后 60 秒自动生效，无需重启 -->
</configuration>
```

---

## 五、应用层使用

### 5.1 声明 Logger

**方式一：推荐，Lombok @Slf4j**
```java
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class UserService {

    public void login() {
        log.info("用户登录成功, userId={}", 1001);
        log.error("数据库连接失败", e);
    }
}
```

**方式二：标准写法**
```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class UserService {
    private static final Logger log = LoggerFactory.getLogger(UserService.class);
}
```

### 5.2 MDC 传递请求标识

用于在日志中串联同一次请求的所有日志：

```java
// 拦截器 / 过滤器中
MDC.put("requestUUID", UUID.randomUUID().toString());
try {
    // 处理请求
} finally {
    MDC.remove("requestUUID");
}
```

logback 格式中引用：`%X{requestUUID}`

---

## 六、application.yml 配套配置

```yaml
logging:
  config: classpath:Spring-logback.xml   # 指定 logback 配置文件
  path: data/logs/myapp                  # 日志根目录（被 springProperty 读取）
  level:
    root: INFO                           # 全局默认级别
    org.springframework: ERROR            # 包级别覆盖
    com.example.myapp: DEBUG

log:
  stdout: STDOUT                         # 自定义属性，可选
```

---

## 七、常见问题排查

### Q1：配置不生效？
- 确认 `logging.config` 路径正确，文件在 `src/main/resources/` 下
- 检查文件名是否被 Spring Boot 自动识别（`logback.xml` / `logback-spring.xml`）
- Maven 构建后检查 `target/classes/` 下是否有该文件

### Q2：ERROR 日志文件为空？
- 检查 `FILE_ERROR` appender 是否加了 `LevelFilter`
- 确认 `<OnMismatch>DENY</OnMismatch>` 写法正确（大小写敏感）
- 验证文件权限，日志目录是否可写

### Q3：日志中文乱码？
- 确认 appender 使用了 `<encoder>` 而非 `<layout>`
- `<charset>` 设为 `UTF-8`
- 控制台乱码额外加 JVM 参数：`-Dfile.encoding=UTF-8`

### Q4：日志文件不滚动？
- 确认 rollingPolicy 是 `SizeAndTimeBasedRollingPolicy`
- `fileNamePattern` 必须包含 `%d`（日期）和 `%i`（序号）
- `maxFileSize` 不能超过 2GB（FAT32 文件系统限制）

### Q5：Spring Boot Actuator 日志动态调整？
```bash
curl -X POST "http://localhost:8080/actuator/loggers/com.example.myapp" \
     -H "Content-Type: application/json" \
     -d '{"configuredLevel": "DEBUG"}'
```

---

## 八、快速检查清单

- [ ] `pom.xml` 包含 `spring-boot-starter-logging`（或传递依赖）
- [ ] 配置文件放在 `src/main/resources/` 下
- [ ] 文件名是 `logback-spring.xml` 或 `logback.xml`（非标准名需 `logging.config` 指定）
- [ ] appender 使用 `<encoder>` 替代 `<layout>`
- [ ] 滚动策略使用 `SizeAndTimeBasedRollingPolicy`
- [ ] 根级别 `root level` 已设置
- [ ] application.yml 中日志目录路径可写
- [ ] 生产环境关闭 `scan="true"` 避免性能损耗