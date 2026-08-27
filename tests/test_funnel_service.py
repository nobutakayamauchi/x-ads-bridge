from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import funnel_service


class FunnelTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "funnel.sqlite3"
        self.patch_db = patch.object(funnel_service, "DB_PATH", self.db_path)
        self.patch_secret = patch.object(funnel_service, "HASH_SECRET", "test-hash-secret")
        self.patch_audit = patch.object(funnel_service, "AUDIT_TOKEN", "test-audit-token")
        self.patch_db.start()
        self.patch_secret.start()
        self.patch_audit.start()
        self.addCleanup(self.patch_db.stop)
        self.addCleanup(self.patch_secret.stop)
        self.addCleanup(self.patch_audit.stop)

    def _event(self, *, event_id: str, event: str, device_id: str, session_id: str = "session-12345678"):
        return funnel_service.FunnelEvent(
            event_id=event_id,
            event=event,
            product="webai-bridge",
            device_id=device_id,
            session_id=session_id,
            path="/sales-catalog/products/webai-bridge/sales.html",
            source="x.com",
            twclid="",
            utm_source="x",
            utm_medium="paid",
            utm_campaign="wab-test",
            utm_content="",
            campaign_id="p5vot",
            line_item_id="xhwda",
        )

    def test_duplicate_event_id_is_idempotent(self):
        event = self._event(
            event_id="event-00000001",
            event="lp_view",
            device_id="device-customer-0001",
        )
        self.assertTrue(funnel_service._insert_event(event))
        self.assertFalse(funnel_service._insert_event(event))

        summary = funnel_service._query_summary("webai-bridge", 0, 4_000_000_000)
        self.assertEqual(summary["events"]["lp_view"]["total_events"], 1)
        self.assertEqual(summary["events"]["lp_view"]["audited_events"], 1)

    def test_owner_exclusion_keeps_raw_but_removes_audited_counts(self):
        owner_device = "device-owner-00000001"
        customer_device = "device-customer-0001"

        funnel_service._insert_event(
            self._event(event_id="event-00000001", event="lp_view", device_id=owner_device)
        )
        funnel_service._insert_event(
            self._event(event_id="event-00000002", event="lp_view", device_id=customer_device)
        )
        funnel_service._insert_event(
            self._event(event_id="event-00000003", event="purchase_click", device_id=owner_device)
        )

        owner_hash = funnel_service._device_hash(owner_device)
        with funnel_service._db() as conn:
            conn.execute(
                "INSERT INTO exclusions(device_hash, label, created_at) VALUES (?, ?, ?)",
                (owner_hash, "owner-iphone", 1),
            )

        summary = funnel_service._query_summary("webai-bridge", 0, 4_000_000_000)

        lp = summary["events"]["lp_view"]
        self.assertEqual(lp["total_devices"], 2)
        self.assertEqual(lp["audited_devices"], 1)

        purchase = summary["events"]["purchase_click"]
        self.assertEqual(purchase["total_devices"], 1)
        self.assertEqual(purchase["audited_devices"], 0)

        self.assertEqual(summary["derived"]["lp_unique"], 1)
        self.assertEqual(summary["derived"]["purchase_click_unique"], 0)

    def test_join_keys_include_customer_cta_but_never_owner_cta(self):
        owner_device = "device-owner-00000001"
        customer_device = "device-customer-0001"
        owner_session = "owner-session-12345678"
        customer_session = "customer-session-12345678"

        funnel_service._insert_event(
            self._event(
                event_id="event-00000001",
                event="purchase_click",
                device_id=owner_device,
                session_id=owner_session,
            )
        )
        funnel_service._insert_event(
            self._event(
                event_id="event-00000002",
                event="consult_click",
                device_id=customer_device,
                session_id=customer_session,
            )
        )
        funnel_service._insert_event(
            self._event(
                event_id="event-00000003",
                event="purchase_click",
                device_id=customer_device,
                session_id=customer_session,
            )
        )

        owner_hash = funnel_service._device_hash(owner_device)
        with funnel_service._db() as conn:
            conn.execute(
                "INSERT INTO exclusions(device_hash, label, created_at) VALUES (?, ?, ?)",
                (owner_hash, "owner-iphone", 1),
            )

        result = funnel_service._query_join_keys("webai-bridge", 0, 4_000_000_000)
        self.assertEqual(result["join_key_count"], 1)
        self.assertTrue(result["owner_excluded"])
        self.assertEqual(
            result["join_keys"][0]["client_reference_id"],
            f"wab_{customer_session}",
        )
        self.assertEqual(
            result["join_keys"][0]["events"],
            ["consult_click", "purchase_click"],
        )
        self.assertNotIn(owner_session, str(result))
        self.assertNotIn("device_hash", str(result))

    def test_extended_tracker_events_are_accepted(self):
        for index, event_name in enumerate(
            [
                "consult_cta_view",
                "purchase_cta_view",
                "consult_checkout_start",
                "purchase_checkout_start",
                "consult_checkout_return",
                "purchase_checkout_return",
                "scroll_25",
                "scroll_50",
                "scroll_75",
                "scroll_90",
            ],
            start=1,
        ):
            inserted = funnel_service._insert_event(
                self._event(
                    event_id=f"extended-event-{index:04d}",
                    event=event_name,
                    device_id="device-customer-0001",
                )
            )
            self.assertTrue(inserted)

    def test_raw_device_id_is_not_stored_in_events(self):
        raw_device = "device-sensitive-local-id-12345"
        funnel_service._insert_event(
            self._event(event_id="event-00000001", event="lp_view", device_id=raw_device)
        )

        conn = sqlite3.connect(self.db_path)
        try:
            stored = conn.execute("SELECT device_hash FROM events LIMIT 1").fetchone()[0]
            dump = "\n".join(conn.iterdump())
        finally:
            conn.close()

        self.assertNotEqual(stored, raw_device)
        self.assertNotIn(raw_device, dump)
        self.assertEqual(len(stored), 64)

    def test_purchase_complete_client_is_not_declared_authoritative(self):
        event = self._event(
            event_id="event-00000001",
            event="purchase_complete_client",
            device_id="device-customer-0001",
        )
        funnel_service._insert_event(event)
        summary = funnel_service._query_summary("webai-bridge", 0, 4_000_000_000)
        self.assertIn("Stripe", summary["authority_note"])
        self.assertEqual(summary["derived"]["purchase_click_unique"], 0)


if __name__ == "__main__":
    unittest.main()
