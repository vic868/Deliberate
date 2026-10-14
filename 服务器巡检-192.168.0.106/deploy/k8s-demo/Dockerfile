# ============================================================
# demo-api 多阶段构建（产物 ~200MB，最终镜像只含 JRE + jar）
# 构建：docker build -t demo-api:1.0.0 .
# ============================================================

# ---------- 阶段 1：用 Maven 编译打包 ----------
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build

# 先拷 pom 单独下一层依赖，利用 Docker 缓存（改代码不必重下依赖）
COPY pom.xml .
RUN mvn -B -q dependency:go-offline

COPY src ./src
RUN mvn -B -q clean package -DskipTests

# ---------- 阶段 2：只留运行时 ----------
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

# 时区 + 基础工具（排障用，可删）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get update && apt-get install -y --no-install-recommends curl tzdata \
    && rm -rf /var/lib/apt/lists/*

# 非 root 运行（安全基线）
RUN groupadd -r app && useradd -r -g app app

COPY --from=build /build/target/demo-api.jar /app/app.jar
RUN chown -R app:app /app
USER app

EXPOSE 8080

# 容器级健康检查（K8s 用的是下面 YAML 里的探针，这个是兜底）
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/actuator/health || exit 1

# 容器感知的 JVM 参数：让 JVM 按 K8s limits 自动算堆，而不是按宿主机 48G
ENV JAVA_OPTS="-XX:MaxRAMPercentage=70 -XX:InitialRAMPercentage=40 -XX:+UseG1GC -Duser.timezone=Asia/Shanghai"

# exec 形式，保证 java 是 PID 1，能收到 SIGTERM 优雅停机
ENTRYPOINT ["sh","-c","exec java $JAVA_OPTS -jar /app/app.jar"]
