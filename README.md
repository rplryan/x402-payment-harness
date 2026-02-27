# x402 Payment Harness

[![PyPI version](https://img.shields.io/pypi/v/x402-payment-harness.svg)](https://pypi.org/project/x402-payment-harness/)
[![PyPI downloads](https://img.shields.io/pypi/dm/x402-payment-harness.svg)](https://pypi.org/project/x402-payment-harness/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-4%20passing-brightgreen.svg)](https://github.com/rplryan/x402-payment-harness/tree/main/tests)
[![Network: Base](https://img.shields.io/badge/network-Base-0052FF.svg)](https://base.org)

```bash
pip install x402-payment-harness
```

**The missing developer tool for x402.** Test any x402-protected endpoint from your terminal or Python code — no Coinbase Developer Platform wallet required. Just a standard Ethereum private key.

```python
from x402_harness import X402Client

client = X402Client(private_key="0xYOUR_PRIVATE_KEY")
response = client.get("https://api.example.com/premium-data")
print(response.json())
```

The client handles the full `HTTP 402 → EIP-712 sign → X-PAYMENT header → 200 OK` flow automatically.

---

## Why This Exists

The [x402 protocol](https://x402.org) is the emerging standard for HTTP-native micropayments on Base — enabling AI agents, APIs, and services to charge per-request without subscriptions or API key billing.

**The problem:** The reference x402 implementation is built around Coinbase Developer Platform (CDP) managed wallets, which abstract away the signing logic — but require account creation, KYC-adjacent onboarding, and vendor lock-in. This is a real friction point for:

- 🔧 **Server builders** who want to test their x402 endpoint as a client would
- 🤖 **Agent developers** integrating x402 payments into autonomous workflows
- 🧪 **Protocol researchers** exploring x402 behavior across different servers
- 🏃 **Teams running CI/CD** who need deterministic, reproducible payment tests

**This library removes that barrier entirely.** Any standard Ethereum EOA private key works — MetaMask export, hardware wallet, generated test key. No CDP account, no onboarding, no dependency on Coinbase infrastructure.

This is the **only Python x402 client library with native EIP-712 `TransferWithAuthorization` signing**.

---

## Installation

```bash
pip install x402-payment-harness
```

Requires Python 3.8+. For development/testing:

```bash
git clone https://github.com/rplryan/x402-payment-harness
cd x402-payment-harness
pip install -e ".[dev]"
```

---

## Quick Start

### CLI — One Command Payments

```bash
# Pay and fetch in one command
x402-pay --url https://api.example.com/premium-data --key 0xYOUR_PRIVATE_KEY

# Inspect every step of the payment flow
x402-pay --url https://api.example.com/premium-data --key 0xYOUR_PRIVATE_KEY --verbose

# POST request with JSON body
x402-pay --url https://api.example.com/generate --key 0xYOUR_PRIVATE_KEY \
  --method POST --data '{"prompt": "Hello, world"}'
```

### Python Library

```python
from x402_harness import X402Client

# Initialize with any standard EOA private key
client = X402Client(
    private_key="0xYOUR_PRIVATE_KEY",
    network="base-mainnet"       # default; also supports "base-sepolia"
)

# GET request — handles full 402 → sign → retry flow automatically
response = client.get("https://api.example.com/premium-data")

if response.status_code == 200:
    print("Payment accepted:", response.json())

# POST with body
response = client.post(
    "https://api.example.com/generate",
    json={"prompt": "Analyze this market data"}
)

# Access payment details from the last transaction
print(client.last_payment)  # {amount, recipient, signature, nonce, ...}
```

---

## How It Works: The x402 Protocol Flow

When you call `client.get(url)`, the harness executes the complete x402 client protocol:

```
┌──────────┐    GET /premium-data       ┌──────────────────┐
│  Client  │ ──────────────────────────►│  x402 Server     │
│  (you)   │◄────────────────────────── │                  │
└──────────┘   402 + X-PAYMENT-REQUIRED  └──────────────────┘
      │         {amount, payTo, chainId,                ▲
      │          EIP-712 domain separator}              │
      │                                                 │
      ▼ Sign TransferWithAuthorization                  │
  EOA Private Key                                       │
  eth_account.sign_typed_data()                         │
      │                                                 │
      ▼                                                 │
┌──────────┐    GET /premium-data       ┌──────────────────┐
│  Client  │ ──────────────────────────►│  Verify EIP-712  │
│  (you)   │   + X-PAYMENT: <base64>   ►│  signature ✓     │
└──────────┘◄────────────────────────── │  Return 200 OK   │
              200 OK + response body    └──────────────────┘
```

**Steps executed automatically:**
1. Initial HTTP request to target endpoint
2. Receive `402 Payment Required` with `X-PAYMENT-REQUIRED` header
3. Parse EIP-712 domain separator and `TransferWithAuthorization` message struct
4. Sign the struct using your EOA private key via `eth_account`
5. Base64-encode the signed payload and attach as `X-PAYMENT` header
6. Retry the request — server verifies signature and responds `200 OK`

> **On settlement:** This harness implements the complete x402 **client-side** protocol — producing valid, spec-compliant `TransferWithAuthorization` EIP-712 signatures. Server-side on-chain USDC settlement via `receiveWithAuthorization` is the facilitator's responsibility. The harness is the correct tool for testing and validating the client flow against any x402-compliant server.

---

## Use Cases

### 🔨 Server Development & Testing
Building an x402-protected API? Use this harness as your client to test every payment edge case — invalid signatures, expired nonces, wrong amounts — without building a custom test client.

```python
import pytest
from x402_harness import X402Client

def test_my_api_accepts_valid_payment():
    client = X402Client(private_key=TEST_KEY)
    response = client.get("http://localhost:8000/protected")
    assert response.status_code == 200
```

### 🤖 AI Agent Integration
Autonomous agents can make x402 payments without managed wallet infrastructure:

```python
from x402_harness import X402Client

# Agent pays for data, processes result, continues workflow
client = X402Client(private_key=os.environ["AGENT_WALLET_KEY"])
market_data = client.get("https://x402-api.example.com/prices").json()
agent.process(market_data)
```

### 🔄 CI/CD Integration
Add x402 protocol conformance tests to your pipeline:

```yaml
# .github/workflows/test.yml
- name: Test x402 payment flow
  run: x402-pay --url ${{ env.TEST_SERVER_URL }} --key ${{ secrets.TEST_WALLET_KEY }}
```

### 🔍 Protocol Exploration
Explore any x402 endpoint on the network:

```bash
# Discover services via x402 Discovery API, then test them
x402-pay --url https://x402-discovery-api.onrender.com/discover --key 0xYOUR_KEY --verbose
```

---

## Features

| Feature | Description |
|---|---|
| **Full protocol flow** | HTTP 402 challenge → EIP-712 sign → `X-PAYMENT` header, end-to-end |
| **EOA support** | Works with any standard Ethereum private key — no CDP wallet required |
| **ERC-3009 signing** | Native `TransferWithAuthorization` EIP-712 typed data signing |
| **CLI tool** | `x402-pay --url <endpoint>` for fast terminal testing |
| **Python library** | `X402Client` with `get()` and `post()` methods |
| **Base mainnet proven** | Confirmed working against live Base USDC x402 endpoints |
| **Test suite** | 4 passing automated tests covering core protocol flows |
| **Zero vendor lock-in** | Pure open source, no CDP dependency, no API keys needed |

---

## Testing

```bash
pytest tests/ -v
```

All 4 tests pass without any API keys or live network connections — the test suite uses fixtures to mock the 402 challenge/response cycle. This makes it suitable for CI/CD without wallet credentials.

---

## Part of the x402 Infrastructure Suite

This library is part of a suite of open-source tools built to make x402 practical:

| Tool | What It Does | Status |
|---|---|---|
| **x402 Payment Harness** | EOA-based client library and CLI for testing x402 | **This repo** |
| **[x402 Discovery API](https://github.com/rplryan/x402-discovery-api)** | Searchable registry of 251+ live x402-enabled services with health signals | [Live](https://x402-discovery-api.onrender.com) |
| **[x402 Discovery MCP](https://github.com/rplryan/x402-discovery-mcp)** | MCP server exposing Discovery API to Claude, Cursor, Windsurf | [Published](https://registry.modelcontextprotocol.io) |
| **[x402 RouteNet](https://github.com/rplryan/x402-routenet)** | Intelligent routing across x402 services with health-aware fallback | [Live](https://x402-routenet.onrender.com) |

Together these tools cover the three layers every developer needs: **discover** x402 services, **route** to the best one, and **test** the payment flow end-to-end.

---

## Links

- **PyPI:** https://pypi.org/project/x402-payment-harness/
- **x402 Protocol:** https://x402.org
- **x402 Discovery API:** https://x402-discovery-api.onrender.com
- **Base Network:** https://base.org

---

## License

MIT © 2024 rplryan
