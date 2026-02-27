"""EIP-712 TransferWithAuthorization signer for x402 payments.

No CDP dependency — pure eth_account signing.
Implements USDC's EIP-3009 TransferWithAuthorization for Base mainnet.
"""
import base64
import json
import secrets
import time
from typing import Any, Dict

from eth_account import Account
from eth_account.messages import encode_typed_data

from .models import PaymentConfig

# USDC contract on Base mainnet
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6
BASE_CHAIN_ID = 8453


def build_eip712_message(
    from_addr: str,
    to_addr: str,
    amount_raw: int,
    nonce: bytes,
    valid_after: int,
    valid_before: int,
) -> Dict[str, Any]:
    """Build the EIP-712 typed data for TransferWithAuthorization."""
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": BASE_CHAIN_ID,
            "verifyingContract": USDC_CONTRACT,
        },
        "primaryType": "TransferWithAuthorization",
        "message": {
            "from": from_addr,
            "to": to_addr,
            "value": amount_raw,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce,
        },
    }


def sign_payment(config: PaymentConfig, challenge: Dict[str, Any] = None) -> str:
    """
    Sign an x402 payment challenge and return the X-PAYMENT header value.

    Args:
        config: PaymentConfig with private key and optional overrides
        challenge: 402 response body from the server (parsed JSON).
                   If None, uses config values directly.

    Returns:
        Base64-encoded JSON string for the X-PAYMENT header.
    """
    key = config.private_key if config.private_key.startswith("0x") else f"0x{config.private_key}"
    account = Account.from_key(key)
    from_addr = account.address

    # Extract payment params from challenge or config
    if challenge:
        # Find matching accept entry (prefer exact scheme on eip155:8453)
        accepts = challenge.get("accepts", challenge.get("accept", []))
        entry = None
        for a in accepts:
            if a.get("network", a.get("networkId", "")) in (config.network, "eip155:8453"):
                entry = a
                break
        if not entry and accepts:
            entry = accepts[0]
        if not entry:
            raise ValueError("No matching payment option in challenge")

        to_addr = config.to or entry.get("address", entry.get("payTo", ""))
        amount_raw = int(entry.get("amount", entry.get("maxAmountRequired", 5000)))
        # In USDC units: 5000 = $0.005, 1000000 = $1.00
        if config.amount_usd:
            amount_raw = int(config.amount_usd * (10 ** USDC_DECIMALS))
    else:
        if not config.to:
            raise ValueError("PaymentConfig.to is required when no challenge is provided")
        to_addr = config.to
        amount_raw = int((config.amount_usd or 0.005) * (10 ** USDC_DECIMALS))

    # Timing
    now = int(time.time())
    valid_after = now - 60       # 1 min in past (clock skew tolerance)
    valid_before = now + 3600    # 1 hour validity

    # Random nonce (bytes32)
    nonce = secrets.token_bytes(32)

    # Build and sign EIP-712 message
    typed_data = build_eip712_message(
        from_addr=from_addr,
        to_addr=to_addr,
        amount_raw=amount_raw,
        nonce=nonce,
        valid_after=valid_after,
        valid_before=valid_before,
    )
    msg = encode_typed_data(full_message=typed_data)
    signed = account.sign_message(msg)

    # Compose x402 payment payload (x402 version 1)
    payload = {
        "x402Version": 1,
        "scheme": "exact",
        "network": "eip155:8453",
        "payload": {
            "signature": signed.signature.hex(),
            "authorization": {
                "from": from_addr,
                "to": to_addr,
                "value": str(amount_raw),
                "validAfter": str(valid_after),
                "validBefore": str(valid_before),
                "nonce": "0x" + nonce.hex(),
            },
        },
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()
