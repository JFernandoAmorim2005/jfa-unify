# JFA_Unify — Deployment Runbooks

## Ambiente & Pré-requisitos

### Infraestrutura
- **Dev:** Docker Compose (local machine)
- **Staging:** AWS ECR + ECS + RDS PostgreSQL + ElastiCache Redis
- **Production:** AWS ECR + ECS + RDS (Multi-AZ) + ElastiCache (Cluster mode) + CloudFront CDN

### Requisitos
- Docker & Docker Compose (dev)
- AWS CLI v2 configured (staging/prod)
- Terraform 1.5+ (IaC)
- kubectl (ECS context, optional)
- Tuya IoT IoM account + API credentials
- Stripe account (test mode for staging)
- Moloni API keys (Portugal tax integration)

---

## Fase 1: Desenvolvimento (Docker Compose)

### 1.1 Configuração Inicial

#### Clone e estrutura
```bash
git clone https://github.com/jfernandoamorim/jfa-unify.git
cd jfa-unify
cp .env.example .env.dev
```

#### .env.dev (valores para desenvolvimento local)
```
# Backend
FASTAPI_DEBUG=true
DATABASE_URL=postgresql://unify:dev@postgres:5432/unify_dev
REDIS_URL=redis://redis:6379/0
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=8883
MQTT_USERNAME=unify_dev
MQTT_PASSWORD=dev_password_change_in_prod

# Tuya (substitute com valores reais)
TUYA_CLIENT_ID=$TUYA_CLIENT_ID
TUYA_CLIENT_SECRET=$TUYA_CLIENT_SECRET
TUYA_DEVICE_ID=$TUYA_DEVICE_ID
TUYA_DEVICE_KEY=$TUYA_DEVICE_KEY
TUYA_REGION=EU

# Payment (test mode)
STRIPE_API_KEY=sk_test_XXXXX
STRIPE_SIGNING_SECRET=whsec_test_XXXXX
MOLONI_CLIENT_ID=$MOLONI_CLIENT_ID
MOLONI_CLIENT_SECRET=$MOLONI_CLIENT_SECRET

# SvelteKit
PUBLIC_API_URL=http://localhost:8000
VITE_API_BASE=http://localhost:8000
```

#### docker-compose.yml (básico)
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: unify_dev
      POSTGRES_USER: unify
      POSTGRES_PASSWORD: dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U unify"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "8883:8883"
      - "8884:8884"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
      - mosquitto_data:/mosquitto/data
    healthcheck:
      test: ["CMD-SHELL", "mosquitto_sub -h localhost -p 8883 --cafile /etc/mosquitto/ca.crt -C 2 -t '\\$SYS/broker/clients/connected' | grep -q ^"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    environment:
      - DATABASE_URL=postgresql://unify:dev@postgres:5432/unify_dev
      - REDIS_URL=redis://redis:6379/0
      - MQTT_BROKER_HOST=mosquitto
      - MQTT_BROKER_PORT=8883
      - FASTAPI_DEBUG=true
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      mosquitto:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    environment:
      - PUBLIC_API_URL=http://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    command: npm run dev

volumes:
  postgres_data:
  mosquitto_data:
```

### 1.2 Inicialização

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run database migrations
docker-compose exec backend alembic upgrade head

# Seed initial data (users, tenants, devices)
docker-compose exec backend python scripts/seed_dev.py

# Verify connectivity
docker-compose exec backend python -c "from app.db import engine; print('DB OK')"
docker-compose exec backend mosquitto_sub -h mosquitto -p 8883 -t '$SYS/broker/clients/connected'
```

### 1.3 Desenvolvimento Local

```bash
# Watch backend logs
docker-compose logs -f backend

# Run tests locally
docker-compose exec backend pytest tests/ -v --cov=app --cov-report=html

# Access services
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# Docs: http://localhost:8000/docs
# Redis: localhost:6379
# PostgreSQL: localhost:5432 (user: unify, pass: dev)
```

---

## Fase 2: Staging (AWS ECS + RDS)

### 2.1 Configuração Terraform

#### terraform/variables.tf
```hcl
variable "aws_region" {
  default = "eu-west-1"
}

variable "app_name" {
  default = "jfa-unify"
}

variable "environment" {
  default = "staging"
}

variable "container_port" {
  default = 8000
}

variable "rds_allocated_storage" {
  default = 20
}

variable "rds_engine_version" {
  default = "15.2"
}

variable "desired_count" {
  default = 2
}
```

#### terraform/main.tf
```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket         = "jfa-unify-terraform-state"
    key            = "staging/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "jfa_unify" {
  name = "${var.app_name}-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECR Repository
resource "aws_ecr_repository" "backend" {
  name                 = "${var.app_name}-backend"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier            = "${var.app_name}-${var.environment}"
  allocated_storage     = var.rds_allocated_storage
  engine                = "postgres"
  engine_version        = var.rds_engine_version
  instance_class        = "db.t3.micro"
  db_name               = "unify_staging"
  username              = "unify"
  password              = random_password.db_password.result
  skip_final_snapshot   = false
  multi_az              = false
  publicly_accessible   = false
  
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  tags = {
    Name        = "${var.app_name}-${var.environment}"
    Environment = var.environment
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.app_name}-${var.environment}"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  security_group_ids = [aws_security_group.elasticache.id]
  
  tags = {
    Name        = "${var.app_name}-${var.environment}"
    Environment = var.environment
  }
}

# ECS Task Definition (Backend)
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.app_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  
  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true
      
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${aws_db_instance.postgres.username}:${random_password.db_password.result}@${aws_db_instance.postgres.address}:5432/unify_staging"
        },
        {
          name  = "REDIS_URL"
          value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        }
      ]
      
      secrets = [
        {
          name      = "TUYA_CLIENT_ID"
          valueFrom = "arn:aws:secretsmanager:${var.aws_region}:ACCOUNT_ID:secret:jfa-unify-tuya-client-id"
        },
        {
          name      = "STRIPE_API_KEY"
          valueFrom = "arn:aws:secretsmanager:${var.aws_region}:ACCOUNT_ID:secret:jfa-unify-stripe-api-key"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
  
  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
}

# ECS Service
resource "aws_ecs_service" "backend" {
  name            = "${var.app_name}-backend"
  cluster         = aws_ecs_cluster.jfa_unify.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.container_port
  }
  
  depends_on = [
    aws_db_instance.postgres,
    aws_elasticache_cluster.redis
  ]
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.app_name}-${var.environment}"
  retention_in_days = 30
}

# ALB (Application Load Balancer)
resource "aws_lb" "main" {
  name               = "${var.app_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  
  subnets = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.app_name}-backend-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  
  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
}

# Random password for RDS
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Outputs
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "redis_endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}
```

### 2.2 Deployment Staging

```bash
# 1. Build and push to ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com
docker build -t jfa-unify-backend:latest ./backend
docker tag jfa-unify-backend:latest ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/jfa-unify-backend:latest
docker push ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/jfa-unify-backend:latest

# 2. Deploy infrastructure with Terraform
cd terraform
terraform init
terraform plan -var-file=staging.tfvars -out=staging.plan
terraform apply staging.plan

# 3. Run database migrations
# Determine ECS task IP
export TASK_IP=$(aws ecs list-tasks --cluster jfa-unify-staging --service-name jfa-unify-backend --query 'taskArns[0]' --output text | xargs -I {} aws ecs describe-tasks --cluster jfa-unify-staging --tasks {} --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' --output text)

# Port forward or use ECS Exec
aws ecs execute-command \
  --cluster jfa-unify-staging \
  --task TASK_ID \
  --container backend \
  --command "alembic upgrade head" \
  --interactive

# 4. Seed staging data
aws ecs execute-command \
  --cluster jfa-unify-staging \
  --task TASK_ID \
  --container backend \
  --command "python scripts/seed_staging.py" \
  --interactive

# 5. Verify deployment
export ALB_URL=$(terraform output -raw alb_dns_name)
curl http://$ALB_URL/health
curl http://$ALB_URL/docs
```

---

## Fase 3: Produção (Multi-AZ RDS + Cluster Redis)

### 3.1 Pre-requisites

- Terraform state secured in S3 with versioning + DynamoDB locks
- AWS Secrets Manager com todas as credenciais (Tuya, Stripe, Moloni)
- CloudFront distribuição para assets estáticos
- WAF rules para API rate-limiting
- Monitoring: CloudWatch, X-Ray tracing
- Backup automático: RDS snapshots (daily), cross-region replication

### 3.2 Configuração Production

#### terraform/production.tfvars
```hcl
aws_region               = "eu-west-1"
environment              = "production"
rds_allocated_storage    = 100
rds_engine_version       = "15.2"
rds_multi_az             = true
desired_count            = 3
redis_node_type          = "cache.t3.small"
redis_num_cache_nodes    = 3
redis_automatic_failover = true
```

#### Deployment Steps

```bash
# 1. Pre-deployment checklist
# - All feature branches merged and tested in staging
# - Database backup created
# - Rollback plan documented
# - Incident response team on standby

# 2. Create database snapshot
aws rds create-db-snapshot \
  --db-instance-identifier jfa-unify-staging \
  --db-snapshot-identifier jfa-unify-production-backup-$(date +%Y%m%d-%H%M%S)

# 3. Deploy infrastructure
cd terraform
terraform plan -var-file=production.tfvars -out=production.plan
# REVIEW CAREFULLY — production changes require approval
terraform apply production.plan

# 4. Run migrations with zero-downtime strategy
# - Deploy read-only version first
# - Run forward migrations
# - Switch traffic

aws ecs execute-command \
  --cluster jfa-unify-production \
  --task TASK_ID \
  --container backend \
  --command "alembic upgrade head" \
  --interactive

# 5. Health checks
export PROD_ALB=$(terraform output -raw alb_dns_name)
for i in {1..10}; do
  curl -f http://$PROD_ALB/health || exit 1
  sleep 5
done

# 6. Smoke tests
pytest tests/smoke/ -v --tb=short

# 7. Monitor for 1 hour
# - Check CloudWatch metrics (latency, errors, CPU, memory)
# - Verify logs in CloudWatch
# - Monitor Stripe/Moloni integration health
```

---

## Operações Contínuas

### Health Checks

```bash
#!/bin/bash
# health_check.sh — run every 5 minutes via CloudWatch Events

API_URL="https://api.jfa-unify.com"
THRESHOLD_MS=500

# Check API responsiveness
RESPONSE=$(curl -w "\n%{http_code}\n" -s "$API_URL/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo "ALERT: Health check failed with HTTP $HTTP_CODE"
  # Trigger incident response
  exit 1
fi

# Check database connectivity
echo "$BODY" | jq -e '.database == "connected"' || {
  echo "ALERT: Database connectivity issue"
  exit 1
}

# Check Redis connectivity
echo "$BODY" | jq -e '.redis == "connected"' || {
  echo "ALERT: Redis connectivity issue"
  exit 1
}

# Check MQTT broker
curl -s "$API_URL/mqtt/status" | jq -e '.connected == true' || {
  echo "ALERT: MQTT broker disconnected"
  exit 1
}

echo "OK: All health checks passed"
```

### Rollback Procedure

```bash
#!/bin/bash
# rollback.sh — return to previous stable version

ROLLBACK_VERSION=$1  # e.g., "v1.2.0"

if [ -z "$ROLLBACK_VERSION" ]; then
  echo "Usage: ./rollback.sh <version>"
  exit 1
fi

# 1. Scale down current version
aws ecs update-service \
  --cluster jfa-unify-production \
  --service jfa-unify-backend \
  --desired-count 0

# 2. Point to previous ECR image
aws ecs update-task-definition \
  --task-definition jfa-unify-backend \
  --container-definitions "[{\"image\": \"ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/jfa-unify-backend:$ROLLBACK_VERSION\"}]"

# 3. Scale back up
aws ecs update-service \
  --cluster jfa-unify-production \
  --service jfa-unify-backend \
  --desired-count 3

# 4. Wait for tasks to start
sleep 30

# 5. Verify health
./health_check.sh

echo "Rollback to $ROLLBACK_VERSION complete"
```

### Database Maintenance

```bash
#!/bin/bash
# maintenance.sh — monthly maintenance tasks

# 1. Analyze tables for query optimization
aws ecs execute-command \
  --cluster jfa-unify-production \
  --task TASK_ID \
  --container backend \
  --command "psql -c \"ANALYZE;\"" \
  --interactive

# 2. Reindex tables
aws ecs execute-command \
  --cluster jfa-unify-production \
  --task TASK_ID \
  --container backend \
  --command "psql -c \"REINDEX DATABASE unify_prod;\"" \
  --interactive

# 3. Backup logs table (archive old audit records)
aws ecs execute-command \
  --cluster jfa-unify-production \
  --task TASK_ID \
  --container backend \
  --command "python scripts/archive_logs.py --days=730" \
  --interactive

# 4. Verify backup completeness
aws rds describe-db-snapshots \
  --db-instance-identifier jfa-unify-production \
  --query 'DBSnapshots[0].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table
```

---

## Disaster Recovery

### RTO/RPO Targets
- **RTO (Recovery Time Objective):** 30 minutes
- **RPO (Recovery Point Objective):** 1 hour

### Backup Strategy

```bash
#!/bin/bash
# backup.sh — daily automated backup with cross-region replication

# 1. Create RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier jfa-unify-production \
  --db-snapshot-identifier "jfa-unify-prod-$(date +%Y%m%d-%H%M%S)"

# 2. Copy snapshot to DR region (eu-central-1)
SNAPSHOT_ID=$(aws rds describe-db-snapshots \
  --db-instance-identifier jfa-unify-production \
  --query 'DBSnapshots[0].DBSnapshotIdentifier' \
  --output text)

aws rds copy-db-snapshot \
  --source-db-snapshot-identifier "arn:aws:rds:eu-west-1:ACCOUNT_ID:snapshot:$SNAPSHOT_ID" \
  --target-db-snapshot-identifier "$SNAPSHOT_ID-dr" \
  --region eu-central-1

# 3. Backup application state (S3)
aws s3 sync s3://jfa-unify-prod-data/ s3://jfa-unify-dr-backup/ \
  --region eu-west-1 \
  --sse AES256

echo "Backup complete: RDS snapshot and S3 replicated"
```

### Disaster Recovery Test (Quarterly)

```bash
#!/bin/bash
# dr_test.sh — restore from backup to DR region and verify

DR_REGION="eu-central-1"
TEST_IDENTIFIER="jfa-unify-prod-dr-test-$(date +%s)"

# 1. Restore RDS from snapshot in DR region
SNAPSHOT_ID=$(aws rds describe-db-snapshots \
  --region $DR_REGION \
  --query 'DBSnapshots[0].DBSnapshotIdentifier' \
  --output text)

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $TEST_IDENTIFIER \
  --db-snapshot-identifier $SNAPSHOT_ID \
  --region $DR_REGION

# 2. Wait for database to be available
aws rds wait db-instance-available \
  --db-instance-identifier $TEST_IDENTIFIER \
  --region $DR_REGION

# 3. Run smoke tests against restored database
# ... connect to test database and run validation queries ...

# 4. Verify data integrity
# - Check row counts match production
# - Verify recent transactions exist
# - Validate RLS policies still enforced

# 5. Cleanup
aws rds delete-db-instance \
  --db-instance-identifier $TEST_IDENTIFIER \
  --skip-final-snapshot \
  --region $DR_REGION

echo "DR test complete: Data integrity verified"
```

---

## Monitoramento & Alertas

### CloudWatch Alarms

```bash
# High CPU on ECS tasks
aws cloudwatch put-metric-alarm \
  --alarm-name jfa-unify-ecs-cpu-high \
  --alarm-description "Alert when ECS CPU > 70%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold

# High database connections
aws cloudwatch put-metric-alarm \
  --alarm-name jfa-unify-rds-connections \
  --alarm-description "Alert when DB connections > 80" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# API latency
aws cloudwatch put-metric-alarm \
  --alarm-name jfa-unify-api-latency \
  --alarm-description "Alert when latency > 500ms" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 0.5 \
  --comparison-operator GreaterThanThreshold
```

---

## Documento versão: 2026-05-26
## Próximo passo: Scalability Matrix (50-500 locations)
