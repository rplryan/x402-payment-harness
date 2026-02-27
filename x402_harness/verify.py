"""Local signature verification — mirrors server-side logic for testing."""
import base64
import json

from eth_account import Account
from eth_account.messages import encode_typed_data

USC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_CHAIN_ID = 8453


def verify_payment_header(header_value: str) -> dict:
    """Verify an X-PAYMENT header locally."""
    try:
        payload = json.loads(base64.b64decode(header_value).decode())
    except Exception as e:
        return {"valid": False, "error": f"Could not decode header: {e}"}

    auth = payload.get("payload", {}).get("authorization", {})
    sig = payload.get("payload", {}).get("signature", "")

    nonce_raw = auth.get("nonce", "")
    if isinstance(nonce_raw, str) and nonce_raw.startswith("0x"):
        nonce = bytes.fromhex(nonce_raw[2:])
    else:
        nonce = bytes.fromhex(nonce_raw) if nonce_raw else b"\x00" * 32

    typed_data = {
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
            "verifyingContract": USC_CONTRACT,
        },
        "primaryType": "TransferWithAuthorization",
        "message": {
            "from": auth.get("from", ""),
            "to": auth.get("to", ""),
            "value": int(auth.get("value", 0)),
            "validAfter": int(auth.get("validAfter", 0)),
            "validBefore": int(auth.get("validBefore", 0)),
            "nonce": nonce,
        },
    }

    try:
        msg = encode_typed_data(full_message=typed_data)
        recovered = Account.recover_message(msg, signature=bytes.fromhex(sig.replace("0x", "")))
        valid = recovered.lower() == auth.get("from", "").lower()
        amount_usd = int(auth.get("value", 0)) / 1_000_000
        return {
            "valid": valid,
            "signer": recovered,
            "claimed_from": auth.get("from", ""),
            "amount_usd": amount_usd,
            "to": auth.get("to", ""),
            "error": None if valid else f"Signer mismatch",
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
