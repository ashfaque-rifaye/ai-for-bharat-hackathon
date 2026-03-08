"""Test all relevant Bedrock models via Converse API.
Step 1: Find which models actually respond on this AISPL account.
"""

import boto3
import time

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

# Models to test — organized by provider
MODELS = [
    # Anthropic Claude (FTU form just submitted)
    ("anthropic.claude-3-haiku-20240307-v1:0", "Claude 3 Haiku"),
    ("anthropic.claude-3-sonnet-20240229-v1:0", "Claude 3 Sonnet"),
    ("anthropic.claude-3-5-haiku-20241022-v1:0", "Claude 3.5 Haiku"),
    ("anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet v2"),
    ("us.anthropic.claude-3-5-haiku-20241022-v1:0", "Claude 3.5 Haiku (us)"),
    ("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet v2 (us)"),
    # Amazon Nova
    ("amazon.nova-pro-v1:0", "Nova Pro"),
    ("amazon.nova-lite-v1:0", "Nova Lite"),
    ("amazon.nova-micro-v1:0", "Nova Micro"),
    # Meta Llama
    ("meta.llama3-8b-instruct-v1:0", "Llama 3 8B"),
    ("meta.llama3-1-8b-instruct-v1:0", "Llama 3.1 8B"),
    ("meta.llama3-1-70b-instruct-v1:0", "Llama 3.1 70B"),
    ("meta.llama3-2-1b-instruct-v1:0", "Llama 3.2 1B"),
    ("meta.llama3-2-3b-instruct-v1:0", "Llama 3.2 3B"),
    ("us.meta.llama3-3-70b-instruct-v1:0", "Llama 3.3 70B"),
    # Mistral
    ("mistral.mistral-7b-instruct-v0:2", "Mistral 7B"),
    ("mistral.mixtral-8x7b-instruct-v0:1", "Mixtral 8x7B"),
    ("mistral.mistral-large-2402-v1:0", "Mistral Large"),
    # DeepSeek
    ("deepseek.v3.2", "DeepSeek V3.2"),
    ("deepseek.r1-v1:0", "DeepSeek R1"),
    # Google
    ("google.gemma-3-4b-it", "Gemma 3 4B"),
    ("google.gemma-3-27b-it", "Gemma 3 27B"),
]

# Test with a realistic Hindi prompt for our voice agent use case
TEST_MSG = "मुझे किसानों के लिए सरकारी योजनाओं की जानकारी चाहिए"

print("=" * 80)
print("BEDROCK MODEL TEST — VaaniSetu Voice Agent")
print(f"Test prompt: {TEST_MSG}")
print("=" * 80)
print()

working = []
failed = []

for model_id, label in MODELS:
    try:
        start = time.time()
        resp = bedrock.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": TEST_MSG}]}],
            inferenceConfig={"maxTokens": 100, "temperature": 0.3},
        )
        elapsed = time.time() - start

        text = resp["output"]["message"]["content"][0]["text"].strip()
        usage = resp.get("usage", {})
        in_tokens = usage.get("inputTokens", "?")
        out_tokens = usage.get("outputTokens", "?")

        # Truncate response for display
        display_text = text[:100].replace("\n", " ")

        print(f"  OK   | {label:28s} | {elapsed:.1f}s | in={in_tokens} out={out_tokens}")
        print(f"         {display_text}")
        working.append((model_id, label, elapsed, in_tokens, out_tokens))

    except Exception as e:
        err_name = type(e).__name__
        err_msg = str(e)[:80]
        print(f"  FAIL | {label:28s} | {err_name}: {err_msg}")
        failed.append((model_id, label, err_msg))

    print()

print("=" * 80)
print(f"RESULTS: {len(working)} WORKING / {len(failed)} FAILED")
print("=" * 80)

if working:
    print("\nWORKING MODELS:")
    for mid, lab, elapsed, inp, out in working:
        print(f"  {lab:28s} | {mid:50s} | {elapsed:.1f}s")

if failed:
    print("\nFAILED MODELS:")
    for mid, lab, err in failed:
        print(f"  {lab:28s} | {err[:60]}")
