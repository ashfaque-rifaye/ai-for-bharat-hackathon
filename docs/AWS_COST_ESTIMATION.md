# VaaniSetu — AWS Cost Estimation & Service Mapping

## Budget: $100 AWS Credits

---

## 1. Service-by-Service Cost Breakdown

### 1.1 Amazon Bedrock (AI/LLM) — ~$30-35

| Model | Use Case | Pricing | Est. Usage | Est. Cost |
|-------|----------|---------|------------|-----------|
| Claude 3 Haiku (Input) | Conversation AI | $0.25/1M tokens | ~2M tokens | $0.50 |
| Claude 3 Haiku (Output) | Conversation AI | $1.25/1M tokens | ~1M tokens | $1.25 |
| Claude 3 Sonnet (Input) | Complex reasoning (fallback) | $3/1M tokens | ~200K tokens | $0.60 |
| Claude 3 Sonnet (Output) | Complex reasoning (fallback) | $15/1M tokens | ~100K tokens | $1.50 |
| Titan Embeddings v2 | Scheme document embeddings | $0.02/1M tokens | ~500K tokens | $0.01 |
| Bedrock Knowledge Base | RAG management | No additional charge | — | $0 |
| **Subtotal** | | | | **~$4** |

> **Note:** During development, expect 10x more usage for testing. Budget **$30-35** total.

### 1.2 Amazon OpenSearch Serverless — ~$15-20

| Component | Pricing | Est. Usage | Est. Cost |
|-----------|---------|------------|-----------|
| Indexing OCU | $0.24/OCU/hour | 0.5 OCU × 200 hrs | $24 |
| Search OCU | $0.24/OCU/hour | 0.5 OCU × 200 hrs | $24 |

> ⚠️ **OpenSearch Serverless is expensive!** Minimum 0.5 OCU each.
> **Alternative:** Use Bedrock KB with **Pinecone** (free tier: 1 index, 100K vectors) or **in-memory FAISS** in Lambda to avoid this cost entirely.

**Recommended: Skip OpenSearch, use one of these alternatives:**

| Alternative | Cost | Trade-off |
|------------|------|-----------|
| **FAISS in Lambda** | $0 | Load embeddings from S3, search in-memory. Limited to ~10K docs. |
| **Bedrock KB with S3** | $0 | Bedrock KB can use built-in vector search with S3 data source |
| **DynamoDB + manual embedding** | $0 | Store embeddings as DynamoDB items, scan + cosine similarity |

### 1.3 Amazon Transcribe — ~$8-12

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Streaming transcription | $0.024/min | ~200 min testing | $4.80 |
| Language detection | Included | — | $0 |

> Free tier: 60 minutes/month for 12 months

### 1.4 Amazon Polly — ~$5-8

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Neural TTS | $16/1M chars | ~300K chars | $4.80 |
| Standard TTS | $4/1M chars | ~100K chars (fallback) | $0.40 |

> Free tier: 5M chars/month for 12 months (standard), 1M chars/month (neural)

### 1.5 Amazon Translate — ~$2-3

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Translation | $15/1M chars | ~150K chars | $2.25 |

> Free tier: 2M chars/month for 12 months

### 1.6 AWS Lambda — ~$1-2

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Requests | $0.20/1M requests | ~50K requests | $0.01 |
| Duration | $0.0000166667/GB-sec | ~10K GB-seconds | $0.17 |

> Free tier: 1M requests + 400K GB-seconds/month → **likely $0**

### 1.7 Amazon API Gateway — ~$1-2

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| WebSocket messages | $1/1M messages | ~100K messages | $0.10 |
| REST API calls | $3.50/1M calls | ~50K calls | $0.18 |
| Connection minutes | $0.25/1M minutes | ~5K minutes | $0.001 |

> Free tier: 1M REST calls/month → **likely $0**

### 1.8 Amazon DynamoDB — ~$1-2

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| On-demand reads | $0.25/1M RRU | ~100K reads | $0.025 |
| On-demand writes | $1.25/1M WRU | ~50K writes | $0.063 |
| Storage | $0.25/GB/month | <1 GB | $0.25 |

> Free tier: 25 GB storage + 25 WCU + 25 RCU → **likely $0**

### 1.9 Amazon S3 — ~$0.50

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Storage | $0.023/GB/month | ~1 GB | $0.023 |
| Requests | $0.005/1K PUT | ~5K requests | $0.025 |

> Free tier: 5 GB storage → **$0**

### 1.10 Amazon SNS (SMS) — ~$2-3

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| SMS (India) | $0.02356/message | ~100 SMS | $2.36 |

### 1.11 CloudWatch — ~$1-2

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Logs ingestion | $0.50/GB | ~2 GB | $1.00 |
| Metrics | $0.30/metric/month | ~20 custom metrics | $6.00 |

> **Optimization:** Use basic metrics (free) + minimal custom metrics

### 1.12 CloudFront + S3 (Frontend) — ~$0.50

| Feature | Pricing | Est. Usage | Est. Cost |
|---------|---------|------------|-----------|
| Data transfer | $0.085/GB | ~5 GB | $0.43 |
| Requests | $0.0075/10K | ~50K requests | $0.038 |

---

## 2. Cost Summary

### Optimized Budget (Recommended)

| Service | Optimized Cost | Notes |
|---------|---------------|-------|
| **Bedrock (LLM)** | $30 | Use Haiku primarily, Sonnet sparingly |
| **Transcribe** | $10 | Stay within ~400 min total |
| **Polly** | $6 | Use neural voices for demo, standard for testing |
| **Translate** | $3 | Use only when needed |
| **SNS (SMS)** | $3 | ~100 test messages |
| **Lambda** | $0 | Free tier covers dev usage |
| **API Gateway** | $0 | Free tier covers dev usage |
| **DynamoDB** | $0 | Free tier covers dev usage |
| **S3** | $0 | Free tier covers dev usage |
| **CloudFront** | $1 | Minimal demo traffic |
| **CloudWatch** | $2 | Minimal custom metrics |
| **OpenSearch** | $0 | **Use FAISS/S3 alternative** |
| **Buffer** | $45 | Safety margin for unexpected usage |
| **TOTAL** | **~$55-100** | **Within budget** |

### Cost Optimization Strategies

1. **Use Claude 3 Haiku over Sonnet** — 60x cheaper, fast enough for conversation
2. **Skip OpenSearch Serverless** — Use FAISS in Lambda or Bedrock KB with S3
3. **Leverage free tiers aggressively** — Lambda, DynamoDB, S3, API Gateway
4. **Batch Transcribe calls** — Don't leave streams open unnecessarily
5. **Cache Polly audio** — Cache common phrases in S3 (greetings, confirmations)
6. **Use standard Polly for testing** — Only neural for demo recordings
7. **Set billing alarms** — $25, $50, $75, $90 thresholds
8. **Minimize CloudWatch custom metrics** — Use embedded metric format

---

## 3. Billing Alarms Setup

```python
# CDK code for billing alarms
from aws_cdk import aws_cloudwatch as cw, aws_sns as sns

alarm_topic = sns.Topic(self, "BillingAlarmTopic")

for threshold in [25, 50, 75, 90]:
    cw.Alarm(self, f"BillingAlarm{threshold}",
        metric=cw.Metric(
            namespace="AWS/Billing",
            metric_name="EstimatedCharges",
            dimensions_map={"Currency": "USD"},
            statistic="Maximum",
            period=Duration.hours(6)
        ),
        threshold=threshold,
        evaluation_periods=1,
        alarm_description=f"AWS charges have exceeded ${threshold}"
    ).add_alarm_action(cw_actions.SnsAction(alarm_topic))
```

---

## 4. Service Availability by Region (ap-south-1 Mumbai)

| Service | Available in ap-south-1? | Notes |
|---------|------------------------|-------|
| Bedrock (Claude 3) | ✅ Yes | Claude 3 Haiku + Sonnet available |
| Bedrock Knowledge Bases | ✅ Yes | |
| Titan Embeddings | ✅ Yes | |
| Transcribe Streaming | ✅ Yes | Hindi, Tamil, English supported |
| Polly Neural | ✅ Yes | Hindi (Kajal), English-IN (Raveena) |
| Translate | ✅ Yes | All Indian languages |
| Lambda | ✅ Yes | |
| API Gateway (WS) | ✅ Yes | |
| DynamoDB | ✅ Yes | |
| OpenSearch Serverless | ✅ Yes | |
| SNS (SMS) | ✅ Yes | India SMS supported |
| S3 | ✅ Yes | |
| CloudFront | ✅ Yes (Global) | |
| Cognito | ✅ Yes | |

> ✅ All required services are available in **ap-south-1 (Mumbai)** — ideal for lowest latency to Indian users.
