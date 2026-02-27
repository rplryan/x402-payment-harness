# x402 Payment Harness

> **EOA-based test harness for x402 micropayments.** Sign and send EIP-712 `TransferWithAuthorization` payments from a local private key — no CDP dependencies, no wallet API, no cloud signing.

[![PyPI](https://img.shields.io/pypi/v/x402-payment-harness)](https://pypi.org/project/x402-payment-harness/)
[![Python](https://img.shields.io/pypi/pyversions/x402-payment-harness)](https://pypi.org/project/x402-payment-harness/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![x402](https://img.shields.io/badge/protocol-x402-blue)](https://x402.org)

---

## What is this?

[x402](https://x402.org) is an HTTP-native micropayment protocol built by Coinbase. It uses HTTP 402 responses to gate API access behind USDC payments on Base mainnet.

The standard x402 payment flow requires an **EIP-712 `TransferWithAuthorization` signature** — but most tutorials assume you\'re using the Coinbase CDP API for signing. If you want to test x402 payments from a simple EOA wallet (e.g. a fresh test key, a Hardhat account, or a script), there\'s no clean tool for it.

**This harness fills that gap.**

---

## Proven on Base mainnet

This harness was used to execute the first known end-to-end x402 payment test from a Python script:

| Field | Value |
|---|---|
| **TX Hash** | [`0xb0ef774a7a26cdb370c305a625b2cf1bd6d7bb98f2ca16119d953bdcebc7e860`](https://basescan.org/tx/0xb0ef774a7a26cdb370c305a625b2cf1bd6d7bb98f2ca16119d953bdcebc7e860) |
| **Network** | Base mainnet (`eip155:8453`) |
| **Amount** | 0.005000 USDC |
| **Block** | 42707833 ✅ |
| **Gas** | 62,147 units / ~$0.002 |

---

## Install

```bash
pip install x402-payment-harness
```

---

## Quick start

### CLI

```bash
# Pay and call an x402-protected URL
x402-pay \
  --key 0xYOUR_PRIVATE_KEY \
  --to 0xRECIPIENT_ADDRESS \
  --amount 0.005 \
  https://x402-discovery-api.onrender.com/discover?query=search

# Output:
# ✅ Status: 200
#    TX Hash:   0xabc123...
#    Explorer:  https://basescan.org/tx/0xabc123...
```

```bash
# Use env var for private key (recommended)
export X402_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
x402-pay --to 0xRECIPIENT --amount 0.005 https://api.example.com/resource
```

```bash
# Generate only the X-PAYMENT header (no HTTP call)
x402-pay --sign-only --key 0xYOUR_KEY --to 0xRECIPIENT --amount 0.005
# X-PAYMENT: eyJ4NDAyVmVyc2lvbiI6MSwic2NoZW1lIjoiZXhhY3QiLC...
```

```bash
# JSON output for scripting
x402-pay --json --key 0xYOUR_KEY --to 0xRECIPIENT --amount 0.005 https://api.example.com/
# { "success": true, "status_code": 200, "tx_hash": "0x...", ... }
```

### Python library

```python
from x402_harness import X402Client, PaymentConfig

config = PaymentConfig(
    private_key="0xYOUR_PRIVATE_KEY",
    pay_to="0xRECIPIENT_ADDRESS",
    amount_usdc=0.005,
    network="eip155:8453",  # Base mainnet
)

client = X402Client()
result = client.get("https://api.example.com/resource", config)

if result.success:
    print(f"Payment confirmed! TX: {result.tx_hash}")
else:
    print(f"Failed: {result.error}")
```

### Sign only (no HTTP)

```python
from x402_harness import sign_payment, PaymentConfig

config = PaymentConfig(
    private_key="0xYOUR_PRIVATE_KEY",
    pay_to="0xRECIPIENT_ADDRESS",
    amount_usdc=0.005,
)

header_value = sign_payment(config)  # base64-encoded JSON
# Use as: headers={"X-PAYMENT": header_value}
```

---

## How x402 works

```
Client                          Server
  |                               |
  |-- GET /resource ------------> |
  |                               |
  |<-- 402 Payment Required ------|
  |    { "accepts": [{            |
  |        "scheme": "exact",     |
  |        "network": "eip155:8453",|
  |        "payTo": "0x...",      |
  |        "amount": "5000"       |
  |      }] }                     |
  |                               |
  | [sign EIP-712 locally]        |
  |                               |
  |-- GET /resource ------------> |
  |   X-PAYMENT: base64(...)      |
  |                               |
  |<-- 200 OK --------------------|  
  |   X-PAYMENT-RESPONSE: ...     |
  |   { ...resource data... }     |
```

This harness implements the client side: signs the EIP-712 `TransferWithAuthorization` payload and attaches it as the `X-PAYMENT` header on the retry.

---

## API reference

### `PaymentConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `private_key` | `str` | required | 0x-prefixed hex private key |
| `pay_to` | `str` | required | Recipient address |
| `amount_usdc` | `float` | required | Amount in USDC (e.g. `0.005`) |
| `network` | `str` | `"eip155:8453"` | Base mainnet |
| `usdc_contract` | `str` | Base USDC | USDC contract address |
| `valid_for_seconds` | `int` | `300` | Authorization validity window |
| `scheme` | `str` | `"exact"` | Payment scheme |

### `X402Client.get(url, config, params=None)`

Makes a GET request with automatic x402 payment. Returns `PaymentResult`.

### `sign_payment(config)` → `str`

Signs payment without making any HTTP requests. Returns base64-encoded `X-PAYMENT` header value.

### `PaymentResult`

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | True if server returned 200 |
| `status_code` | `int` | HTTP status code |
| `tx_hash` | `str\|None` | On-chain transaction hash |
| `receipt` | `dict\|None` | Decoded `X-PAYMENT-RESPONSE` |
| `response_body` | `dict\|None` | Response JSON body |
| `error` | `str\|None` | Error message if failed |

---

## Why no CDP dependency?

Coinbase CDP wallets require `CDP_WALLET_SECRET` — a base64-encoded private key that must be stored correctly and passed to the CDP signing API. For test environments:

- Secrets can be truncated in storage (common in `.env` files)
- CDP API requires network calls, adding latency and failure modes
- EOA wallets are simpler: sign locally with `eth_account`, submit directly

This harness uses pure `eth_account` signing. If you have a private key, you can sign.

---

## Compatibility

| Network | USDC Contract | Chain ID |
|---|---|---|
| Base mainnet | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 8453 |
| Base Sepolia | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | 84532 |

For Base Sepolia:
```python
config = PaymentConfig(
    private_key="0xYOUR_KEY",
    pay_to="0xRECIPIENT",
    amount_usdc=0.001,
    network="eip155:84532",
    usdc_contract="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
)
```

---

## Related projects

- [x402 Service Discovery API](https://x402-discovery-api.onrender.com) — find x402-enabled services
- [x402 Discovery MCP](https://github.com/rplryan/x402-discovery-mcp) — MCP server for AI agent discovery
- [x402 RouteNet](https://x402-routenet.onrender.com) — smart routing for x402 payments
- [x402.org](https://x402.org) — protocol specification

---

## License

MIT
