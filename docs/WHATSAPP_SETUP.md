# WhatsApp Integration Setup (Twilio Sandbox)

VaaniSetu supports WhatsApp as a communication channel via Twilio's WhatsApp Sandbox.  
Users can text the bot on WhatsApp in any of the 8 supported Indian languages and receive AI-powered scheme guidance.

---

## Architecture

```
User (WhatsApp) → Twilio → API Gateway → WhatsApp Lambda → AI Engine Lambda → Bedrock Claude → Reply via TwiML
```

The WhatsApp Lambda is already deployed at:

```
POST https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/whatsapp
```

---

## Prerequisites

| Item            | Details                                          |
| --------------- | ------------------------------------------------ |
| Twilio Account  | Free trial works (https://www.twilio.io/console) |
| AWS Account     | VaaniSetu CDK stacks already deployed            |
| WhatsApp Phone  | Any phone with WhatsApp installed                |

---

## Step-by-Step Setup

### 1. Create a Twilio Account

1. Go to https://www.twilio.com/try-twilio and sign up (free trial is fine).
2. Verify your phone number.
3. From the Twilio Console dashboard, note down:
   - **Account SID** (e.g. `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   - **Auth Token** (click the eye icon to reveal)

### 2. Activate the WhatsApp Sandbox

1. In the Twilio Console, go to **Messaging → Try it out → Send a WhatsApp message**.
2. Follow the on-screen instructions:
   - Open WhatsApp on your phone.
   - Send the join code (e.g. `join <your-sandbox-word>`) to the Twilio Sandbox number shown (usually `+1 415 523 8886`).
   - You'll get a confirmation reply.

### 3. Configure the Webhook URL

1. In the Twilio Console, go to **Messaging → Settings → WhatsApp Sandbox Settings**.
2. Set the fields:

   | Field                               | Value                                                                              |
   | ----------------------------------- | ---------------------------------------------------------------------------------- |
   | **When a message comes in**         | `https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/whatsapp`            |
   | **HTTP Method**                     | `POST`                                                                             |
   | **Status callback URL** (optional)  | `https://hbm4onktgf.execute-api.us-east-1.amazonaws.com/prod/whatsapp`            |

3. Click **Save**.

### 4. Set Twilio Credentials in AWS Lambda

The WhatsApp Lambda needs your Twilio credentials for signature validation.  
Update the Lambda environment variables in the AWS Console:

1. Go to **AWS Console → Lambda → Functions → vaanisetu-whatsapp**.
2. Click **Configuration → Environment variables → Edit**.
3. Add or update:

   | Key                    | Value                              |
   | ---------------------- | ---------------------------------- |
   | `TWILIO_ACCOUNT_SID`   | Your Twilio Account SID            |
   | `TWILIO_AUTH_TOKEN`     | Your Twilio Auth Token             |

4. Click **Save**.

> **Alternative (CDK)**: You can also set these in `infrastructure/cdk/stacks/api_stack.py` under the WhatsApp Lambda environment variables and redeploy.

### 5. Test the Integration

1. Open WhatsApp on your phone.
2. Send a message to the Twilio Sandbox number (the one you joined in Step 2).
3. Try these test messages:

   | Message                                       | Expected Behaviour                              |
   | --------------------------------------------- | ----------------------------------------------- |
   | `Hi`                                          | Hindi greeting + introduction to VaaniSetu      |
   | `I am a farmer in UP with 2 acres of land`    | Scheme recommendations (PM-KISAN, RKVY, etc.)  |
   | `Tell me about PM-KISAN`                      | Scheme details + eligibility check              |
   | `मैं किसान हूँ`                                | Hindi response — automatic language detection    |
   | `நான் ஒரு விவசாயி`                               | Tamil response — automatic language detection    |

---

## How It Works

1. **Twilio** receives the WhatsApp message and POSTs the form-encoded payload to our webhook.
2. **WhatsApp Lambda** parses the message, looks up (or creates) a session keyed by the phone number hash.
3. **AI Engine Lambda** is invoked with the message + conversation history.
4. **Bedrock Claude 3 Haiku** generates a context-aware response in the user's detected language.
5. The response is returned as **TwiML XML**, which Twilio delivers back to the user on WhatsApp.

Sessions are **stateful** — the bot remembers the conversation for 7 days per phone number.

---

## Troubleshooting

| Issue                          | Fix                                                                                 |
| ------------------------------ | ----------------------------------------------------------------------------------- |
| No reply from bot              | Check CloudWatch Logs for `vaanisetu-whatsapp` Lambda                               |
| "Could not process" reply      | Verify AI_ENGINE_FUNCTION env var points to `vaanisetu-ai-engine`                   |
| Twilio webhook error (11200)   | Ensure the webhook URL is correct and returns 200 with TwiML XML                    |
| Signature validation failure   | Ensure TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are correct                         |
| Messages in wrong language     | The bot auto-detects language; first message defaults to Hindi                       |

---

## Production Considerations (Post-Hackathon)

- **Twilio WhatsApp Business API**: Migrate from Sandbox to a verified WhatsApp Business number.
- **Request signature validation**: Uncomment/add Twilio signature verification in the Lambda.
- **Rate limiting**: Add API Gateway throttling to prevent abuse.
- **Media support**: Current implementation handles text only; add image/document handling for Aadhaar uploads.
