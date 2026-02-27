# x402 Payment Harness

> EOA-based Python library and CLI for testing x402 payments. No CDP wallet needed.

[![PyPI version](https://img.shields.io/pypi/v/x402-payment-harness.svg)](https://pypi.org/project/x402-payment-harness/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Network: Base](https://img.shields.io/badge/network-Base-0052FF.svg)](https://base.org)

```bash
pip install x402-payment-harness
```

The missing developer tool for x402. Test any x402-protected endpoint from your terminal or Python code using a standard EOA private key — no Coinbase Developer Platform wallet, no account creation, no friction.

---

## Quick Start

```python
from x402_harness import X402Client

client = X402Client(private_key="0xYOUR_PRIVATE_KEY")
response = client.get("https://api.example.com/premium-data")
print(response.json())
```

That's it. The client handles the full HTTP 402 challenge → EIP-712 sign → `X-PAYMENT` header flow automatically.

---

## CLI

```bash
# Pay and fetch in one command
x402-pay --url https://api.example.com/premium-data --key 0xYOUR_PRIVATE_KEY

# With verbose output to inspect every step of the payment flow
x402-pay --url https://api.example.com/premium-data --key 0xYOUR_PRIVATE_KEY --verbose
```

---

## Why This Exists

The [x402 protocol](https://x402.org) enables HTTP-native micropayments by extending HTTP 402. When a server requires payment, it responds with a `402 Payment Required` status and a `X-PAYMENT-REQUIRED` header containing EIP-712 payment requirements. The client must construct a [`TransferWithAuthorization`](https://eips.ethereum.org/EIPS/eip-3009) signature and attach it as an `X-PAYMENT` header on a follow-up request.

**The problem:** The reference x402 implementation is built around Coinbase Developer Platform (CDP) wallets, which abstract away the signing logic — but require account creation and onboarding. This is a real barrier when you just want to test a server you've built or explore the protocol.

**This library solves it:** Any standard Ethereum EOA private key works. If you have a funded Base wallet — from MetaMask, a hardware wallet, or a generated test key — you can test any x402 endpoint in minutes without touching CDP.

---

## Features

| Feature | Description |
|---|---|
| Full protocol flow | HTTP 402 challenge → EIP-712 sign → `X-PAYMENT` header, end-to-end |
| EOA support | Works with any standard private key — no CDP wallet required |
| CLI tool | `x402-pay --url <endpoint>` for fast terminal testing |
| Python library | `X402Client` with `get()` and `post()` methods |
| Base mainnet tested | Confirmed working against live Base USDC endpoints |
| Test suite | 4 passing automated tests covering core protocol flows |

---

## Installation

```bash
pip install x402-payment-harness
```

Requires Python 3.8+ and a Base wallet funded with USDC.

---

## Protocol Flow

When you call `client.get(url)`, the harness executes the full x402 client protocol:

1. Makes the initial HTTP request to the target endpoint
2. Receives `402 Payment Required` with a `X-PAYMENT-REQUIRED` header containing payment details
3. Parses the EIP-712 domain separator and `TransferWithAuthorization` message struct
4. Signs the struct using your EOA private key via `eth_account`
5. Base64-encodes the signature and attaches it as an `X-PAYMENT` header
6. Retries the request — the server verifies the signature and responds `200 OK`

**Note on settlement:** This harness implements the full x402 **client-side** protocol. Server-side on-chain USDC settlement via `receiveWithAuthorization` is the facilitator's responsibility. Test servers typically return `200` on valid signature verification alone, which is the correct behavior for development environments. The harness is the right tool for testing and validating the client flow against any x402-compliant server.

---

## Full Example

```python
from x402_harness import X402Client

# Initialize with your EOA private key
client = X402Client(
    private_key="0xYOUR_PRIVATE_KEY",
    network="base-mainnet"       # default; also supports "base-sepolia"
)

# GET request to an x402-protected endpoint
response = client.get("https://api.example.com/premium-data")

if response.status_code == 200:
    print("Payment accepted:", response.json())
else:
    print("Unexpected status:", response.status_code)

# POST also supported
response = client.post(
    "https://api.example.com/generate",
    json={"prompt": "Hello, world"}
)
```

---

## Running the Tests

```bash
git clone https://github.com/rplryan/x402-payment-harness
cd x402-payment-harness
pip install -e ".[dev]"
pytest tests/ -v
```

All 4 tests pass without any API keys or live network connections — the test suite uses fixtures to mock the 402 challenge/response cycle.

---

## Links

- **PyPI:** https://pypi.org/project/x402-payment-harness/
- **GitHub:** https://github.com/rplryan/x402-payment-harness
- **x402 Protocol:** https://x402.org

---

## Part of the x402 Infrastructure Suite

This library is part of a set of tools built to make x402 practical for everyday developers:

| Tool | What It Does | Status |
|---|---|---|
| **x402 Payment Harness** | EOA-based client library and CLI for testing x402 | This repo |
| **x402 Discovery API** | Searchable registry of live x402-enabled services | [Live on Render](https://github.com/rplryan/x402-discovery-api) |
| **x402 RouteNet** | Intelligent routing with multi-provider fallback | [Live on Render](https://github.com/rplryan/x402-routenet) |

Together, these tools cover the three layers a developer needs: **find** a service (Discovery API), **pay** it reliably (RouteNet), and **test** the flow end-to-end (this library).

---

## License

MIT © 2024 rplryan
