"""CLI for x402 Payment Harness.

Usage:
    x402-pay --key 0xPRIVATE_KEY https://example.com/api
    x402-pay --key 0xPRIVATE_KEY --to 0xRECIPIENT --amount 0.005 https://example.com/api
    x402-pay --env-key MY_PRIVATE_KEY_VAR https://example.com/api
"""
import argparse
import json
import os
import sys

from .client import X402Client
from .models import PaymentConfig


def main():
    parser = argparse.ArgumentParser(
        prog="x402-pay",
        description="Test x402 payments from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pay a protected URL with your private key
  x402-pay --key 0xYOUR_PRIVATE_KEY https://x402-discovery-api.onrender.com/discover?q=test

  # Specify recipient and amount
  x402-pay --key 0xYOUR_KEY --to 0xRECIPIENT --amount 0.01 https://api.example.com/endpoint

  # Use environment variable for the key (safer)
  export X402_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
  x402-pay --env-key X402_PRIVATE_KEY https://api.example.com/endpoint

  # Verbose output (show the full payment header)
  x402-pay --key 0xYOUR_KEY --verbose https://api.example.com/endpoint
        """,
    )
    parser.add_argument("url", help="URL to pay and access")
    key_group = parser.add_mutually_exclusive_group(required=True)
    key_group.add_argument("--key", metavar="HEX", help="Private key (hex, 0x-prefixed)")
    key_group.add_argument("--env-key", metavar="ENV_VAR", help="Env var containing private key")
    parser.add_argument("--to", metavar="ADDRESS", help="Recipient address (overrides server challenge)")
    parser.add_argument("--amount", type=float, metavar="USD", help="Amount in USD (overrides server challenge)")
    parser.add_argument("--network", default="eip155:8453", help="Network (default: eip155:8453 = Base mainnet)")
    parser.add_argument("--method", default="GET", help="HTTP method (default: GET)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show payment header and full response")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")

    args = parser.parse_args()

    # Resolve private key
    if args.env_key:
        private_key = os.environ.get(args.env_key)
        if not private_key:
            print(f"Error: environment variable '{args.env_key}' not set", file=sys.stderr)
            sys.exit(1)
    else:
        private_key = args.key

    config = PaymentConfig(
        private_key=private_key,
        to=args.to,
        amount_usd=args.amount,
        network=args.network,
    )

    client = X402Client(timeout=args.timeout)

    if not args.json_output:
        print(f"🔑 Sender: {config.sender_address}")
        print(f"🌐 URL: {args.url}")
        print(f"💸 Initiating x402 payment flow...")

    result = client.pay(args.url, config, method=args.method)

    if args.json_output:
        output = {
            "success": result.success,
            "status_code": result.status_code,
            "response": result.response_body,
        }
        if result.error:
            output["error"] = result.error
        if args.verbose and result.payment_header_sent:
            output["payment_header"] = result.payment_header_sent
        print(json.dumps(output, indent=2))
    else:
        if result.success:
            print(f"✅ Payment successful (HTTP {result.status_code})")
        else:
            print(f"❌ Payment failed (HTTP {result.status_code})")
            if result.error:
                print(f"   Error: {result.error}")

        if args.verbose:
            if result.payment_header_sent:
                print(f"\n📦 X-PAYMENT header sent:")
                print(f"   {result.payment_header_sent[:80]}...")
            print(f"\n📄 Response:")
            print(json.dumps(result.response_body, indent=2))
        else:
            if result.response_body:
                # Print a summary
                body = result.response_body
                if isinstance(body, dict):
                    if "results" in body:
                        count = len(body["results"])
                        print(f"   Results: {count} service(s) found")
                    elif "error" in body or "detail" in body:
                        msg = body.get("error") or body.get("detail")
                        print(f"   Message: {msg}")
                    else:
                        keys = list(body.keys())[:5]
                        print(f"   Keys: {keys}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
