import hashlib
import hmac
from datetime import datetime
from typing import Mapping
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


SECURE_HASH_FIELDS = {"vnp_SecureHash", "vnp_SecureHashType"}
RESPONSE_FIELDS = {
    "vnp_Amount",
    "vnp_BankCode",
    "vnp_BankTranNo",
    "vnp_CardType",
    "vnp_OrderInfo",
    "vnp_PayDate",
    "vnp_ResponseCode",
    "vnp_TmnCode",
    "vnp_TransactionNo",
    "vnp_TransactionStatus",
    "vnp_TxnRef",
    "vnp_SecureHash",
    "vnp_SecureHashType",
}


class VNPaySigner:
    def __init__(self, hash_secret: str) -> None:
        self.hash_secret = hash_secret

    @staticmethod
    def canonical_query(parameters: Mapping[str, str | int | None]) -> str:
        filtered = [
            (key, str(value))
            for key, value in parameters.items()
            if key not in SECURE_HASH_FIELDS and value not in (None, "")
        ]
        return urlencode(sorted(filtered))

    def sign(self, parameters: Mapping[str, str | int | None]) -> str:
        payload = self.canonical_query(parameters).encode("utf-8")
        return hmac.new(self.hash_secret.encode("utf-8"), payload, hashlib.sha512).hexdigest()

    def validate(self, parameters: Mapping[str, str | int | None]) -> bool:
        supplied = str(parameters.get("vnp_SecureHash") or "")
        if not supplied:
            return False
        return hmac.compare_digest(self.sign(parameters), supplied.lower())

    def build_payment_url(self, payment_url: str, parameters: Mapping[str, str | int | None]) -> str:
        query = self.canonical_query(parameters)
        secure_hash = self.sign(parameters)
        separator = "&" if "?" in payment_url else "?"
        return f"{payment_url}{separator}{query}&vnp_SecureHash={secure_hash}"

    @staticmethod
    def expected_response(parameters: Mapping[str, str]) -> dict[str, str]:
        return {key: value for key, value in parameters.items() if key in RESPONSE_FIELDS}

    @staticmethod
    def parse_pay_date(value: str | None) -> datetime | None:
        if not value:
            return None
        parsed = datetime.strptime(value, "%Y%m%d%H%M%S")
        return parsed.replace(tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
