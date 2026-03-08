"""Build Lambda zip and deploy."""
import boto3
import zipfile
import os
import io

base = "backend/lambdas/orchestrator"
buf = io.BytesIO()
zf = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
count = 0
for root, dirs, files in os.walk(base):
    if "__pycache__" in root:
        continue
    for f in files:
        full = os.path.join(root, f)
        arcname = os.path.relpath(full, base)
        zf.write(full, arcname)
        count += 1
zf.close()
buf.seek(0)
zip_bytes = buf.getvalue()
print(f"Files: {count}, ZIP size: {len(zip_bytes) / 1024 / 1024:.2f} MB")

# Check if under 50MB limit
if len(zip_bytes) > 50 * 1024 * 1024:
    print("ERROR: ZIP exceeds 50MB Lambda limit!")
    exit(1)

lam = boto3.client("lambda", region_name="us-east-1")
r = lam.update_function_code(
    FunctionName="vaanisetu-orchestrator",
    ZipFile=zip_bytes,
)
print(f"DEPLOYED: {r['LastModified']}")
