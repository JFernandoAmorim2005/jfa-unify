# JFA Unify — Backup & Disaster Recovery Plan

## Backup Strategy

### 1. PostgreSQL Database Backups

**Daily full backup + hourly WAL archives**

**Backup script** (`scripts/backup-db.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/opt/jfa/unify/backups/postgresql"
RETENTION_DAYS=30
DB_NAME="jfa_unify"
DB_USER="${DB_USER}"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

# Create daily backup
docker exec jfa_unify_postgres pg_dump \
  -U "$DB_USER" \
  -Fc \
  -v \
  -f "/var/lib/postgresql/backup/db_full_$BACKUP_DATE.dump" \
  "$DB_NAME"

# Archive WAL logs (continuous)
docker exec jfa_unify_postgres pg_basebackup \
  -U "$DB_USER" \
  -Ft \
  -z \
  -P \
  -D "/var/lib/postgresql/backup/wal_$BACKUP_DATE"

# Copy to external storage (S3/Azure/GCS)
aws s3 cp "$BACKUP_DIR/db_full_$BACKUP_DATE.dump" \
  s3://jfa-unify-backups/postgresql/ \
  --sse AES256

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "db_full_*" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Backup completed: db_full_$BACKUP_DATE.dump"
```

**Schedule:** Cron job (daily at 02:00 UTC)

```bash
0 2 * * * /opt/jfa/unify/scripts/backup-db.sh >> /var/log/jfa-backup.log 2>&1
```

---

### 2. Redis Persistence

**RDB snapshots + AOF (Append-Only File)**

**Config** (`config/redis.conf`):

```
save 900 1           # Save every 15 min if 1+ keys changed
save 300 10          # Save every 5 min if 10+ keys changed
appendonly yes       # Enable AOF
appendfsync everysec # Sync every second
```

**Backup:**

```bash
docker exec jfa_unify_redis redis-cli BGSAVE
docker cp jfa_unify_redis:/data/dump.rdb /opt/jfa/unify/backups/redis/
```

---

### 3. Application Code & Config

**Git-based backups:**

```bash
# Automatic daily backup via git
git bundle create /opt/jfa/unify/backups/jfa-unify-$(date +%Y%m%d).bundle main
```

**Config backup** (secrets not included):

```bash
tar --exclude='*.env' --exclude='.git' \
  -czf /opt/jfa/unify/backups/config-$(date +%Y%m%d).tar.gz \
  /opt/jfa/unify/config/ /opt/jfa/unify/.env.*.example
```

---

### 4. External Cloud Storage

**Primary:** AWS S3 or Azure Blob Storage

```bash
# Push daily
aws s3 sync /opt/jfa/unify/backups/ s3://jfa-unify-backups/ \
  --exclude "*.tmp" \
  --storage-class GLACIER \
  --sse AES256

# Retention: 90 days in S3, 1 year in Glacier
```

---

## Recovery Procedures

### Scenario 1: Database Corruption

**RTO:** 15 minutes | **RPO:** 1 hour

**Steps:**

```bash
# 1. Stop backend to prevent further writes
docker-compose stop backend

# 2. Restore from latest backup
BACKUP_FILE="s3://jfa-unify-backups/postgresql/db_full_YYYYMMDD_hhmmss.dump"
aws s3 cp "$BACKUP_FILE" /tmp/restore.dump

# 3. Create new database
docker exec jfa_unify_postgres createdb -U $DB_USER jfa_unify_restore

# 4. Restore
docker exec jfa_unify_postgres pg_restore \
  -U "$DB_USER" \
  -d jfa_unify_restore \
  /var/lib/postgresql/restore.dump

# 5. Verify restore
docker exec jfa_unify_postgres psql -U $DB_USER -d jfa_unify_restore -c "SELECT COUNT(*) FROM devices;"

# 6. Swap databases (rename)
docker exec jfa_unify_postgres psql -U $DB_USER -c \
  "ALTER DATABASE jfa_unify RENAME TO jfa_unify_corrupted; 
   ALTER DATABASE jfa_unify_restore RENAME TO jfa_unify;"

# 7. Restart backend
docker-compose start backend

# 8. Verify application
curl -f http://localhost:8000/health || rollback
```

---

### Scenario 2: Complete Infrastructure Failure

**RTO:** 1-2 hours | **RPO:** 1 hour

**Prerequisites:**
- Secondary ubuntu-50 instance (standby in same datacenter)
- Database snapshots in AWS/Azure
- Docker images in registry

**Steps:**

```bash
# 1. Activate secondary instance
# (assumed to be already provisioned, just powered off)
aws ec2 start-instances --instance-ids i-secondary-ubuntu50

# 2. Wait for boot (5 min) + verify network access
ssh ubuntu@ubuntu-50-secondary ping 8.8.8.8

# 3. Restore docker-compose.prod.yml + .env
aws s3 cp s3://jfa-unify-backups/docker-compose.prod.yml \
  /opt/jfa/unify/

aws s3 cp s3://jfa-unify-backups/.env.production \
  /opt/jfa/unify/

# 4. Restore database from backup
docker-compose exec postgres pg_restore \
  -U "$DB_USER" \
  -d jfa_unify \
  s3://jfa-unify-backups/postgresql/db_full_latest.dump

# 5. Start all services
docker-compose -f docker-compose.prod.yml up -d

# 6. Update DNS to point to secondary
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123 \
  --change-batch file://route53-failover.json

# 7. Monitor logs & metrics
tail -f /opt/jfa/unify/logs/*.log
```

---

### Scenario 3: Data Breach / Ransomware

**RTO:** 4 hours | **RPO:** 24 hours

**Response:**

```bash
# 1. Isolate production immediately
docker-compose down

# 2. Notify security team + start incident response

# 3. Restore from clean backup (from 24h ago)
# Assume backup was on secure, offline storage
aws s3 cp s3://jfa-unify-backups-cold/db_full_YESTERDAY.dump /tmp/

# 4. Forensics: preserve current state for analysis
tar -czf /forensics/jfa-unify-$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/jfa/unify/ /var/lib/docker/

# 5. Full system rebuild from backup
docker pull registry.jfernandoamorim.com/jfa-unify-backend:latest
docker pull registry.jfernandoamorim.com/jfa-unify-frontend:latest

# 6. Restore database
docker-compose exec postgres pg_restore -d jfa_unify /tmp/db_full_YESTERDAY.dump

# 7. Notify clients: "Service restored from 24h backup; reviewing incident"
```

---

## Testing & Validation

### Monthly Backup Test

**Schedule:** First Tuesday of every month

**Procedure:**

```bash
#!/bin/bash

# 1. Restore to test environment (separate VM)
docker-compose -f docker-compose.test.yml up -d

# 2. Download backup from S3
aws s3 cp s3://jfa-unify-backups/postgresql/db_full_latest.dump /tmp/

# 3. Restore to test database
docker exec jfa_unify_postgres_test pg_restore \
  -U $DB_USER -d jfa_unify_test /tmp/db_full_latest.dump

# 4. Run validation queries
docker exec jfa_unify_postgres_test psql -U $DB_USER -d jfa_unify_test << EOF
  SELECT COUNT(*) as device_count FROM devices;
  SELECT COUNT(*) as access_log_count FROM access_logs;
  SELECT COUNT(*) as tenant_count FROM tenants;
  SELECT MAX(created_at) as latest_log FROM access_logs;
EOF

# 5. Verify application boots with restored data
docker-compose -f docker-compose.test.yml up backend
curl http://localhost:8000/health

# 6. Report results
echo "✅ Backup test passed on $(date)" | \
  mail -s "JFA Unify Backup Test - PASSED" ops@jfernandoamorim.com
```

---

## Backup Retention Policy

| Backup Type | Retention | Storage | Cost |
|-------------|-----------|---------|------|
| Daily full (PostgreSQL) | 30 days | S3 Standard | ~EUR 10/month |
| Hourly WAL (PostgreSQL) | 7 days | S3 Standard | ~EUR 5/month |
| Redis RDB | 7 days | Local + S3 | ~EUR 2/month |
| Git bundles | Unlimited | GitHub + S3 Glacier | ~EUR 5/month |
| **Total monthly** | — | — | **~EUR 22/month** |

---

## RTO/RPO Targets

| Scenario | RTO | RPO | Difficulty |
|----------|-----|-----|-----------|
| Single service restart | 5 min | 0 min | Easy |
| Database corruption | 15 min | 1 hour | Medium |
| VM failure | 30 min | 1 hour | Medium |
| Zone failure | 1 hour | 1 hour | Hard |
| Complete data loss | 2-4 hours | 24 hours | Hard |

---

## Checklist

- [ ] Daily backup script in cron
- [ ] S3 bucket configured with versioning + lifecycle
- [ ] Monthly backup restoration tests scheduled
- [ ] Incident response playbook documented
- [ ] Team trained on recovery procedures
- [ ] Secondary VM provisioned (cold standby)
- [ ] DNS failover scripts tested
- [ ] External backup (Glacier) verified
