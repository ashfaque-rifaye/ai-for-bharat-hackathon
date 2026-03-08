# Amazon Connect IVR Setup Guide (Manual)

> **Why manual?** AISPL (Amazon India) restricts API-based Amazon Connect instance
> creation. The CDK `ConnectStack` will fail with an "access denied" error.
> You must create the Connect instance from the **AWS Console** and then wire the
> VaaniSetu Lambda manually.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| AWS Account (India) | Must be activated for Amazon Connect |
| `vaanisetu-connect-handler` Lambda | Deployed via `cdk deploy VaaniSetuConnect` (Lambda only — the instance CfnResource will fail, but the Lambda deploys fine) |
| Phone number from Connect | Claimed inside the Connect console |

---

## Step 1 — Create an Amazon Connect Instance

1. Go to **AWS Console → Amazon Connect → Create Instance**.
2. Choose **Store users within Amazon Connect** for identity management.
3. Set the instance alias to `vaanisetu` (or any unique name).
4. Skip adding an admin user for now (you can add one later).
5. Accept defaults for data storage and telephony options.
6. Click **Create instance** — this takes 2-5 minutes.
7. Note the **Instance ID** (from the URL: `https://<region>.console.aws.amazon.com/connect/home?#/instance/<INSTANCE_ID>/...`)

---

## Step 2 — Claim a Phone Number

1. Inside the Connect instance dashboard, click **Claim a phone number**.
2. Choose **DID (Direct Inward Dial)** — select your country.
3. Pick any available number.
4. Associate it with the default **Sample inbound flow** for now (we'll change it later).
5. Note the phone number.

---

## Step 3 — Add `vaanisetu-connect-handler` Lambda

1. In the **Connect console**, go to **Contact flows → AWS Lambda**.
2. Click **Add Lambda Function**.
3. Enter the ARN of the deployed `vaanisetu-connect-handler` Lambda:
   ```
   arn:aws:lambda:<region>:<account>:function:vaanisetu-connect-handler
   ```
4. Click **Add Lambda Function**.

---

## Step 4 — Create a Contact Flow

1. Go to **Contact flows → Create contact flow**.
2. Name it **VaaniSetu IVR Flow**.
3. Build the flow using the blocks below:

### Block Layout

```
[Entry Point]
      │
      ▼
[Set Voice]  →  Engine: Neural, Voice: Kajal, Language: hi-IN
      │
      ▼
[Play Prompt]  →  "नमस्ते! वाणी सेतु में आपका स्वागत है। कृपया अपना सवाल बोलें।"
      │
      ▼
[Get Customer Input]
   Type: Speech
   Timeout: 5 seconds
   Language: hi-IN
      │
      ▼
[Invoke AWS Lambda]  →  vaanisetu-connect-handler
   Timeout: 8 seconds
      │
      ▼
[Play Prompt]  →  Use $.External.response (Lambda output)
      │
      ▼
[Loop back to Get Customer Input]
      │
      ▼ (on timeout / disconnect)
[Play Prompt]  →  "धन्यवाद! वाणी सेतु का उपयोग करने के लिए शुक्रिया।"
      │
      ▼
[Disconnect]
```

### Step-by-step Block Config

1. **Set Voice** block:
   - Engine: `Neural`
   - Voice: `Kajal`
   - Language: `hi-IN`

2. **Play Prompt** (welcome):
   - Text-to-Speech: `नमस्ते! वाणी सेतु में आपका स्वागत है। कृपया अपना सवाल बोलें।`

3. **Get Customer Input** block:
   - Input type: **Speech**
   - Set timeout: 5 seconds
   - Language: `hi-IN`

4. **Invoke AWS Lambda** block:
   - Function ARN: your `vaanisetu-connect-handler`
   - Timeout: 8 seconds
   - The Lambda receives the speech transcription and returns `response` in the result

5. **Play Prompt** (response):
   - Text-to-Speech: `$.External.response`

6. **Loop** back to step 3 for multi-turn conversation.

7. **Disconnect** on timeout or error.

---

## Step 5 — Assign the Flow to Your Phone Number

1. Go to **Phone numbers** in the Connect dashboard.
2. Click on your claimed number.
3. Change Contact flow to **VaaniSetu IVR Flow**.
4. Save.

---

## Step 6 — Test the IVR

1. Call the claimed phone number from any phone.
2. Say "नमस्ते" or "किसानों के लिए योजना बताओ".
3. The Lambda should process your speech via Bedrock and respond through Polly TTS.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Lambda timeout | Increase timeout to 15s in the Invoke Lambda block |
| "Access denied" on Lambda | Re-add the Lambda ARN in Connect → Contact flows → AWS Lambda |
| No speech recognition | Check that Get Customer Input is set to "Speech" not "DTMF" |
| Hindi not working | Ensure Set Voice block has language `hi-IN` and voice `Kajal` |
| Lambda returns empty | Check CloudWatch Logs for `vaanisetu-connect-handler` |

---

## Environment Variables for the Lambda

The `vaanisetu-connect-handler` Lambda needs these env vars (set via CDK or console):

| Variable | Value |
|---|---|
| `SESSIONS_TABLE` | `vaanisetu-sessions` |
| `SCHEMES_TABLE` | `vaanisetu-schemes` |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` |
| `BEDROCK_FALLBACK_MODEL_ID` | `amazon.nova-pro-v1:0` |
| `AWS_REGION_NAME` | `us-east-1` |

---

## Multi-Language Support

To support multiple languages in the IVR:

1. Add a **Store Customer Input** (DTMF) block at the start asking users to press:
   - 1 for Hindi
   - 2 for English
   - 3 for Tamil
   - 4 for Bengali

2. Use a **Set Contact Attributes** block to store the chosen language.

3. Pass the language code to the Lambda via contact attributes.

4. Use separate **Set Voice** blocks per language path:
   - Hindi: Kajal (hi-IN)
   - English: Kajal (en-IN)
   - Tamil: Kajal (hi-IN) with Translate fallback
   - Bengali: Kajal (hi-IN) with Translate fallback
