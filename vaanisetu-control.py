#!/usr/bin/env python3
"""
VaaniSetu — Backend Control (Stop / Start / Status)
=====================================================
Hard stop:  Sets all VaaniSetu Lambda reserved concurrency to 0.
            Lambdas cannot be invoked → entire backend is disabled.
            DynamoDB + S3 remain but cost nothing when idle.

Start:      Removes the reserved concurrency limit → Lambdas run normally.

Usage:
  python vaanisetu-control.py stop     # Hard-stop all backend Lambdas
  python vaanisetu-control.py start    # Re-enable all backend Lambdas
  python vaanisetu-control.py status   # Check current state
  python vaanisetu-control.py          # Interactive menu
"""

import sys
import boto3

REGION = "us-east-1"

# ANSI
G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[1m"
D = "\033[2m"
C = "\033[96m"
E = "\033[0m"


def get_vaanisetu_lambdas(lam_client):
    """Discover all VaaniSetu Lambda functions."""
    fns = []
    for page in lam_client.get_paginator("list_functions").paginate():
        for fn in page.get("Functions", []):
            name = fn["FunctionName"]
            if "vaanisetu" in name.lower() or "VaaniSetu" in name:
                fns.append(name)
    return sorted(fns)


def get_status(lam_client, fn_name):
    """Check if a Lambda is stopped (concurrency=0) or active."""
    try:
        resp = lam_client.get_function_concurrency(FunctionName=fn_name)
        conc = resp.get("ReservedConcurrentExecutions")
        if conc == 0:
            return "STOPPED"
        return f"active (reserved={conc})"
    except lam_client.exceptions.ResourceNotFoundException:
        return "active"
    except Exception:
        return "active"


def stop_lambda(lam_client, fn_name):
    """Stop a Lambda by setting reserved concurrency to 0."""
    lam_client.put_function_concurrency(
        FunctionName=fn_name,
        ReservedConcurrentExecutions=0,
    )


def start_lambda(lam_client, fn_name):
    """Start a Lambda by removing reserved concurrency limit."""
    lam_client.delete_function_concurrency(FunctionName=fn_name)


def show_status(lam_client, lambdas):
    """Display status of all Lambdas."""
    print(f"\n{B}{C}  VaaniSetu Backend Status{E}")
    print(f"  {'─'*50}")

    all_active = True
    for fn in lambdas:
        st = get_status(lam_client, fn)
        color = R if "STOPPED" in st else G
        if "STOPPED" in st:
            all_active = False
        print(f"  {fn:<50} {color}{st}{E}")

    overall = f"{G}ALL RUNNING{E}" if all_active else f"{R}STOPPED{E}"
    print(f"\n  Overall: {overall}\n")
    return all_active


def do_stop(lam_client, lambdas):
    """Hard-stop all VaaniSetu Lambdas."""
    print(f"\n{B}{Y}  Stopping all VaaniSetu Lambdas...{E}")
    for fn in lambdas:
        st = get_status(lam_client, fn)
        if "STOPPED" in st:
            print(f"  {fn:<50} {D}already stopped{E}")
            continue
        try:
            stop_lambda(lam_client, fn)
            print(f"  {fn:<50} {R}STOPPED{E}")
        except Exception as e:
            print(f"  {fn:<50} {R}ERROR: {e}{E}")

    print(f"\n  {G}Backend is now STOPPED.{E}")
    print(f"  {D}No Lambda can be invoked. DynamoDB/S3 are idle (no cost).{E}")
    print(f"  {D}API Gateway will return errors for any request.{E}\n")


def do_start(lam_client, lambdas):
    """Re-enable all VaaniSetu Lambdas."""
    print(f"\n{B}{G}  Starting all VaaniSetu Lambdas...{E}")
    for fn in lambdas:
        st = get_status(lam_client, fn)
        if "STOPPED" not in st:
            print(f"  {fn:<50} {D}already active{E}")
            continue
        try:
            start_lambda(lam_client, fn)
            print(f"  {fn:<50} {G}STARTED{E}")
        except Exception as e:
            print(f"  {fn:<50} {R}ERROR: {e}{E}")

    print(f"\n  {G}Backend is now RUNNING.{E}")
    print(f"  {D}All Lambdas can be invoked normally.{E}\n")


def interactive(lam_client, lambdas):
    """Interactive menu."""
    while True:
        is_active = show_status(lam_client, lambdas)
        print(f"  {B}Commands:{E}")
        if is_active:
            print(f"    {Y}stop{E}   — Hard-stop all Lambdas (saves costs)")
        else:
            print(f"    {G}start{E}  — Re-enable all Lambdas")
        print(f"    {D}status{E} — Refresh status")
        print(f"    {D}quit{E}   — Exit")
        print()

        try:
            choice = input(f"  {B}>{E} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "stop":
            do_stop(lam_client, lambdas)
        elif choice == "start":
            do_start(lam_client, lambdas)
        elif choice == "status":
            continue
        elif choice in ("quit", "exit", "q"):
            break
        else:
            print(f"  {R}Unknown command: {choice}{E}\n")


def main():
    session = boto3.Session(region_name=REGION)
    lam_client = session.client("lambda")

    lambdas = get_vaanisetu_lambdas(lam_client)
    if not lambdas:
        print(f"{R}No VaaniSetu Lambda functions found in {REGION}.{E}")
        sys.exit(1)

    print(f"{B}Found {len(lambdas)} VaaniSetu Lambda functions.{E}")

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "stop":
            do_stop(lam_client, lambdas)
        elif cmd == "start":
            do_start(lam_client, lambdas)
        elif cmd == "status":
            show_status(lam_client, lambdas)
        else:
            print(f"Usage: python vaanisetu-control.py [stop|start|status]")
    else:
        interactive(lam_client, lambdas)


if __name__ == "__main__":
    main()
