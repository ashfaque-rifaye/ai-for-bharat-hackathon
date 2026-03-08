#!/usr/bin/env python3
"""Seed DynamoDB schemes table with government scheme data from JSON files."""

import json
import os
import sys
import glob
from datetime import datetime, timezone

import boto3

# Configuration
REGION = os.environ.get("AWS_REGION", "us-east-1")
SCHEMES_TABLE = os.environ.get("SCHEMES_TABLE", "vaanisetu-schemes")
SEED_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "infrastructure", "seed-data", "schemes")


def load_scheme_files(data_dir: str) -> list[dict]:
    """Load all scheme JSON files from the seed data directory."""
    schemes = []
    json_files = glob.glob(os.path.join(data_dir, "*.json"))

    if not json_files:
        print(f"❌ No JSON files found in {data_dir}")
        sys.exit(1)

    for filepath in sorted(json_files):
        with open(filepath, "r", encoding="utf-8") as f:
            scheme = json.load(f)
            scheme["updatedAt"] = datetime.now(timezone.utc).isoformat()
            schemes.append(scheme)
            print(f"  📄 Loaded {os.path.basename(filepath)} → {scheme['schemeId']}")

    return schemes


def seed_schemes(schemes: list[dict], table_name: str, region: str):
    """Write schemes to DynamoDB table using batch_writer."""
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    print(f"\n📤 Writing {len(schemes)} schemes to DynamoDB table '{table_name}'...")

    with table.batch_writer() as batch:
        for scheme in schemes:
            batch.put_item(Item=scheme)
            print(f"  ✅ {scheme['schemeId']}: {scheme['name']['en']}")

    print(f"\n🎉 Successfully seeded {len(schemes)} schemes!")


def verify_seeds(table_name: str, region: str):
    """Verify seeded data by scanning the table."""
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    response = table.scan(Select="COUNT")
    count = response["Count"]
    print(f"\n🔍 Verification: {count} items in table '{table_name}'")

    # Show categories
    response = table.scan(
        ProjectionExpression="schemeId, #n, category",
        ExpressionAttributeNames={"#n": "name"}
    )
    print("\n📋 Schemes in database:")
    print(f"{'ID':<25} {'Category':<15} {'Name'}")
    print("-" * 70)
    for item in sorted(response["Items"], key=lambda x: x["schemeId"]):
        print(f"  {item['schemeId']:<23} {item['category']:<13} {item['name']['en']}")


def upload_to_s3(schemes: list[dict], bucket_name: str, region: str):
    """Upload scheme documents to S3 for Bedrock Knowledge Base."""
    s3 = boto3.client("s3", region_name=region)

    print(f"\n📤 Uploading scheme docs to S3 bucket '{bucket_name}'...")

    for scheme in schemes:
        # Create a rich text document for RAG
        doc = create_scheme_document(scheme)
        key = f"schemes/{scheme['schemeId']}.txt"

        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=doc.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )
        print(f"  ✅ Uploaded {key}")

    print(f"\n🎉 Uploaded {len(schemes)} scheme documents to S3!")


def create_scheme_document(scheme: dict) -> str:
    """Create a rich text document from scheme data for RAG indexing."""
    lines = []

    # English version
    lines.append(f"# {scheme['name']['en']}")
    lines.append(f"Scheme ID: {scheme['schemeId']}")
    lines.append(f"Category: {scheme['category']}")
    lines.append(f"Ministry: {scheme['ministry']}")
    lines.append(f"\n## Description\n{scheme['description']['en']}")
    lines.append(f"\n## Short Description\n{scheme['shortDescription']['en']}")

    # Eligibility
    if "eligibility" in scheme and "description" in scheme["eligibility"]:
        lines.append(f"\n## Eligibility\n{scheme['eligibility']['description']['en']}")

    # Benefits
    if "benefits" in scheme:
        b = scheme["benefits"]
        lines.append(f"\n## Benefits\n{b['description']['en']}")
        if b.get("amount"):
            lines.append(f"Amount: ₹{b['amount']:,}")
        if b.get("frequency"):
            lines.append(f"Frequency: {b['frequency']}")

    # Required Documents
    if scheme.get("requiredDocuments"):
        lines.append("\n## Required Documents")
        for doc in scheme["requiredDocuments"]:
            mandatory = " (mandatory)" if doc.get("mandatory") else ""
            lines.append(f"- {doc['name']['en']}{mandatory}")

    # Hindi version (for Hindi queries in RAG)
    lines.append(f"\n\n---\n# हिंदी: {scheme['name']['hi']}")
    lines.append(f"श्रेणी: {scheme['category']}")
    lines.append(f"\n## विवरण\n{scheme['description']['hi']}")
    if "eligibility" in scheme and "description" in scheme["eligibility"]:
        lines.append(f"\n## पात्रता\n{scheme['eligibility']['description']['hi']}")
    if "benefits" in scheme:
        lines.append(f"\n## लाभ\n{scheme['benefits']['description']['hi']}")

    # Tamil version
    if scheme["name"].get("ta"):
        lines.append(f"\n\n---\n# தமிழ்: {scheme['name']['ta']}")
        lines.append(f"\n## விவரம்\n{scheme['description'].get('ta', '')}")
        if "eligibility" in scheme and "description" in scheme["eligibility"]:
            lines.append(f"\n## தகுதி\n{scheme['eligibility']['description'].get('ta', '')}")

    return "\n".join(lines)


def main():
    """Run the seed script."""
    print("=" * 60)
    print("🌾 VaaniSetu — Scheme Data Seeder")
    print("=" * 60)

    # Load schemes
    print(f"\n📂 Loading scheme data from: {SEED_DATA_DIR}")
    schemes = load_scheme_files(SEED_DATA_DIR)
    print(f"\n📊 Loaded {len(schemes)} schemes")

    # Seed DynamoDB
    seed_schemes(schemes, SCHEMES_TABLE, REGION)

    # Verify
    verify_seeds(SCHEMES_TABLE, REGION)

    # Upload to S3 (optional - needs bucket name)
    bucket_name = os.environ.get("SCHEME_DOCS_BUCKET")
    if bucket_name:
        upload_to_s3(schemes, bucket_name, REGION)
    else:
        print("\n⚠️  Set SCHEME_DOCS_BUCKET env var to also upload to S3 for RAG")

    print("\n✅ Seeding complete!")


if __name__ == "__main__":
    main()
