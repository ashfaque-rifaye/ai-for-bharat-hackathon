# VaaniSetu Deployment Guide

Complete guide to deploy the VaaniSetu prototype — backend (AWS CDK), frontend (S3 + CloudFront), and integrations (WhatsApp, Connect).

---

## What's Already Deployed

| Component            | Status  | URL / ARN                                                                       |
| -------------------- | ------- | ------------------------------------------------------------------------------- |
| REST API (API GW)    | ✅ Live | `https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod`                 |
| WebSocket API        | ✅ Live | `wss://o4m08dq7pb.execute-api.us-east-1.amazonaws.com/prod`                   |
| Orchestrator Lambda  | ✅ Live | `vaanisetu-orchestrator`                                                        |
| AI Engine Lambda     | ✅ Live | `vaanisetu-ai-engine`                                                           |
| Voice Processor      | ✅ Live | `vaanisetu-voice-processor`                                                     |
| Notification Lambda  | ✅ Live | `vaanisetu-notification`                                                        |
| Post-Call Lambda     | ✅ Live | `vaanisetu-post-call`                                                           |
| WhatsApp Lambda      | ✅ Live | `vaanisetu-whatsapp`                                                            |
| DynamoDB Tables      | ✅ Live | `vaanisetu-sessions`, `vaanisetu-schemes`, `vaanisetu-applications`            |
| Bedrock Guardrail    | ✅ Live | Guardrail ID: `46tqyral1aho` v1                                                |
| Frontend             | 🟡 Built| `frontend/dist/` — needs hosting                                               |

---

## 1. Backend Deployment (CDK)

Already deployed. To redeploy after code changes:

```powershell
cd infrastructure/cdk
pip install -r requirements.txt
cdk deploy --all --require-approval never
```

Three stacks:
- **VaaniSetu-Data**: DynamoDB tables, S3 buckets
- **VaaniSetu-AI**: AI Engine Lambda, Bedrock guardrail
- **VaaniSetu-API**: API Gateway, Orchestrator, Voice Processor, WhatsApp, Notification Lambdas

### Seed Scheme Data

If the schemes table is empty, seed it:

```powershell
cd scripts
python seed_data.py
```

This loads 10 government schemes from `infrastructure/seed-data/schemes/`.

---

## 2. Frontend Deployment

### Option A: S3 + CloudFront (Recommended for Production)

#### Create S3 Bucket

```powershell
aws s3 mb s3://vaanisetu-frontend --region us-east-1
```

#### Enable Static Website Hosting

```powershell
aws s3 website s3://vaanisetu-frontend --index-document index.html --error-document index.html
```

#### Upload Build

```powershell
cd frontend
npm run build
aws s3 sync dist/ s3://vaanisetu-frontend/ --delete
```

#### Create CloudFront Distribution

1. Go to **AWS Console → CloudFront → Create Distribution**.
2. Origin domain: `vaanisetu-frontend.s3.amazonaws.com`
3. Origin access: **Origin Access Control (OAC)** — create a new OAC.
4. Default cache behaviour: **Redirect HTTP to HTTPS**.
5. Default root object: `index.html`
6. Error pages: Add custom error response for 403 → `/index.html` (200) — this enables SPA routing.
7. Click **Create Distribution**.
8. Copy the S3 bucket policy from the CloudFront console and apply it to the bucket.

#### Update S3 Bucket Policy

After creating the CloudFront distribution, update the bucket policy to allow CloudFront access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::vaanisetu-frontend/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::<ACCOUNT_ID>:distribution/<DISTRIBUTION_ID>"
                }
            }
        }
    ]
}
```

Your frontend will be available at: `https://<distribution-id>.cloudfront.net`

### Option B: Quick Demo (Vite Dev Server)

For hackathon demos, just run locally:

```powershell
cd frontend
npm run dev
```

Opens at `http://localhost:3000` — already configured to call the production AWS API.

### Option C: Vite Preview (Local Production Build)

```powershell
cd frontend
npm run build
npm run preview
```

Serves the built files on `http://localhost:4173`.

---

## 3. WhatsApp Integration (Twilio)

See [WHATSAPP_SETUP.md](./WHATSAPP_SETUP.md) for detailed step-by-step instructions.

Quick summary:
1. Create Twilio account → get Account SID + Auth Token
2. Activate WhatsApp Sandbox → join with your phone
3. Set webhook URL: `https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/whatsapp`
4. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in the Lambda env vars
5. Test by sending a message on WhatsApp

---

## 4. Amazon Connect IVR (Voice Channel)

See [CONNECT_IVR_SETUP.md](./CONNECT_IVR_SETUP.md) for detailed instructions.

Quick summary:
1. Create Amazon Connect instance in AWS Console
2. Claim a phone number (+91 India DID)
3. Create a Contact Flow that invokes the VaaniSetu Orchestrator Lambda
4. Associate the phone number with the Contact Flow
5. Test by calling the number

---

## 5. Environment Variables Reference

### Frontend (`frontend/.env` or Vite env)

| Variable           | Default  | Description                              |
| ------------------ | -------- | ---------------------------------------- |
| `VITE_API_MODE`    | `prod`   | `prod` = AWS API, `local` = mock server  |
| `VITE_API_ENDPOINT`| (auto)   | Override API URL (optional)              |
| `VITE_WS_ENDPOINT` | (auto)   | Override WebSocket URL (optional)        |

### Backend Lambda Environment Variables

All set automatically by CDK:

| Variable              | Lambda           | Value                          |
| --------------------- | ---------------- | ------------------------------ |
| `SESSIONS_TABLE`      | All              | `vaanisetu-sessions`           |
| `SCHEMES_TABLE`       | Orchestrator, AI | `vaanisetu-schemes`            |
| `APPLICATIONS_TABLE`  | Orchestrator     | `vaanisetu-applications`       |
| `AI_ENGINE_FUNCTION`  | Orchestrator     | `vaanisetu-ai-engine`          |
| `VOICE_BUCKET`        | Voice Processor  | `vaanisetu-voice-*`            |
| `BEDROCK_GUARDRAIL_ID`| AI Engine        | `46tqyral1aho`                 |
| `TWILIO_ACCOUNT_SID`  | WhatsApp         | (set manually)                 |
| `TWILIO_AUTH_TOKEN`   | WhatsApp         | (set manually)                 |

---

## 6. Verification Checklist

After deployment, verify each component:

```powershell
$base = "https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod"

# Health check
Invoke-RestMethod "$base/health"

# List schemes
(Invoke-RestMethod "$base/schemes").schemes.Count

# Create session
$session = Invoke-RestMethod -Uri "$base/sessions" -Method POST -Body '{"language":"hi-IN"}' -ContentType "application/json"
$session.sessionId

# Send message
$msg = Invoke-RestMethod -Uri "$base/sessions/$($session.sessionId)/message" -Method POST -Body '{"text":"I am a farmer in UP"}' -ContentType "application/json"
$msg.response

# Analytics
Invoke-RestMethod "$base/analytics"
```

---

## 7. Cost Estimate (Hackathon/Demo Usage)

| Service           | Free Tier           | Estimated Monthly Cost |
| ----------------- | ------------------- | ---------------------- |
| Lambda            | 1M requests free    | $0.00                  |
| API Gateway       | 1M requests free    | $0.00                  |
| DynamoDB          | 25 WCU/RCU free     | $0.00                  |
| Bedrock Claude    | No free tier        | ~$5-15 (demo usage)   |
| Polly             | 5M chars free (12mo)| $0.00                  |
| Transcribe        | 60 min/mo free      | $0.00                  |
| S3                | 5GB free            | $0.00                  |
| CloudFront        | 1TB free (12mo)     | $0.00                  |
| **Total**         |                     | **~$5-15/month**       |
