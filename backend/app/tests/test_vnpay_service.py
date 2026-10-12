from datetime import timedelta

from app.services.vnpay_service import VNPaySigner


def test_vnpay_canonicalization_and_hmac_vector() -> None:
    signer = VNPaySigner("unit-test-secret")
    parameters = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": "TESTVNP1",
        "vnp_Amount": 72000000,
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": "260930ABC123",
        "vnp_OrderInfo": "YPGym membership 260930ABC123",
        "vnp_ReturnUrl": "https://example.test/api/v1/payments/vnpay/return",
        "vnp_SecureHashType": "HmacSHA512",
        "ignored_empty": "",
    }
    expected_query = (
        "vnp_Amount=72000000&vnp_Command=pay&vnp_CurrCode=VND&"
        "vnp_OrderInfo=YPGym+membership+260930ABC123&"
        "vnp_ReturnUrl=https%3A%2F%2Fexample.test%2Fapi%2Fv1%2Fpayments%2Fvnpay%2Freturn&"
        "vnp_TmnCode=TESTVNP1&vnp_TxnRef=260930ABC123&vnp_Version=2.1.0"
    )
    expected_hash = "46711c0afe482f8d0bf196f1fd377a89a9b782d45e31c3047329102f1a8f8b6814471fafea8952ee40228f31b5d5f15b325bdbdfe9cbad5fab226aec88bd63a5"
    assert signer.canonical_query(parameters) == expected_query
    assert signer.sign(parameters) == expected_hash
    assert signer.validate({**parameters, "vnp_SecureHash": expected_hash})
    assert not signer.validate({**parameters, "vnp_SecureHash": "0" * 128})


def test_vnpay_timestamp_is_parsed_in_gmt_plus_seven() -> None:
    parsed = VNPaySigner.parse_pay_date("20260930153045")
    assert parsed is not None
    assert parsed.utcoffset() == timedelta(hours=7)
