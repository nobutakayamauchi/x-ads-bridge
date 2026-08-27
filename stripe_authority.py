from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class StripeAuthorityError(ValueError):
    pass


@dataclass(frozen=True)
class StripeAuthorityContract:
    product_metadata_value: str
    purchase_payment_link: str
    purchase_amount_jpy: int
    purchase_purpose: str = "PUBLIC_SALES_LP"
    consultation_payment_link: str | None = None
    consultation_purpose: str = "PUBLIC_SALES_INQUIRY"
    currency: str = "jpy"
    client_reference_prefix: str = "wab_"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StripeAuthorityContract":
        if not isinstance(value, dict):
            raise StripeAuthorityError("stripe authority contract must be an object")
        required = ("product_metadata_value", "purchase_payment_link", "purchase_amount_jpy")
        missing = [key for key in required if value.get(key) in (None, "")]
        if missing:
            raise StripeAuthorityError(
                f"stripe authority contract missing: {', '.join(missing)}"
            )
        amount = int(value["purchase_amount_jpy"])
        if amount <= 0:
            raise StripeAuthorityError("purchase_amount_jpy must be > 0")
        prefix = str(value.get("client_reference_prefix") or "wab_")
        if not prefix or len(prefix) > 24:
            raise StripeAuthorityError("client_reference_prefix is invalid")
        consultation_link = value.get("consultation_payment_link")
        return cls(
            product_metadata_value=str(value["product_metadata_value"]),
            purchase_payment_link=str(value["purchase_payment_link"]),
            purchase_amount_jpy=amount,
            purchase_purpose=str(value.get("purchase_purpose") or "PUBLIC_SALES_LP"),
            consultation_payment_link=(
                str(consultation_link) if consultation_link not in (None, "") else None
            ),
            consultation_purpose=str(
                value.get("consultation_purpose") or "PUBLIC_SALES_INQUIRY"
            ),
            currency=str(value.get("currency") or "jpy").lower(),
            client_reference_prefix=prefix,
        )


def _metadata(session: dict[str, Any]) -> dict[str, Any]:
    value = session.get("metadata")
    return value if isinstance(value, dict) else {}


def _safe_evidence(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(session.get("id") or ""),
        "created": int(session.get("created") or 0),
        "payment_intent": str(session.get("payment_intent") or ""),
        "payment_link": str(session.get("payment_link") or ""),
        "client_reference_id": str(session.get("client_reference_id") or ""),
        "amount_total": int(session.get("amount_total") or 0),
        "currency": str(session.get("currency") or "").lower(),
        "status": str(session.get("status") or ""),
        "payment_status": str(session.get("payment_status") or ""),
    }


def _audited_refs(join_keys: list[dict[str, Any]]) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for item in join_keys:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("client_reference_id") or "").strip()
        if not ref:
            continue
        raw_events = item.get("events")
        if not isinstance(raw_events, list):
            continue
        refs[ref] = {str(event) for event in raw_events if str(event)}
    return refs


def join_stripe_authority(
    contract_value: dict[str, Any],
    audited_join_keys: list[dict[str, Any]],
    checkout_sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    contract = StripeAuthorityContract.from_dict(contract_value)
    refs = _audited_refs(audited_join_keys)

    paid: list[dict[str, Any]] = []
    paid_unjoined: list[dict[str, Any]] = []
    consultations: list[dict[str, Any]] = []
    consultations_unjoined: list[dict[str, Any]] = []
    rejected_relevant: list[dict[str, Any]] = []
    seen_session_ids: set[str] = set()

    for session in checkout_sessions:
        if not isinstance(session, dict):
            continue
        session_id = str(session.get("id") or "").strip()
        if not session_id or session_id in seen_session_ids:
            continue
        seen_session_ids.add(session_id)

        metadata = _metadata(session)
        if str(metadata.get("product") or "") != contract.product_metadata_value:
            continue

        payment_link = str(session.get("payment_link") or "")
        purpose = str(metadata.get("purpose") or "")
        client_reference_id = str(session.get("client_reference_id") or "").strip()
        status = str(session.get("status") or "")
        payment_status = str(session.get("payment_status") or "")
        currency = str(session.get("currency") or "").lower()
        amount_total = int(session.get("amount_total") or 0)
        livemode = session.get("livemode") is True

        if payment_link == contract.purchase_payment_link:
            if purpose != contract.purchase_purpose:
                rejected_relevant.append(
                    {**_safe_evidence(session), "reason": "purchase purpose mismatch"}
                )
                continue
            if not (
                livemode
                and status == "complete"
                and payment_status == "paid"
                and currency == contract.currency
                and amount_total == contract.purchase_amount_jpy
            ):
                rejected_relevant.append(
                    {
                        **_safe_evidence(session),
                        "reason": "purchase session is not exact live paid offer",
                    }
                )
                continue

            evidence = _safe_evidence(session)
            if (
                client_reference_id.startswith(contract.client_reference_prefix)
                and "purchase_click" in refs.get(client_reference_id, set())
            ):
                paid.append(evidence)
            else:
                paid_unjoined.append(evidence)
            continue

        if (
            contract.consultation_payment_link
            and payment_link == contract.consultation_payment_link
        ):
            if purpose != contract.consultation_purpose:
                rejected_relevant.append(
                    {**_safe_evidence(session), "reason": "consultation purpose mismatch"}
                )
                continue
            if not (
                livemode
                and status == "complete"
                and currency == contract.currency
                and amount_total == 0
            ):
                rejected_relevant.append(
                    {
                        **_safe_evidence(session),
                        "reason": "consultation session is not exact live completion",
                    }
                )
                continue

            evidence = _safe_evidence(session)
            if (
                client_reference_id.startswith(contract.client_reference_prefix)
                and "consult_click" in refs.get(client_reference_id, set())
            ):
                consultations.append(evidence)
            else:
                consultations_unjoined.append(evidence)

    return {
        "ok": True,
        "stripe_paid_purchases": len(paid),
        "stripe_consultation_completions": len(consultations),
        "unjoined_paid_purchase_candidates": len(paid_unjoined),
        "unjoined_consultation_candidates": len(consultations_unjoined),
        "authoritative_paid_sessions": paid,
        "authoritative_consultation_sessions": consultations,
        "paid_unjoined_sessions": paid_unjoined,
        "consultation_unjoined_sessions": consultations_unjoined,
        "rejected_relevant_sessions": rejected_relevant,
        "audited_client_reference_count": len(refs),
        "invariant": (
            "Only an exact live Stripe offer completion joined by client_reference_id "
            "to an owner-excluded audited CTA session is authoritative."
        ),
    }
