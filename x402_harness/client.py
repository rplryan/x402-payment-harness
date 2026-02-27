"""HTTP client for x402 payment flow.

Handles the two-step x402 protocol:
  1. Initial request → receives 402 with payment challenge
  2. Signs the challenge with EOA private key
  3. Retries with X-PAYMENT header → receives 200 (or error)
"""
import json
from typing import Any, Dict, Optional

import requests

from .models import PaymentConfig, PaymentResult
from .signer import sign_payment


class X402Client:
    """HTTP client that speaks x402 payment protocol."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "x402-payment-harness/1.0.0"})

    def pay(
        self,
        url: str,
        config: PaymentConfig,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
    ) -> PaymentResult:
        """
        Make an x402 payment to a URL.

        Automatically handles the 402 → sign → retry flow.

        Returns:
            PaymentResult with success status and response details
        """
        # Step 1: probe the endpoint
        try:
            resp = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            return PaymentResult(success=False, status_code=0, error=str(e))

        if resp.status_code != 402:
            # Already accessible or error
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text}
            return PaymentResult(
                success=resp.status_code < 400,
                status_code=resp.status_code,
                response_body=body,
            )

        # Step 2: parse the 402 challenge
        try:
            challenge = resp.json()
        except Exception:
            return PaymentResult(
                success=False,
                status_code=402,
                error=f"Could not parse 402 challenge: {resp.text[:500]}",
            )

        # Step 3: sign the payment
        try:
            payment_header = sign_payment(config, challenge)
        except Exception as e:
            return PaymentResult(
                success=False,
                status_code=402,
                error=f"Payment signing failed: {e}",
            )

        # Step 4: retry with payment header
        try:
            paid_resp = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers={"X-PAYMENT": payment_header},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            return PaymentResult(
                success=False,
                status_code=0,
                payment_header_sent=payment_header,
                error=str(e),
            )

        try:
            body = paid_resp.json()
        except Exception:
            body = {"raw": paid_resp.text}

        return PaymentResult(
            success=paid_resp.status_code < 400,
            status_code=paid_resp.status_code,
            response_body=body,
            payment_header_sent=payment_header,
        )
