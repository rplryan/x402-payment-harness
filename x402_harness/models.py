"""Data models for x402 payment harness."""
from dataclasses import dataclass, field
from typing import Optional
from eth_account import Account


@dataclass
class PaymentConfig:
    """Configuration for an x402 payment."""
    private_key: str          # EOA private key (hex, with or without 0x prefix)
    to: Optional[str] = None  # Recipient address (overrides server challenge)
    amount_usd: Optional[float] = None  # Amount in USD (overrides server challenge)
    network: str = "eip155:8453"        # Base mainnet

    @property
    def sender_address(self) -> str:
        """Derive sender address from private key."""
        key = self.private_key if self.private_key.startswith("0x") else f"0x{self.private_key}"
        return Account.from_key(key).address


@dataclass
class PaymentResult:
    """Result of an x402 payment attempt."""
    success: bool
    status_code: int
    response_body: dict = field(default_factory=dict)
    payment_header_sent: Optional[str] = None
    error: Optional[str] = None
