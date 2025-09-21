# Ledzephyr Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Configuration](#configuration)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)
9. [Security Considerations](#security-considerations)

## Overview

Ledzephyr can be deployed in multiple environments, from local development to production Kubernetes clusters. This guide covers all deployment scenarios with a focus on production-readiness, observability, and security.

## Prerequisites

### Required

- Python 3.11+ (for local deployment)
- Docker 20.10+ (for containerized deployment)
- Kubernetes 1.24+ (for K8s deployment)
- Valid API credentials for:
  - Jira (username + API token)
  - Zephyr Scale (Bearer token) - optional
  - qTest (Bearer token) - optional

### Recommended

- Prometheus for metrics collection
- Grafana for visualization
- OpenTelemetry Collector for distributed tracing
- Redis or Memcached for enhanced caching

## Deployment Options

### 1. Local Development

```bash
# Install with Poetry
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your API credentials

# Run the CLI
poetry run lz doctor  # Test connectivity
poetry run lz metrics -p PROJECT_KEY -w 7d
```

### 2. Docker Standalone

```bash
# Build the image
docker build -t ledzephyr:latest .

# Run with environment variables
docker run --rm \
  -e LEDZEPHYR_JIRA_URL=https://your-company.atlassian.net \
  -e LEDZEPHYR_JIRA_USERNAME=your-email@company.com \
  -e LEDZEPHYR_JIRA_API_TOKEN=your-token \
  ledzephyr:latest metrics -p PROJECT_KEY -w 7d
```

### 3. Docker Compose

```bash
# Start all services
docker-compose up -d

# Run metrics command
docker-compose exec ledzephyr lz metrics -p PROJECT_KEY -w 7d

# Start monitoring server
docker-compose exec ledzephyr lz monitor --port 8080
```

### 4. Kubernetes

See [Kubernetes Deployment](#kubernetes-deployment) section below.

## Docker Deployment

### Building the Image

The Dockerfile uses a multi-stage build for optimal size and security:

```bash
# Build with buildx for multi-platform support
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ledzephyr/ledzephyr:latest \
  --push .
```

### Running with Docker Compose

1. Create a `.env` file with your credentials:

```env
LEDZEPHYR_JIRA_URL=https://your-company.atlassian.net
LEDZEPHYR_JIRA_USERNAME=your-email@company.com
LEDZEPHYR_JIRA_API_TOKEN=your-jira-token
LEDZEPHYR_ZEPHYR_TOKEN=your-zephyr-token  # Optional
LEDZEPHYR_QTEST_URL=https://your-company.qtestnet.com  # Optional
LEDZEPHYR_QTEST_TOKEN=your-qtest-token  # Optional
PROJECT_KEY=YOUR_PROJECT
```

2. Start the services:

```bash
# Production mode
docker-compose up -d

# Development mode with hot reload
docker-compose --profile dev up

# Run tests in container
docker-compose --profile test up

# Run school-of-fish tests
docker-compose --profile schools up
```

### Container Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker inspect ledzephyr --format='{{json .State.Health}}'

# View health check logs
docker logs ledzephyr --tail 50 | grep health
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace ledzephyr
```

### 2. Create Secrets

```bash
# Create secret for API tokens
kubectl create secret generic ledzephyr-secrets \
  --from-literal=jira_username=your-email@company.com \
  --from-literal=jira_api_token=your-jira-token \
  --from-literal=zephyr_token=your-zephyr-token \
  --from-literal=qtest_token=your-qtest-token \
  -n ledzephyr
```

### 3. Create ConfigMap

```bash
# Apply configuration
kubectl apply -f k8s/configmap.yaml -n ledzephyr
```

### 4. Deploy Application

```bash
# Deploy the application
kubectl apply -f k8s/deployment.yaml -n ledzephyr

# Verify deployment
kubectl get pods -n ledzephyr
kubectl logs -f deployment/ledzephyr -n ledzephyr
```

### 5. Access Monitoring Endpoint

```bash
# Port-forward for local access
kubectl port-forward service/ledzephyr 8080:8080 -n ledzephyr

# Access endpoints
curl http://localhost:8080/health
curl http://localhost:8080/metrics
```

### Helm Chart Installation (Alternative)

```bash
# Add Helm repository
helm repo add ledzephyr https://charts.ledzephyr.io
helm repo update

# Install with custom values
helm install ledzephyr ledzephyr/ledzephyr \
  --namespace ledzephyr \
  --create-namespace \
  --values values.yaml
```

Example `values.yaml`:

```yaml
replicaCount: 3

image:
  repository: ledzephyr/ledzephyr
  tag: latest
  pullPolicy: IfNotPresent

secrets:
  jiraUrl: https://your-company.atlassian.net
  jiraUsername: your-email@company.com
  jiraApiToken: <base64-encoded-token>
  zephyrToken: <base64-encoded-token>
  qtestUrl: https://your-company.qtestnet.com
  qtestToken: <base64-encoded-token>

resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

monitoring:
  enabled: true
  prometheusOperator: true
  grafanaDashboard: true
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LEDZEPHYR_JIRA_URL` | Jira instance URL | Yes | - |
| `LEDZEPHYR_JIRA_USERNAME` | Jira username/email | Yes | - |
| `LEDZEPHYR_JIRA_API_TOKEN` | Jira API token | Yes | - |
| `LEDZEPHYR_ZEPHYR_TOKEN` | Zephyr Scale API token | No | - |
| `LEDZEPHYR_QTEST_URL` | qTest instance URL | No | - |
| `LEDZEPHYR_QTEST_TOKEN` | qTest API token | No | - |
| `LEDZEPHYR_CACHE_DIR` | Cache directory path | No | `~/.ledzephyr_cache` |
| `LEDZEPHYR_CACHE_TTL` | Cache TTL in seconds | No | `3600` |
| `LEDZEPHYR_LOG_LEVEL` | Log level | No | `INFO` |
| `ENVIRONMENT` | Environment name | No | `development` |
| `OTLP_ENDPOINT` | OpenTelemetry endpoint | No | - |

### Configuration File

Create a `.ledzephyr.yaml` configuration file:

```yaml
# API Configuration
jira:
  url: https://your-company.atlassian.net
  username: your-email@company.com
  api_token: ${JIRA_API_TOKEN}  # Use env var reference

zephyr:
  token: ${ZEPHYR_TOKEN}

qtest:
  url: https://your-company.qtestnet.com
  token: ${QTEST_TOKEN}

# Cache Configuration
cache:
  enabled: true
  directory: /var/cache/ledzephyr
  ttl: 3600
  max_size_mb: 500

# Observability
observability:
  metrics:
    enabled: true
    port: 8080
  tracing:
    enabled: true
    endpoint: otel-collector:4317
  logging:
    level: INFO
    format: json  # or "text"

# Performance
performance:
  timeout: 30
  max_retries: 3
  connection_pool_size: 10
  parallel_workers: 4
```

## Monitoring & Observability

### 1. Prometheus Setup

Deploy Prometheus to scrape metrics:

```bash
# Install Prometheus Operator
kubectl create namespace monitoring
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring

# Apply Prometheus configuration
kubectl apply -f monitoring/prometheus.yml
```

### 2. Grafana Dashboard

Import the pre-configured dashboard:

1. Access Grafana UI
2. Navigate to Dashboards → Import
3. Upload `monitoring/grafana-dashboard.json`
4. Select Prometheus data source

### 3. Health Checks

The application exposes multiple health endpoints:

- `/health` - Comprehensive health status
- `/health/live` - Kubernetes liveness probe
- `/health/ready` - Kubernetes readiness probe
- `/metrics` - Prometheus metrics
- `/info` - Service information

Example health check response:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45Z",
  "version": "0.1.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection OK",
      "metadata": {
        "connection_pool_size": 10,
        "active_connections": 2
      }
    },
    "api": {
      "status": "healthy",
      "message": "External APIs reachable",
      "metadata": {
        "jira": "ok",
        "zephyr": "ok",
        "qtest": "ok"
      }
    },
    "cache": {
      "status": "healthy",
      "message": "Cache system operational",
      "metadata": {
        "hit_rate": 0.85,
        "size_mb": 120
      }
    }
  }
}
```

### 4. Distributed Tracing

Configure OpenTelemetry for distributed tracing:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

exporters:
  jaeger:
    endpoint: jaeger-collector:14250

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
```

### 5. Alerting

Configure alerts in `monitoring/alerts.yml`:

- High error rate (>1% warning, >5% critical)
- High API latency (P95 > 2s)
- Low cache hit rate (<50%)
- Service down
- Pod restarts
- Memory/CPU limits

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

```bash
# Test Jira connectivity
lz doctor

# Verify credentials
curl -u username:api_token \
  https://your-company.atlassian.net/rest/api/2/myself
```

#### 2. High Memory Usage

```bash
# Check memory usage
kubectl top pods -n ledzephyr

# Adjust limits in deployment
kubectl edit deployment ledzephyr -n ledzephyr
```

#### 3. Slow Performance

```bash
# Check metrics endpoint
curl http://localhost:8080/metrics | grep duration

# Enable debug logging
export LEDZEPHYR_LOG_LEVEL=DEBUG
```

#### 4. Cache Issues

```bash
# Clear cache
rm -rf ~/.ledzephyr_cache/*

# Disable cache temporarily
export LEDZEPHYR_CACHE_TTL=0
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Local debugging
LEDZEPHYR_LOG_LEVEL=DEBUG lz metrics -p PROJECT_KEY -w 7d

# In Kubernetes
kubectl set env deployment/ledzephyr LEDZEPHYR_LOG_LEVEL=DEBUG -n ledzephyr
```

### Performance Tuning

```yaml
# Optimize for large projects
performance:
  timeout: 60  # Increase timeout
  max_retries: 5  # More retries
  connection_pool_size: 20  # Larger pool
  parallel_workers: 8  # More workers
```

## Security Considerations

### 1. Secret Management

- Never commit credentials to version control
- Use Kubernetes Secrets or external secret managers
- Rotate API tokens regularly
- Use least-privilege principle for API access

### 2. Network Security

```yaml
# NetworkPolicy example
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ledzephyr-netpol
spec:
  podSelector:
    matchLabels:
      app: ledzephyr
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - port: 443  # HTTPS
    - port: 53   # DNS
```

### 3. Container Security

- Run as non-root user
- Use read-only root filesystem
- Scan images for vulnerabilities
- Keep base images updated

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

### 4. API Rate Limiting

Configure rate limiting to prevent API abuse:

```yaml
# In deployment.yaml
env:
- name: RATE_LIMIT_PER_MINUTE
  value: "100"
- name: RATE_LIMIT_BURST
  value: "20"
```

## Production Checklist

Before deploying to production:

- [ ] Configure proper resource limits
- [ ] Set up monitoring and alerting
- [ ] Enable distributed tracing
- [ ] Configure autoscaling (HPA)
- [ ] Set up PodDisruptionBudget
- [ ] Configure health checks
- [ ] Enable security policies
- [ ] Set up backup strategy
- [ ] Document runbooks
- [ ] Test disaster recovery

## Support

For issues or questions:

1. Check the [troubleshooting guide](#troubleshooting)
2. Review application logs
3. Check metrics and health endpoints
4. Open an issue on GitHub
5. Contact the team at support@ledzephyr.io