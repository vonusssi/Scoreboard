"""
Offline-first sync for shared Scoreboard profiles.

Data model
----------
A profile is no longer stored as absolute numbers but as:
    baseline   - the scores the profile had before event tracking started
                 (used to migrate old profiles without losing anything)
    events     - every +/- button press, each with a unique id
    pending    - ids of events not yet uploaded
    share_code - None for local-only profiles, otherwise the online code

The displayed scores are always recomputed from baseline + events.
Merging two devices is therefore trivial: take the union of all events.
Nothing gets lost or counted twice, no matter who was offline when.

Remote layout (Firebase Realtime Database):
    /shared/<code>/name
    /shared/<code>/baseline/<game>
    /shared/<code>/events/<event_id>
"""
import copy
import json
import secrets
import time
import uuid
from datetime import date

from kivy.network.urlrequest import UrlRequest

try:
    import certifi
    CA_FILE = certifi.where()
except ImportError:
    CA_FILE = None

GAMES = ["Ever", "Pagan", "Wonders", "Clever", "Clever4",
         "Kniffel", "Targi", "Dice", "Harmonies"]

# no 0/O/1/I so codes are easy to read out loud
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 10


# --------------------------------------------------------------------------
# Local data helpers
# --------------------------------------------------------------------------
def empty_game():
    return [[0, 0], ["00.00.0000", "00.00.0000"], [0, 0]]


def new_profile():
    return {
        "baseline": {g: empty_game() for g in GAMES},
        "events": {},
        "pending": [],
        "share_code": None,
    }


def read_profile(store, name):
    """Return a (deep-copied) profile in the new format.
    Old-format profiles are migrated once and saved back."""
    # JsonStore.get returns its internal dict -> copy, so we never
    # mutate stored data by accident
    raw = copy.deepcopy(store.get(name))

    if "baseline" in raw:
        raw.setdefault("events", {})
        raw.setdefault("pending", [])
        raw.setdefault("share_code", None)
        for g in GAMES:
            raw["baseline"].setdefault(g, empty_game())
        return raw

    # old format: {"Ever": [...], "Pagan": [...], ...}
    data = new_profile()
    for g in GAMES:
        if g in raw:
            data["baseline"][g] = raw[g]
    store.put(name, **data)
    return data


def unique_name(store, name):
    base, i = name, 2
    while store.exists(name):
        name = f"{base} ({i})"
        i += 1
    return name


def make_event(game, player, sign):
    return {
        "id": uuid.uuid4().hex,
        "ts": time.time(),
        "game": game,
        "player": player,
        "sign": sign,
        "date": date.today().strftime("%d.%m.%Y"),
    }


def compute_scores(baseline, events):
    """Replay all events on top of the baseline, oldest first."""
    scores = {g: copy.deepcopy(baseline.get(g, empty_game())) for g in GAMES}

    ordered = sorted(events.values(), key=lambda e: (e.get("ts", 0), e.get("id", "")))
    for ev in ordered:
        try:
            game, p, sign = ev["game"], int(ev["player"]), int(ev["sign"])
        except (KeyError, TypeError, ValueError):
            continue
        if game not in scores or p not in (0, 1):
            continue

        g = scores[game]
        other = 1 - p
        g[0][p] += sign
        if sign > 0:                      # a win
            g[1][p] = ev.get("date", g[1][p])
            g[2][p] += 1
            g[2][other] = 0
        else:                             # a correction ("undo")
            g[2][p] = max(0, g[2][p] - 1)
    return scores


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------
class SyncManager:
    def __init__(self, base_url, store, on_profile_updated=None):
        self.base_url = base_url.rstrip("/")
        self.store = store
        self.on_profile_updated = on_profile_updated
        self._busy = set()    # profiles with a request in flight
        self._again = set()   # profiles that changed while busy

    # ---- low level -------------------------------------------------------
    def _url(self, code, sub=""):
        return f"{self.base_url}/shared/{code}{sub}.json"

    def _request(self, url, method="GET", body=None, on_success=None, on_fail=None):
        def ok(req, result):
            if isinstance(result, (bytes, str)):
                try:
                    result = json.loads(result)
                except ValueError:
                    pass
            if on_success:
                on_success(result)

        def fail(req, error):
            if on_fail:
                on_fail(error)

        UrlRequest(
            url,
            method=method,
            req_body=json.dumps(body) if body is not None else None,
            req_headers={"Content-Type": "application/json"},
            on_success=ok,
            on_failure=fail,   # HTTP errors (e.g. 401 wrong rules)
            on_error=fail,     # no connection, timeout, ...
            timeout=10,
            ca_file=CA_FILE,
        )

    def _finish(self, name):
        self._busy.discard(name)
        if name in self._again:
            self._again.discard(name)
            self.sync_profile(name)

    # ---- periodic sync ---------------------------------------------------
    def sync_all(self):
        for name in self.store.keys():
            self.sync_profile(name)

    def sync_profile(self, name):
        """Push pending local events, then pull remote events.
        Fails silently when offline - it is simply retried later."""
        if not self.store.exists(name):
            return
        data = read_profile(self.store, name)
        code = data["share_code"]
        if not code:
            return
        if name in self._busy:
            self._again.add(name)
            return
        self._busy.add(name)

        pending = [i for i in data["pending"] if i in data["events"]]
        if not pending:
            self._pull(name, code)
            return

        body = {i: data["events"][i] for i in pending}
        self._request(
            self._url(code, "/events"), "PATCH", body,
            on_success=lambda _: self._after_push(name, code, pending),
            on_fail=lambda _: self._finish(name),
        )

    def _after_push(self, name, code, sent):
        if self.store.exists(name):
            data = read_profile(self.store, name)
            data["pending"] = [i for i in data["pending"] if i not in sent]
            self.store.put(name, **data)
        self._pull(name, code)

    def _pull(self, name, code):
        self._request(
            self._url(code, "/events"), "GET",
            on_success=lambda res: self._merge(name, res),
            on_fail=lambda _: self._finish(name),
        )

    def _merge(self, name, remote_events):
        try:
            if not self.store.exists(name) or not isinstance(remote_events, dict):
                return
            data = read_profile(self.store, name)
            new = {k: v for k, v in remote_events.items() if k not in data["events"]}
            if not new:
                return
            data["events"].update(new)
            self.store.put(name, **data)
            if self.on_profile_updated:
                self.on_profile_updated(name)
        finally:
            self._finish(name)

    # ---- sharing / joining (need to be online once) ----------------------
    def share_profile(self, name, on_done, on_fail):
        data = read_profile(self.store, name)
        if data["share_code"]:
            on_done(data["share_code"])
            return

        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        sent_ids = set(data["events"])
        body = {"name": name, "baseline": data["baseline"], "events": data["events"]}

        def done(_):
            if not self.store.exists(name):
                return
            d = read_profile(self.store, name)
            d["share_code"] = code
            # anything pressed while the upload was running is still pending
            d["pending"] = [i for i in d["events"] if i not in sent_ids]
            self.store.put(name, **d)
            on_done(code)
            self.sync_profile(name)

        self._request(self._url(code), "PUT", body, done, on_fail)

    def join_profile(self, code, on_done, on_fail):
        code = code.strip().upper().replace(" ", "").replace("-", "")
        if len(code) != CODE_LENGTH or any(c not in CODE_ALPHABET for c in code):
            on_fail("Invalid code.")
            return

        # already joined earlier? just open it
        for name in self.store.keys():
            if read_profile(self.store, name)["share_code"] == code:
                on_done(name)
                self.sync_profile(name)
                return

        def got(result):
            if not isinstance(result, dict) or "baseline" not in result:
                on_fail("No shared profile with this code.")
                return
            name = unique_name(self.store, result.get("name") or "Shared")
            data = new_profile()
            for g in GAMES:
                if g in result["baseline"]:
                    data["baseline"][g] = result["baseline"][g]
            data["events"] = result.get("events") or {}
            data["share_code"] = code
            self.store.put(name, **data)
            on_done(name)

        self._request(self._url(code), "GET", None, got,
                      lambda _: on_fail("Could not reach the server."))
