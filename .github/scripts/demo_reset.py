"""Keep the demo turf's diary clear.

Every booking a prospect makes on the landing page lands in the demo diary and
blocks that hour on one of the fields. Left alone the diary fills up and the
next turf owner is told everything is taken, which is exactly the impression
the demo must not give.

This cancels demo bookings older than MAX_AGE_MINUTES. A booking survives the
call that created it, so the owner can still ask for the same slot twice and
hear it refused — the moment that sells the agent — and a few minutes later the
slot is free again for the next owner.

It only ever touches record type `demo_booking`. The client's real diary
(`booking`) is never read or written.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://autosham-voice-ai-agent-production.up.railway.app/api/v1"
DEMO_RECORD_TYPE = "demo_booking"
MAX_AGE_MINUTES = 10


def call(method, path, body=None):
    request = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-API-Key": os.environ["AUTOSHAM_API_KEY"], "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or "{}")


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=MAX_AGE_MINUTES)
    records = call("GET", f"/records?record_type={DEMO_RECORD_TYPE}&status=booked&limit=100")["records"]

    cleared = kept = 0
    for record in records:
        created = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
        if created > cutoff:
            kept += 1
            continue
        try:
            call("POST", f"/records/{record['uuid']}/status",
                 {"status": "cancelled", "expected_status": "booked"})
            cleared += 1
            print(f"cleared {record['data'].get('local_time')} on {record['data'].get('blocks_slot')}")
        except urllib.error.HTTPError as error:
            print(f"could not clear {record['uuid']}: {error.code}", file=sys.stderr)

    print(f"{cleared} cleared, {kept} still within the last {MAX_AGE_MINUTES} minutes")


if __name__ == "__main__":
    main()
