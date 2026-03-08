#!/usr/bin/env python3
"""
VaaniSetu — AWS Cost & Resource Monitor
=========================================
Shows REAL costs from AWS Cost Explorer + real usage from CloudWatch.
Cost Explorer is called sparingly ($0.01/call) — every 30 min.
CloudWatch metrics refresh every 60s (free).

Also writes plain-text snapshot to aws-costs.log.

Run: python aws-cost-monitor.py
"""

import json
import os
import re as _re
import sys
import time
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

REGION = "us-east-1"
USAGE_REFRESH = 60          # seconds — CloudWatch metrics (free)
COST_REFRESH = 1800         # seconds — Cost Explorer (30 min, $0.01/call)
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aws-costs.log")
BUDGET = 100.0


class C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def fmt_cost(val):
    if val is None:
        return f"{C.DIM}--{C.END}"
    if val == 0:
        return f"{C.GREEN}$0.00{C.END}"
    if val < 0.01:
        return f"{C.GREEN}<$0.01{C.END}"
    if val < 1.0:
        return f"{C.YELLOW}${val:.4f}{C.END}"
    return f"{C.RED}${val:.2f}{C.END}"


def fmt_cost_plain(val):
    if val is None:
        return "--"
    if val == 0:
        return "$0.00"
    return f"${val:.4f}"


def fmt_bytes(b):
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


# ═══════════════════════════════════════════════════════════════
#  Resource Discovery
# ═══════════════════════════════════════════════════════════════

def discover_resources(clients):
    res = {"dynamodb": [], "lambdas": [], "s3": [], "api_rest": [], "api_ws": []}

    try:
        for page in clients["ddb"].get_paginator("list_tables").paginate():
            for t in page.get("TableNames", []):
                if "vaanisetu" in t.lower():
                    res["dynamodb"].append(t)
    except Exception:
        pass

    try:
        for page in clients["lam"].get_paginator("list_functions").paginate():
            for fn in page.get("Functions", []):
                if "vaanisetu" in fn["FunctionName"].lower() or "VaaniSetu" in fn["FunctionName"]:
                    res["lambdas"].append(fn["FunctionName"])
    except Exception:
        pass

    try:
        for b in clients["s3"].list_buckets().get("Buckets", []):
            if "vaanisetu" in b["Name"].lower():
                res["s3"].append(b["Name"])
    except Exception:
        pass

    try:
        for api in clients["apigw"].get_rest_apis().get("items", []):
            if "vaanisetu" in api["name"].lower() or "VaaniSetu" in api["name"]:
                res["api_rest"].append({"id": api["id"], "name": api["name"]})
    except Exception:
        pass

    try:
        for api in clients["apigwv2"].get_apis().get("Items", []):
            if "vaanisetu" in api.get("Name", "").lower() or "VaaniSetu" in api.get("Name", ""):
                res["api_ws"].append({"id": api["ApiId"], "name": api["Name"]})
    except Exception:
        pass

    return res


def check_lambda_status(clients, lambda_names):
    statuses = {}
    for fn in lambda_names:
        try:
            resp = clients["lam"].get_function_concurrency(FunctionName=fn)
            conc = resp.get("ReservedConcurrentExecutions")
            statuses[fn] = "STOPPED" if conc == 0 else f"active (reserved={conc})"
        except clients["lam"].exceptions.ResourceNotFoundException:
            statuses[fn] = "active"
        except Exception:
            statuses[fn] = "active"
    return statuses


# ═══════════════════════════════════════════════════════════════
#  CloudWatch Usage Metrics (FREE)
# ═══════════════════════════════════════════════════════════════

def get_cw_usage(clients, resources, hours=24):
    cw = clients["cw"]
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    usage = {}

    ddb_r = ddb_w = 0
    for table in resources["dynamodb"]:
        for metric, target in [("ConsumedReadCapacityUnits", "r"), ("ConsumedWriteCapacityUnits", "w")]:
            try:
                resp = cw.get_metric_statistics(
                    Namespace="AWS/DynamoDB", MetricName=metric,
                    Dimensions=[{"Name": "TableName", "Value": table}],
                    StartTime=start, EndTime=end, Period=3600, Statistics=["Sum"],
                )
                val = sum(p["Sum"] for p in resp.get("Datapoints", []))
                if target == "r":
                    ddb_r += val
                else:
                    ddb_w += val
            except Exception:
                pass
    usage["ddb_reads"] = ddb_r
    usage["ddb_writes"] = ddb_w

    invocations = errors = throttles = 0
    total_duration = 0
    for fn in resources["lambdas"]:
        for metric, stat in [("Invocations", "Sum"), ("Errors", "Sum"), ("Throttles", "Sum"), ("Duration", "Average")]:
            try:
                resp = cw.get_metric_statistics(
                    Namespace="AWS/Lambda", MetricName=metric,
                    Dimensions=[{"Name": "FunctionName", "Value": fn}],
                    StartTime=start, EndTime=end, Period=3600, Statistics=[stat],
                )
                pts = resp.get("Datapoints", [])
                if not pts:
                    continue
                if stat == "Sum":
                    v = sum(p["Sum"] for p in pts)
                else:
                    v = pts[-1]["Average"]
                if metric == "Invocations":
                    invocations += v
                elif metric == "Errors":
                    errors += v
                elif metric == "Throttles":
                    throttles += v
                elif metric == "Duration":
                    total_duration += v
            except Exception:
                pass
    usage["lambda_invocations"] = invocations
    usage["lambda_errors"] = errors
    usage["lambda_throttles"] = throttles
    usage["lambda_avg_ms"] = total_duration / max(len(resources["lambdas"]), 1)

    api_calls = 0
    for api in resources["api_rest"]:
        try:
            resp = cw.get_metric_statistics(
                Namespace="AWS/ApiGateway", MetricName="Count",
                Dimensions=[{"Name": "ApiName", "Value": api["name"]}],
                StartTime=start, EndTime=end, Period=3600, Statistics=["Sum"],
            )
            api_calls += sum(p["Sum"] for p in resp.get("Datapoints", []))
        except Exception:
            pass
    usage["api_requests"] = api_calls

    s3_bytes = 0
    for bucket in resources["s3"]:
        try:
            resp = cw.get_metric_statistics(
                Namespace="AWS/S3", MetricName="BucketSizeBytes",
                Dimensions=[{"Name": "BucketName", "Value": bucket}, {"Name": "StorageType", "Value": "StandardStorage"}],
                StartTime=end - timedelta(days=2), EndTime=end, Period=86400, Statistics=["Average"],
            )
            pts = resp.get("Datapoints", [])
            if pts:
                s3_bytes += sorted(pts, key=lambda p: p["Timestamp"])[-1]["Average"]
        except Exception:
            pass
    usage["s3_bytes"] = s3_bytes

    return usage


# ═══════════════════════════════════════════════════════════════
#  AWS Cost Explorer — REAL billing ($0.01/call)
# ═══════════════════════════════════════════════════════════════

def get_real_costs(ce_client):
    today = datetime.now(timezone.utc).date()
    start = today.replace(day=1)
    if today.day == 1:
        prev = today - timedelta(days=1)
        start = prev.replace(day=1)

    result = {"services": [], "total": 0.0, "error": None, "fetched_at": datetime.now().strftime("%H:%M:%S"), "forecast": None}

    try:
        resp = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": today.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        for period in resp.get("ResultsByTime", []):
            for group in period.get("Groups", []):
                svc = group["Keys"][0]
                amt = float(group["Metrics"]["UnblendedCost"]["Amount"])
                if amt > 0:
                    result["services"].append((svc, amt))
                    result["total"] += amt
        result["services"].sort(key=lambda x: -x[1])
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "DataUnavailableException":
            result["error"] = "no_data"
        else:
            result["error"] = f"{code}: {e.response['Error']['Message']}"
    except Exception as e:
        result["error"] = str(e)

    try:
        tomorrow = today + timedelta(days=1)
        eom = today.replace(month=today.month + 1, day=1) if today.month < 12 else today.replace(year=today.year + 1, month=1, day=1)
        if tomorrow < eom:
            resp = ce_client.get_cost_forecast(
                TimePeriod={"Start": tomorrow.isoformat(), "End": eom.isoformat()},
                Metric="UNBLENDED_COST", Granularity="MONTHLY",
            )
            result["forecast"] = float(resp.get("Total", {}).get("Amount", 0))
    except Exception:
        pass

    return result


# ═══════════════════════════════════════════════════════════════
#  Render Dashboard
# ═══════════════════════════════════════════════════════════════

def render(resources, lambda_statuses, usage, costs, refresh_n, fetch_time, next_cost_refresh):
    clear()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    def p(text="", log_text=None):
        print(text)
        clean = _re.sub(r'\033\[[0-9;]*m', '', log_text if log_text is not None else text)
        lines.append(clean)

    p(f"{C.BOLD}{C.CYAN}{'='*72}{C.END}")
    p(f"{C.BOLD}{C.CYAN}  VaaniSetu — AWS Cost & Resource Monitor{C.END}")
    p(f"{C.BOLD}{C.CYAN}{'='*72}{C.END}")
    p(f"  {C.DIM}Region: {REGION} | Account: 786684642160 | {now}{C.END}")
    p(f"  {C.DIM}Refresh #{refresh_n} | Fetch: {fetch_time:.1f}s | Next billing check: {next_cost_refresh}{C.END}")
    p()

    # ── Resources & Status ─────────────────────────────────────
    p(f"{C.BOLD}{C.BLUE}  DEPLOYED RESOURCES & STATUS{C.END}")
    p(f"  {C.DIM}{'─'*55}{C.END}")

    any_stopped = any("STOPPED" in s for s in lambda_statuses.values())
    backend_status = f"{C.RED}STOPPED{C.END}" if any_stopped else f"{C.GREEN}RUNNING{C.END}"
    p(f"  Backend Status: {backend_status}", f"  Backend Status: {'STOPPED' if any_stopped else 'RUNNING'}")
    p()

    p(f"  {C.BOLD}DynamoDB ({len(resources['dynamodb'])}){C.END}")
    for t in resources["dynamodb"]:
        p(f"    {t}")

    p(f"  {C.BOLD}Lambda ({len(resources['lambdas'])}){C.END}")
    for fn in resources["lambdas"]:
        st = lambda_statuses.get(fn, "unknown")
        color = C.RED if "STOPPED" in st else C.GREEN
        p(f"    {fn:<55} {color}{st}{C.END}", f"    {fn:<55} {st}")

    p(f"  {C.BOLD}S3 ({len(resources['s3'])}){C.END}")
    for b in resources["s3"]:
        p(f"    {b}")

    p(f"  {C.BOLD}API Gateway{C.END}")
    for api in resources["api_rest"]:
        p(f"    REST: {api['name']} ({api['id']})")
    for api in resources["api_ws"]:
        p(f"    WS:   {api['name']} ({api['id']})")
    p()

    # ── Usage (CloudWatch — real, free) ────────────────────────
    p(f"{C.BOLD}{C.BLUE}  REAL USAGE (CloudWatch, last 24h){C.END}")
    p(f"  {C.DIM}{'─'*55}{C.END}")

    dr = usage.get("ddb_reads", 0)
    dw = usage.get("ddb_writes", 0)
    inv = usage.get("lambda_invocations", 0)
    err = usage.get("lambda_errors", 0)
    thr = usage.get("lambda_throttles", 0)
    avg = usage.get("lambda_avg_ms", 0)
    api = usage.get("api_requests", 0)
    s3b = usage.get("s3_bytes", 0)

    ec = C.RED if err > 0 else C.GREEN
    tc = C.RED if thr > 0 else C.GREEN

    p(f"  {'DynamoDB Reads:':<28} {dr:>10,.0f} RCU")
    p(f"  {'DynamoDB Writes:':<28} {dw:>10,.0f} WCU")
    p(f"  {'Lambda Invocations:':<28} {inv:>10,.0f}")
    p(f"  {'Lambda Avg Duration:':<28} {avg:>10,.0f} ms")
    p(f"  {'Lambda Errors:':<28} {ec}{err:>10,.0f}{C.END}", f"  {'Lambda Errors:':<28} {err:>10,.0f}")
    p(f"  {'Lambda Throttles:':<28} {tc}{thr:>10,.0f}{C.END}", f"  {'Lambda Throttles:':<28} {thr:>10,.0f}")
    p(f"  {'API Gateway Requests:':<28} {api:>10,.0f}")
    p(f"  {'S3 Storage:':<28} {fmt_bytes(s3b):>10}")
    p()

    # ── Real Costs (Cost Explorer) ─────────────────────────────
    p(f"{C.BOLD}{C.BLUE}  ACTUAL AWS BILL (Cost Explorer){C.END}")
    p(f"  {C.DIM}{'─'*55}{C.END}")
    p(f"  {C.DIM}Last fetched: {costs.get('fetched_at', 'pending')} | $0.01 per query — refreshes every 30 min{C.END}")

    if costs.get("error") == "no_data":
        p(f"  {C.GREEN}No charges recorded this billing period{C.END}", "  No charges recorded this billing period")
    elif costs.get("error"):
        p(f"  {C.YELLOW}Warning: {costs['error']}{C.END}", f"  Warning: {costs['error']}")
    elif costs["services"]:
        for svc, amt in costs["services"]:
            short = svc.replace("Amazon ", "").replace("AWS ", "")
            if len(short) > 38:
                short = short[:35] + "..."
            p(f"  {short:<40} {fmt_cost(amt)}", f"  {short:<40} {fmt_cost_plain(amt)}")
        p(f"  {C.DIM}{'─'*55}{C.END}")
        p(f"  {C.BOLD}{'Month-to-Date Total:':<40} {fmt_cost(costs['total'])}{C.END}",
          f"  {'Month-to-Date Total:':<40} {fmt_cost_plain(costs['total'])}")
        if costs.get("forecast"):
            p(f"  {C.BOLD}{'Forecasted Month End:':<40} {fmt_cost(costs['forecast'])}{C.END}",
              f"  {'Forecasted Month End:':<40} {fmt_cost_plain(costs['forecast'])}")
    else:
        p(f"  {C.GREEN}$0.00 — No charges this month{C.END}", "  $0.00 — No charges this month")
    p()

    # ── Budget ─────────────────────────────────────────────────
    total = costs.get("total", 0)
    remaining = BUDGET - total
    pct = (total / BUDGET) * 100

    bar_w = 40
    filled = int(bar_w * min(pct, 100) / 100)
    bc = C.GREEN if pct < 50 else C.YELLOW if pct < 80 else C.RED
    bar = f"{bc}{'█' * filled}{C.DIM}{'░' * (bar_w - filled)}{C.END}"

    p(f"{C.BOLD}{C.BLUE}  HACKATHON BUDGET ($100){C.END}")
    p(f"  {C.DIM}{'─'*55}{C.END}")
    p(f"  [{bar}] {pct:.1f}%", f"  [{'#' * filled}{'.' * (bar_w - filled)}] {pct:.1f}%")
    p(f"  {'Spent:':<15} {fmt_cost(total)}", f"  {'Spent:':<15} {fmt_cost_plain(total)}")
    p(f"  {'Remaining:':<15} {C.BOLD}{C.GREEN}${remaining:.2f}{C.END}", f"  {'Remaining:':<15} ${remaining:.2f}")
    p()

    p(f"  {C.DIM}Usage refreshes every {USAGE_REFRESH}s (free) | Billing every {COST_REFRESH//60} min ($0.01){C.END}")
    p(f"  {C.DIM}Stop backend:  python vaanisetu-control.py stop{C.END}")
    p(f"  {C.DIM}Start backend: python vaanisetu-control.py start{C.END}")
    p(f"  {C.DIM}Press Ctrl+C to stop monitor{C.END}")
    p(f"{C.BOLD}{C.CYAN}{'='*72}{C.END}")
    sys.stdout.flush()

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ═══════════════════════════════════════════════════════════════
#  Main Loop
# ═══════════════════════════════════════════════════════════════

def main():
    print(f"{C.BOLD}Initializing AWS Cost Monitor...{C.END}")
    try:
        session = boto3.Session(region_name=REGION)
        sts = session.client("sts")
        arn = sts.get_caller_identity()["Arn"]
        print(f"  Authenticated: {arn}")
    except NoCredentialsError:
        print(f"{C.RED}No AWS credentials. Run 'aws configure'.{C.END}")
        sys.exit(1)

    clients = {
        "ddb": session.client("dynamodb"),
        "lam": session.client("lambda"),
        "s3": session.client("s3"),
        "apigw": session.client("apigateway"),
        "apigwv2": session.client("apigatewayv2"),
        "cw": session.client("cloudwatch"),
        "ce": session.client("ce", region_name="us-east-1"),
    }

    resources = None
    costs = {"services": [], "total": 0.0, "error": None, "fetched_at": "pending"}
    last_cost_fetch = 0
    refresh_n = 0

    try:
        while True:
            refresh_n += 1
            t0 = time.time()

            if resources is None or refresh_n % 5 == 1:
                resources = discover_resources(clients)

            statuses = check_lambda_status(clients, resources["lambdas"])
            usage = get_cw_usage(clients, resources)

            now_ts = time.time()
            if now_ts - last_cost_fetch >= COST_REFRESH:
                costs = get_real_costs(clients["ce"])
                last_cost_fetch = now_ts

            elapsed = time.time() - t0
            secs_left = max(0, COST_REFRESH - (time.time() - last_cost_fetch))
            next_cost = f"in {int(secs_left//60)}m {int(secs_left%60)}s"

            render(resources, statuses, usage, costs, refresh_n, elapsed, next_cost)
            time.sleep(USAGE_REFRESH)

    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Monitor stopped.{C.END}")


if __name__ == "__main__":
    main()
