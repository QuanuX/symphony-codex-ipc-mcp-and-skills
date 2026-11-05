#!/usr/bin/env python3
"""Optional Notion OAuth and explicit report publishing. Python 3.11+, stdlib only.

This adapter never runs Symphony commands or polls page edits. MCP credentials
and Notion workspace credentials are separate. Every external write is explicit.
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import stat
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

API = "https://api.notion.com"
VERSION = "2026-03-11"  # Explicit API baseline, independent of MCP protocol.
MAX_BYTES = 1024 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def read_private(path):
    path = Path(path)
    require(path.is_absolute(), "Private paths must be absolute")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        require(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid() and not st.st_mode & 0o077,
                "Private files must be owned, regular, mode 0600 or stricter")
        raw = f.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "Private file exceeds limit")
        return json.loads(raw)


def private_parent(path):
    p = Path(path)
    require(p.is_absolute(), "Private paths must be absolute")
    st = p.parent.lstat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and not st.st_mode & 0o077,
            "Private directory must be owned, mode 0700, and not a symlink")
    return p


def write_private(path, obj, replace=False):
    path = private_parent(path)
    raw = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()
    require(len(raw) <= MAX_BYTES, "Document exceeds limit")
    temp = path.with_name(path.name + ".tmp-" + secrets.token_hex(8)) if replace else path
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    if replace:
        os.replace(temp, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never send workspace credentials to another host.


def request(path, payload, authorization):
    require(path in ("/v1/oauth/token", "/v1/oauth/revoke", "/v1/pages"), "Unsupported Notion operation")
    data = json.dumps(payload, ensure_ascii=False).encode()
    require(len(data) <= 500000, "Notion payload exceeds 500KB")
    req = Request(API + path, data=data, method="POST", headers={
        "Authorization": authorization, "Notion-Version": VERSION, "Content-Type": "application/json"})
    opener = build_opener(HTTPSHandler(), NoRedirect())
    try:
        with opener.open(req, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, "Notion response exceeds limit")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        # No response body, auth code, token or uploaded content in diagnostics.
        raise RuntimeError(f"Notion HTTP {exc.code}; no automatic retry") from None


def config(path):
    c = read_private(path)
    require(c.get("schema") == "symphony.notion.publisher.v1", "Unsupported publisher profile")
    require(set(c) <= {"schema", "client_id", "client_secret_file", "redirect_uri", "token_file", "workspace_id", "allowed_parent_pages"}, "Unknown publisher field")
    require(isinstance(c.get("workspace_id"), str) and c["workspace_id"], "Select expected workspace_id")
    require(isinstance(c.get("allowed_parent_pages"), list) and c["allowed_parent_pages"], "Select allowed parent pages")
    require(all(isinstance(p, str) and p for p in c["allowed_parent_pages"]), "Invalid parent page")
    private_parent(c["token_file"])
    return c


def basic(c):
    secret = read_private(c["client_secret_file"])["client_secret"]
    require(isinstance(secret, str) and secret, "Missing client secret")
    return "Basic " + base64.b64encode((c["client_id"] + ":" + secret).encode()).decode()


def token(c):
    t = read_private(c["token_file"])
    require(t.get("workspace_id") == c["workspace_id"] and t.get("access_token"), "Workspace/token binding mismatch")
    return t


def authorize(c):
    """One-shot state-bound callback; user completes consent in their browser."""
    uri = urlsplit(c["redirect_uri"])
    require(uri.scheme in ("https", "http") and uri.path == "/notion/callback" and not uri.query and not uri.fragment and not uri.username,
            "Use a registered /notion/callback URI without query or fragment")
    if uri.scheme == "http":
        require(uri.hostname == "127.0.0.1", "Plain HTTP allowed only for loopback callback")
    require(not Path(c["token_file"]).exists(), "Existing token file preserved; use a new profile for reauthorization")
    # HTTPS callback uses a user-owned tunnel to this local port. No inbound
    # credentials or authorization server are exposed by the MCP listener.
    port = uri.port if uri.hostname == "127.0.0.1" and uri.scheme == "http" else 8766
    require(port is not None and 1024 <= port <= 65535, "Explicit loopback port required")
    state = secrets.token_urlsafe(48)
    expires = time.monotonic() + 600
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # URL contains a one-use authorization code.

        def do_GET(self):
            parsed = urlsplit(self.path)
            q = parse_qs(parsed.query, keep_blank_values=True)
            valid = (parsed.path == "/notion/callback" and time.monotonic() < expires and
                     len(q.get("state", [])) == 1 and secrets.compare_digest(q["state"][0], state) and not result)
            if not valid:
                self.send_response(400)
                self.end_headers()
                return
            result["consumed"] = True
            try:
                require("error" not in q and len(q.get("code", [])) == 1, "Notion authorization denied or invalid")
                t = request("/v1/oauth/token", {"grant_type": "authorization_code", "code": q["code"][0], "redirect_uri": c["redirect_uri"]}, basic(c))
                require(t.get("workspace_id") == c["workspace_id"] and t.get("access_token"), "Authorized workspace differs from selected workspace")
                write_private(c["token_file"], t)
                result["ok"] = True
            except Exception:
                result["ok"] = False
            self.send_response(200 if result["ok"] else 400)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Connection saved. Return to your terminal." if result["ok"] else b"Authorization failed. Return to your terminal; no automatic retry.")

    class BoundedServer(HTTPServer):
        def get_request(self):
            sock, address = super().get_request()
            sock.settimeout(3)
            return sock, address

    with BoundedServer(("127.0.0.1", port), Callback) as server:
        server.timeout = 1
        url = API + "/v1/oauth/authorize?" + urlencode({"owner": "user", "client_id": c["client_id"], "redirect_uri": c["redirect_uri"], "response_type": "code", "state": state})
        print("Complete Notion consent in your browser:\n" + url, flush=True)
        while not result and time.monotonic() < expires:
            server.handle_request()
    require(result.get("ok"), "Authorization failed or expired; inspect Notion connection settings before trying again")
    return {"connected": True, "workspace_id": c["workspace_id"]}


def prepare(c, parent, title, body, kind, output):
    require(parent in c["allowed_parent_pages"], "Parent page outside configured scope")
    require(kind in ("report", "incident", "research"), "Unsupported document kind")
    require(0 < len(title) <= 200 and 0 < len(body) <= 100000, "Title/body exceeds limit or is empty")
    t = token(c)
    publication = secrets.token_hex(16)
    # Plain-text blocks avoid executable templates and preserve supplied text.
    text = f"Symphony {kind}\nPublication ID: {publication}\n\n" + body
    chunks = [text[i:i + 1800] for i in range(0, len(text), 1800)]
    payload = {"parent": {"page_id": parent}, "properties": {"title": {"type": "title", "title": [{"type": "text", "text": {"content": title}}]}},
               "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}} for chunk in chunks]}
    plan = {"schema": "symphony.notion.publication.v1", "publication_id": publication,
            "workspace_id": c["workspace_id"], "token_binding": digest(t), "payload": payload,
            "created_at": time.time(), "expires_at": time.time() + 900}
    plan["sha256"] = digest(plan)
    write_private(output, plan)
    return {"plan": str(output), "workspace_id": c["workspace_id"], "parent_page": parent,
            "title": title, "kind": kind, "publication_id": publication, "sha256": plan["sha256"], "published": False}


def publish(c, plan_path, expected_sha):
    plan_path = private_parent(plan_path)
    plan = read_private(plan_path)
    checksum = plan.pop("sha256")
    require(checksum == expected_sha == digest(plan), "Plan checksum does not match the approved preview")
    require(plan.get("schema") == "symphony.notion.publication.v1" and time.time() < plan["expires_at"], "Plan expired or invalid")
    t = token(c)
    require(plan["token_binding"] == digest(t) and plan["workspace_id"] == c["workspace_id"], "Connection changed; prepare a new preview")
    require(plan["payload"]["parent"]["page_id"] in c["allowed_parent_pages"], "Destination no longer allowed")
    receipt_path = plan_path.with_name(plan_path.name + ".receipt.json")
    receipt = {"publication_id": plan["publication_id"], "workspace_id": c["workspace_id"],
               "approved_sha256": checksum, "outcome": "unknown_requires_reconciliation", "retry_automatically": False}
    # Exclusive durable claim BEFORE network dispatch; a second process or retry
    # cannot publish this plan again, including after a crash or lost response.
    write_private(receipt_path, receipt)
    try:
        response = request("/v1/pages", plan["payload"], "Bearer " + t["access_token"])
        require(response.get("object") == "page" and response.get("id"), "Notion did not return a page receipt")
        receipt.update(outcome="published", page_id=response["id"], url=response.get("url"))
        write_private(receipt_path, receipt, replace=True)
    except Exception:
        # Original unknown receipt survives; do not print uploaded content.
        raise RuntimeError(f"Publication outcome unknown. Inspect {receipt_path} and search Notion for publication ID {plan['publication_id']}. Do not blindly retry.") from None
    return receipt


def refresh(c):
    t = token(c)
    require(t.get("refresh_token"), "No refresh token; reauthorize explicitly")
    lock = Path(c["token_file"] + ".refresh-pending.json")
    write_private(lock, {"outcome": "unknown_until_saved", "retry_automatically": False})
    result = request("/v1/oauth/token", {"grant_type": "refresh_token", "refresh_token": t["refresh_token"]}, basic(c))
    require(result.get("access_token") and result.get("refresh_token"), "Incomplete refresh response")
    require(result.get("workspace_id", c["workspace_id"]) == c["workspace_id"], "Refreshed workspace mismatch")
    t.update(result)
    write_private(c["token_file"], t, replace=True)
    lock.unlink()
    return {"refreshed": True, "existing_publication_plans_invalidated": True}


def revoke(c):
    t = token(c)
    request("/v1/oauth/revoke", {"token": t["access_token"]}, basic(c))
    Path(c["token_file"]).unlink()
    return {"revoked": True, "workspace_id": c["workspace_id"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("authorize", "status", "refresh", "revoke"):
        sub.add_parser(name)
    preview = sub.add_parser("prepare")
    preview.add_argument("--parent-page", required=True)
    preview.add_argument("--title", required=True)
    preview.add_argument("--body-file", type=Path, required=True)
    preview.add_argument("--kind", choices=("report", "incident", "research"), default="report")
    preview.add_argument("--output", type=Path, required=True)
    send = sub.add_parser("publish")
    send.add_argument("--plan", type=Path, required=True)
    send.add_argument("--approve-sha256", required=True)
    args = p.parse_args()
    try:
        c = config(args.config)
        if args.action == "authorize":
            result = authorize(c)
        elif args.action == "status":
            t = token(c)
            result = {"workspace_id": t["workspace_id"], "credentials_stored": True, "live_access": "not_probed", "allowed_parent_pages": c["allowed_parent_pages"]}
        elif args.action == "prepare":
            with args.body_file.open("rb") as f:
                raw = f.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, "Report file exceeds limit")
            result = prepare(c, args.parent_page, args.title, raw.decode("utf-8"), args.kind, args.output)
        elif args.action == "publish":
            result = publish(c, args.plan, args.approve_sha256)
        elif args.action == "refresh":
            result = refresh(c)
        else:
            result = revoke(c)
        print(json.dumps(result))
    except Exception as exc:
        # Inputs and remote response bodies are deliberately absent from errors.
        p.exit(2, f"Notion adapter: {exc}\n")


if __name__ == "__main__":
    main()
