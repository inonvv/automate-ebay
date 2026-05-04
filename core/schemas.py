import os
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator

Currency = Literal["USD", "ILS", "EUR", "GBP"]


class Money(BaseModel):
    """Cart-side amount + observed currency. No FX conversion is performed."""
    amount: float = Field(ge=0)
    currency: Currency


class SearchInput(BaseModel):
    """Validated inputs for a search-and-filter call."""
    query: str = Field(min_length=1)
    max_price: float = Field(gt=0)
    limit: int = Field(gt=0)
    currency: "Currency" = "USD"

    @field_validator("query")
    @classmethod
    def _strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query must not be blank")
        return v


class Credentials(BaseModel):
    """eBay sign-in credentials, sourced from env (.env -> EBAY_USER / EBAY_PASS)."""
    user: str = Field(min_length=1)
    password: SecretStr

    @field_validator("password")
    @classmethod
    def _password_not_blank(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("password must not be blank")
        return v

    @classmethod
    def from_env(cls) -> "Credentials":
        return cls(
            user=os.environ.get("EBAY_USER", ""),
            password=os.environ.get("EBAY_PASS", ""),
        )
