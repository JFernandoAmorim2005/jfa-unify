# Landing Page Deployment Guide (jfaunify.pt/madeira)

## Current Status

**File:** `frontend/landing/index.html` (ready)
**Status:** ✅ Content 100% complete, HTML/CSS ready
**Next step:** Deploy to production

---

## Deployment Options

### Option A: Static Hosting (AWS S3 + CloudFront) — RECOMMENDED

**Fastest, cheapest, reliable**

**Setup (10 minutes):**

```bash
# 1. Create S3 bucket
aws s3 mb s3://jfa-unify-madeira-landing

# 2. Enable static website hosting
aws s3 website s3://jfa-unify-madeira-landing \
  --index-document index.html \
  --error-document index.html

# 3. Upload HTML
aws s3 cp frontend/landing/index.html s3://jfa-unify-madeira-landing/

# 4. Set public read access
aws s3api put-bucket-policy \
  --bucket jfa-unify-madeira-landing \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::jfa-unify-madeira-landing/*"
    }]
  }'

# 5. Create CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name jfa-unify-madeira-landing.s3.amazonaws.com \
  --default-root-object index.html

# 6. Update DNS
# In your domain registrar, add CNAME:
# madeira.jfaunify.pt CNAME d123456.cloudfront.net
```

**Cost:** ~EUR 1-2/month (S3 + CloudFront)
**Performance:** <100ms global, CDN cached
**Uptime:** 99.99% (AWS SLA)

---

### Option B: Docker Container (ubuntu-50)

**If you want to host on your own server**

**Setup (20 minutes):**

```bash
# 1. Create Dockerfile.landing
cat > frontend/landing/Dockerfile << 'EOF'
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

# 2. Create nginx.conf
cat > frontend/landing/nginx.conf << 'EOF'
events { worker_connections 1024; }
http {
  server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    try_files $uri /index.html =404;
  }
}
EOF

# 3. Build image
docker build -t jfa-unify-landing:latest frontend/landing/

# 4. Run container
docker run -d \
  --name jfa-landing \
  -p 8080:80 \
  jfa-unify-landing:latest

# 5. Test
curl http://localhost:8080

# 6. Add to docker-compose.prod.yml (optional)
# Set up nginx reverse proxy to route madeira.jfaunify.pt → :8080
```

**Cost:** Included in ubuntu-50 hosting
**Performance:** Depends on network
**Uptime:** Depends on your infrastructure

---

### Option C: Vercel / Netlify (For rapid testing)

**Fastest to go live (5 minutes)**

```bash
# 1. Push to GitHub
git add frontend/landing/index.html
git commit -m "feat: Madeira landing page"
git push origin main

# 2. Connect repository to Vercel
# Visit vercel.com → Import project → Select GitHub repo

# 3. Configure build
# Build command: (none, static site)
# Output directory: frontend/landing/

# 4. Deploy
# Vercel auto-deploys on git push

# 5. Add custom domain
# In Vercel dashboard: Settings → Domains → Add madeira.jfaunify.pt
# Update DNS CNAME to Vercel's nameservers
```

**Cost:** Free tier (unlimited deploys), EUR 20/month for custom domain
**Performance:** Global CDN (Vercel edge network)
**Uptime:** 99.99%

---

## Recommended: AWS S3 + CloudFront (Option A)

### Full Setup Script

```bash
#!/bin/bash

BUCKET_NAME="jfa-unify-madeira-landing"
DOMAIN="madeira.jfaunify.pt"
REGION="eu-west-1"

echo "=== JFA Unify Landing Page Deployment ==="

# Step 1: Create S3 bucket
echo "Creating S3 bucket..."
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Step 2: Upload file
echo "Uploading index.html..."
aws s3 cp frontend/landing/index.html s3://$BUCKET_NAME/

# Step 3: Set bucket policy
echo "Setting public access..."
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::'"$BUCKET_NAME"'/*"
  }]
}'

# Step 4: Create CloudFront distribution
echo "Creating CloudFront distribution..."
aws cloudfront create-distribution \
  --origin-domain-name $BUCKET_NAME.s3.amazonaws.com \
  --default-root-object index.html \
  --enabled \
  --comment "JFA Unify Madeira Landing Page" \
  --default-cache-behavior \
  "AllowedMethods={Items=[GET,HEAD],Quantity=2},CachePolicyId=658327ea-f89d-4fab-a63d-7e88639e58f6,Compress=true,TargetOriginId=myOrigin,ViewerProtocolPolicy=redirect-to-https" \
  --origins "Items=[{DomainName=$BUCKET_NAME.s3.amazonaws.com,Id=myOrigin,S3OriginConfig={}}],Quantity=1" \
  > /tmp/distribution.json

DISTRIBUTION_ID=$(jq -r '.Distribution.Id' /tmp/distribution.json)
DISTRIBUTION_DOMAIN=$(jq -r '.Distribution.DomainName' /tmp/distribution.json)

echo "✅ Distribution created: $DISTRIBUTION_ID"
echo "✅ Domain: $DISTRIBUTION_DOMAIN"
echo ""
echo "Next steps:"
echo "1. Update DNS CNAME: $DOMAIN → $DISTRIBUTION_DOMAIN"
echo "2. Wait 15 minutes for DNS propagation"
echo "3. Test: curl https://$DOMAIN"
```

---

## Post-Deployment Verification

```bash
#!/bin/bash

DOMAIN="madeira.jfaunify.pt"

echo "=== Landing Page Verification ==="

# 1. Check DNS resolution
echo "1. Checking DNS..."
dig +short $DOMAIN

# 2. Check HTTP/HTTPS
echo "2. Checking HTTP response..."
curl -I https://$DOMAIN

# 3. Check SSL certificate
echo "3. Checking SSL..."
openssl s_client -connect $DOMAIN:443 -servername $DOMAIN

# 4. Performance test
echo "4. Page load time..."
time curl -s https://$DOMAIN > /dev/null

# 5. Mobile check
echo "5. Testing mobile responsiveness..."
# Use Lighthouse API or online tool (gtmetrix.com)

echo "✅ All checks passed!"
```

---

## Monitoring & Updates

### Continuous Deployment (Auto-update on git push)

If using S3 + GitHub Actions:

```yaml
# .github/workflows/deploy-landing.yml
name: Deploy Landing Page

on:
  push:
    branches: [main]
    paths: ['frontend/landing/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Upload to S3
        run: |
          aws s3 cp frontend/landing/index.html s3://jfa-unify-madeira-landing/
      
      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_DIST_ID }} \
            --paths "/*"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

## Tracking & Analytics

Add Google Analytics or Plausible:

```html
<!-- In frontend/landing/index.html -->

<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>

<!-- Or Plausible (privacy-friendly) -->
<script defer data-domain="madeira.jfaunify.pt" src="https://plausible.io/js/plausible.js"></script>
```

**Track:**
- Page views (overall traffic)
- CTA clicks (demo request, pricing, contact)
- Bounce rate (if >60%, improve messaging)
- Referrers (where traffic comes from)

---

## Domain Setup (jfaunify.pt)

**Prerequisites:**
- Domain registered (jfaunify.pt)
- Domain registrar access (GoDaddy, Namecheap, AWS Route53, etc.)

**For AWS Route53 (recommended):**

```bash
# 1. Create hosted zone for jfaunify.pt
aws route53 create-hosted-zone \
  --name jfaunify.pt \
  --caller-reference $(date +%s)

# 2. Get nameservers
aws route53 list-hosted-zones-by-name --dns-name jfaunify.pt

# 3. Update domain registrar to use these nameservers
# (In your registrar dashboard, set nameservers to AWS Route53 values)

# 4. Create CNAME record for madeira subdomain
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "madeira.jfaunify.pt",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "d123456.cloudfront.net"}]
      }
    }]
  }'

# 5. Verify (wait 5-15 minutes for propagation)
nslookup madeira.jfaunify.pt
```

---

## Rollback Plan

**If something breaks:**

```bash
# 1. Revert to previous version (keep in S3 versioning)
aws s3 cp s3://jfa-unify-madeira-landing/index.html.bak \
  s3://jfa-unify-madeira-landing/index.html

# 2. Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"

# 3. Verify
curl https://madeira.jfaunify.pt

# 4. If still broken, revert DNS CNAME back to backup domain
# (set up backup.jfaunify.pt as failover)
```

---

## Checklist

- [ ] HTML file ready (frontend/landing/index.html)
- [ ] Domain registered (jfaunify.pt)
- [ ] S3 bucket created
- [ ] CloudFront distribution created
- [ ] DNS CNAME updated (madeira.jfaunify.pt)
- [ ] SSL certificate verified
- [ ] Site accessible (https://madeira.jfaunify.pt)
- [ ] Analytics set up (Google Analytics or Plausible)
- [ ] CTA tracked (demo request, contact form)
- [ ] Mobile responsiveness tested (gtmetrix.com)
- [ ] Backup in place (previous version in S3 versioning)

---

## Support

**If deployed on AWS:**
- CloudFront dashboard: https://console.aws.amazon.com/cloudfront/
- S3 bucket: https://s3.console.aws.amazon.com/
- CloudFront invalidation: AWS CLI or console

**If deployed on Vercel:**
- Dashboard: https://vercel.com/dashboard
- Deployments: Auto-tracked with git

**If deployed on ubuntu-50:**
- Nginx logs: `docker logs jfa-landing`
- Restart: `docker restart jfa-landing`
