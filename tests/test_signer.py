"""Tests for x402 EIP-712 signer."""
import base64
import json

import pytest
from eth_account import Account

from x402_harness import PaymentConfig, sign_payment
from x402_harness.verify import verify_payment_header


TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
TEST_RECIPIENT = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"


def test_sign_payment_no_challenge():
    """Sign a payment without a server challenge."""
    config = PaymentConfig(
        private_key=TEST_PRIVATE_KEY,
        to=TEST_RECIPIENT,
        amount_usd=0.005,
    )
    header = sign_payment(config)
    assert isinstance(header, str)
    # Decode and verify structure
    payload = json.loads(base64.b64decode(header).decode())
    assert payload["x402Version"] == 1
    assert payload["scheme"] == "exact"
    assert "signature" in payload["payload"]
    auth = payload["payload"]["authorization"]
    assert auth["to"] == TEST_RECIPIENT
    assert int(auth["value"]) == 5000  # $0.005 = 5000 USDC units


def test_sign_payment_with_challenge():
    """Sign a payment using a server-style 402 challenge."""
    challenge = {
        "accepts": [{
            "network": "eip155:8453",
            "address": TEST_RECIPIENT,
            "amount": "5000",
            "scheme": "exact",
        }]
    }
    config = PaymentConfig(private_key=TEST_PRIVATE_KEY)
    header = sign_payment(config, challenge)
    payload = json.loads(base64.b64decode(header).decode())
    assert payload["payload"]["authorization"]["to"] == TEST_RECIPIENT


def test_signature_is_recoverable():
    """Verify that the signature can be locally verified."""
    config = PaymentConfig(
        private_key=TEST_PRIVATE_KEY,
        to=TEST_RECIPIENT,
        amount_usd=0.005,
    )
    header = sign_payment(config)
    result = verify_payment_header(header)
    assert result["valid"] is True
    expected_sender = Account.from_key(TEST_PRIVATE_KEY).address
    assert result["signer"].lower() == expected_sender.lower()
    assert abs(result["amount_usd"] - 0.005) < 0.0001


def test_payment_config_sender_address():
    """Sender address is derived correctly from private key."""
    config = PaymentConfig(private_key=TEST_PRIVATE_KEY, to=TEST_RECIPIENT)
    expected = Account.from_key(TEST_PRIVATE_KEY).address
    assert config.sender_address == expected
