# JFA Unify — Production Monitoring & Observability Setup

## Overview

Complete monitoring, logging, alerting, and observability stack for production deployment on ubuntu-50.

**Components:**
- Prometheus (metrics collection)
- Grafana (visualization & dashboards)
- Loki (log aggregation)
- Alertmanager (alerts)
- Node Exporter (system metrics)

---

## 1. Prometheus Configuration

**File:** `config/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'jfa-unify-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'jfa-unify-postgresql'
    static_configs:
      - targets: ['localhost:5432']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:6379']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - 'alerts.yml'
```

---

## 2. Alert Rules

**File:** `config/alerts.yml`

```yaml
groups:
  - name: jfa_unify
    interval: 30s
    rules:
      # Backend alerts
      - alert: BackendDown
        expr: up{job="jfa-unify-backend"} == 0
        for: 1m
        annotations:
          summary: "JFA Unify backend is down"
          description: "Backend at {{ $labels.instance }} has been down for 1 minute"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate > 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "High request latency"
          description: "p95 latency > 1s for 5 minutes"

      # Database alerts
      - alert: PostgreSQLDown
        expr: up{job="jfa-unify-postgresql"} == 0
        for: 1m
        annotations:
          summary: "PostgreSQL is down"

      - alert: PostgreSQLConnectionsHigh
        expr: postgresql_stat_activity_count > 80
        for: 5m
        annotations:
          summary: "PostgreSQL connection pool near limit"
          description: "{{ $value }} connections (max 100)"

      - alert: PostgreSQLReplicationLag
        expr: postgresql_replication_lag_seconds > 10
        for: 5m
        annotations:
          summary: "PostgreSQL replication lag high"

      # Redis alerts
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        annotations:
          summary: "Redis is down"

      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        annotations:
          summary: "Redis memory usage > 90%"

      # System alerts
      - alert: HighCPU
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        annotations:
          summary: "High CPU usage"
          description: "CPU > 80% for 5 minutes"

      - alert: HighMemory
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.85
        for: 5m
        annotations:
          summary: "High memory usage"
          description: "Memory > 85% for 5 minutes"

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes) < 0.1
        for: 5m
        annotations:
          summary: "Low disk space"
          description: "< 10% free space on root partition"
```

---

## 3. Docker Compose Addition

Add monitoring stack to `docker-compose.prod.yml`:

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: jfa_unify_prometheus
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/alerts.yml:/etc/prometheus/alerts.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped
    networks:
      - jfa_unify_net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  grafana:
    image: grafana/grafana:latest
    container_name: jfa_unify_grafana
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_SECURITY_ADMIN_USER: admin
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - jfa_unify_net

  loki:
    image: grafana/loki:latest
    container_name: jfa_unify_loki
    ports:
      - "3100:3100"
    volumes:
      - ./config/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    restart: unless-stopped
    networks:
      - jfa_unify_net

  alertmanager:
    image: prom/alertmanager:latest
    container_name: jfa_unify_alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./config/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    restart: unless-stopped
    networks:
      - jfa_unify_net

  node_exporter:
    image: prom/node-exporter:latest
    container_name: jfa_unify_node_exporter
    ports:
      - "9100:9100"
    restart: unless-stopped
    networks:
      - jfa_unify_net
```

---

## 4. Grafana Dashboards

**Pre-built dashboards:**
- Backend performance (requests, latency, errors)
- Database health (connections, replication, slow queries)
- Infrastructure (CPU, memory, disk, network)
- MQTT broker activity
- Cache hit rates (Redis)

**Setup:**
1. Access Grafana: `http://localhost:3001` (admin/password)
2. Add Prometheus datasource: `http://prometheus:9090`
3. Import dashboards from `config/grafana-dashboards/*.json`

---

## 5. Logging (Loki + Promtail)

**Promtail config** (agents on each container):

```yaml
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker: {}
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
      - source_labels: ['__meta_docker_container_label_service']
        target_label: 'service'
```

**Loki storage:** `/loki/index`, `/loki/chunks` (10GB default)

---

## 6. Alert Routing (Alertmanager)

**File:** `config/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'critical'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

  routes:
    - match:
        severity: critical
      receiver: critical
      continue: true

    - match:
        severity: warning
      receiver: warnings

receivers:
  - name: 'critical'
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_CRITICAL}
        channel: '#alerts-jfa-unify'
        title: '[CRITICAL] {{ .GroupLabels.alertname }}'

  - name: 'warnings'
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_WARNINGS}
        channel: '#alerts-jfa-unify-warnings'
```

---

## 7. Key Metrics to Monitor

| Metric | Threshold | Action |
|--------|-----------|--------|
| Backend error rate | >5% | Page on-call |
| p95 latency | >1s | Investigate + optimize |
| PostgreSQL connections | >80/100 | Scale replicas |
| Redis memory | >90% | Eviction or cluster mode |
| Disk space | <10% | Rotate logs or expand |
| CPU | >80% | Scale horizontally |
| Memory | >85% | OOM risk, scale or tune |

---

## 8. Dashboard URLs

- **Prometheus:** `http://ubuntu-50:9090`
- **Grafana:** `http://ubuntu-50:3001`
- **Alertmanager:** `http://ubuntu-50:9093`

---

## 9. On-Call Runbook

**When Backend is down:**
1. Check `docker-compose ps` for container status
2. View logs: `docker logs jfa_unify_backend`
3. Check database connectivity: `docker exec jfa_unify_backend psql -h postgres -U $DB_USER -d jfa_unify -c "SELECT 1"`
4. Restart: `docker-compose restart backend`
5. If persists, check disk space / memory / CPU

**When DB is slow:**
1. Check slow query log: `tail -f backend/logs/slow-queries.log`
2. Identify heavy tables: `SELECT * FROM pg_stat_user_tables ORDER BY seq_scan DESC`
3. Add missing indexes (see `docs/schema.md`)
4. Consider read replicas if RLS overhead

---

## Setup Checklist

- [ ] Create `config/prometheus.yml`
- [ ] Create `config/alerts.yml`
- [ ] Create `config/alertmanager.yml`
- [ ] Create `config/loki-config.yml`
- [ ] Add Prometheus/Grafana/Loki/Alertmanager to `docker-compose.prod.yml`
- [ ] Set SLACK_WEBHOOK_CRITICAL, SLACK_WEBHOOK_WARNINGS in `.env.production`
- [ ] Deploy and test alerting (send test alert to Slack)
- [ ] Document runbook in team wiki
