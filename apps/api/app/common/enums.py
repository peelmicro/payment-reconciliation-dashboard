import enum


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"
    partially_refunded = "partially_refunded"
    disputed = "disputed"


class PaymentMethod(str, enum.Enum):
    card = "card"
    paypal_wallet = "paypal_wallet"
    bank_transfer = "bank_transfer"
    direct_debit = "direct_debit"


class StripePaymentType(str, enum.Enum):
    payment_intent = "payment_intent"
    charge = "charge"
    refund = "refund"
    dispute = "dispute"


class PaypalPaymentType(str, enum.Enum):
    order = "order"
    capture = "capture"
    authorization = "authorization"
    refund = "refund"
    dispute = "dispute"


class BankTransferType(str, enum.Enum):
    sepa_credit = "sepa_credit"
    sepa_direct_debit = "sepa_direct_debit"
    swift = "swift"
    domestic = "domestic"


class ReconciliationStatus(str, enum.Enum):
    matched = "matched"
    matched_with_fee = "matched_with_fee"
    amount_mismatch = "amount_mismatch"
    missing_internal = "missing_internal"
    missing_external = "missing_external"
    duplicate = "duplicate"
    disputed = "disputed"
