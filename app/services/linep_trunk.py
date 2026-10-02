"""
Lease-bound, SL1-signed client for the L.I.A.R.A. cluster trunk (linepd on
VM108, TCP 9000 + lease on UDP 9001).

Ported from www.mw-dresden.de (modules/linep_node/infrastructure/trunk.py) so
Personal speaks to the cluster like the MW backend does: HELLO -> INVITE ->
LEASE_ACK on the control port, then a signed SESSION_BIND on the data
connection, then every frame carries an HMAC-SHA-256/128 (ADR 0003 in
Mentor82/L.I.A.R.A.-OS). The cluster currently knows a single SL1 key ring, so
this host holds the cluster key (root-less, mode 0600, outside the repo and the
world-readable .env) until linepd has per-client key rings.

This module imports `linep` at import time; services.linep_provider only
imports it once LiNeP is actually used (the package is optional, see
requirements.txt).
"""
from __future__ import annotations

import secrets
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from linep.v0_2 import (
    LiNePClient,
    NodeEndpointIdentity,
    SessionBindEnvelope,
    UdpControlDatagram,
    decode_control_datagram,
    decode_header,
    decode_session_bind,
    encode_control_datagram,
    encode_session_bind,
    sign_envelope,
    verify_envelope,
)
from linep.v0_2.constants import ControlMessageType, MessageDirection


@dataclass(frozen=True, slots=True)
class TrunkRoute:
    host: str
    port: int
    control_port: int
    key_path: str


def load_key(path: str) -> tuple[int, bytes]:
    """Read the current key only; never include key material in errors/repr."""
    values = {}
    for line in Path(path).read_text(encoding="ascii").splitlines():
        name, sep, value = line.partition("=")
        if sep:
            values[name.strip()] = value.strip()
    try:
        key_id = int(values["key_id"])
        key = bytes.fromhex(values["key"])
    except (KeyError, ValueError):
        raise ValueError("Invalid LiNeP SL1 key file") from None
    if not 0 < key_id <= 65535 or len(key) != 32:
        raise ValueError("Invalid LiNeP SL1 key file")
    return key_id, key


def acquire_lease(route: TrunkRoute, timeout: float) -> SessionBindEnvelope:
    """HELLO -> matching INVITE -> ACK, using a connected UDP socket."""
    identity = NodeEndpointIdentity(secrets.randbits(64) or 1, secrets.randbits(64) or 1, 1)
    hello = UdpControlDatagram(
        node_id=identity.node_id,
        runtime_id=identity.runtime_id,
        endpoint_id=identity.endpoint_id,
        control_seq=1,
        control_epoch=time.time_ns() // 1000,
        flags=1,
        tcp_port=route.port,
    )
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.settimeout(timeout)
        udp.connect((route.host, route.control_port))
        udp.send(encode_control_datagram(hello))
        invite = decode_control_datagram(udp.recv(128))
        if invite is None or (
            invite.message_type != int(ControlMessageType.INVITE)
            or (invite.node_id, invite.runtime_id, invite.endpoint_id)
            != (identity.node_id, identity.runtime_id, identity.endpoint_id)
            or invite.control_epoch != hello.control_epoch
            or invite.lease_token == 0
        ):
            raise ConnectionError("Invalid LiNeP trunk lease invitation")
        hello.message_type = int(ControlMessageType.LEASE_ACK)
        hello.control_seq = 2
        hello.lease_token = invite.lease_token
        udp.send(encode_control_datagram(hello))
    # ACK has no reply. Let linepd's UDP loop activate the lease before TCP bind.
    time.sleep(0.05)
    return SessionBindEnvelope(identity, hello.control_epoch, invite.lease_token)


class TrunkClient(LiNePClient):
    """Upstream codecs and stream handling, with mandatory SL1 framing.

    Usage: `with TrunkClient(route, timeout) as client: client.bind(); ...`
    """

    def __init__(self, route: TrunkRoute, timeout: float) -> None:
        super().__init__(route.host, route.port, timeout)
        self._route = route
        self._key_id, self._key = load_key(route.key_path)
        self._binding: SessionBindEnvelope | None = None
        self._out_seq = 1
        self._in_seq = 0
        self._send_lock = threading.Lock()
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def bind(self) -> None:
        self._binding = acquire_lease(self._route, self.timeout)
        self._send_all(encode_session_bind(self._binding))
        confirmation = decode_session_bind(self._recv_envelope())
        if confirmation is None or (
            confirmation.identity != self._binding.identity
            or confirmation.control_epoch != self._binding.control_epoch
            or confirmation.lease_token != self._binding.lease_token
        ):
            raise ConnectionError("LiNeP trunk did not confirm the signed session")
        self._heartbeat_thread = threading.Thread(target=self._heartbeats, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeats(self) -> None:
        binding = self._binding
        heartbeat = UdpControlDatagram(
            message_type=int(ControlMessageType.HEARTBEAT),
            node_id=binding.identity.node_id,
            runtime_id=binding.identity.runtime_id,
            endpoint_id=binding.identity.endpoint_id,
            control_epoch=binding.control_epoch,
            control_seq=2,
            lease_token=binding.lease_token,
            flags=1,
            tcp_port=self.port,
        )
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(1.0)
            udp.connect((self.host, self._route.control_port))
            while not self._heartbeat_stop.wait(30.0):
                heartbeat.control_seq += 1
                try:
                    udp.send(encode_control_datagram(heartbeat))
                except OSError:
                    # Retry at the next interval; stale leases fail closed at linepd.
                    continue

    def close(self) -> None:
        self._heartbeat_stop.set()
        super().close()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=1.1)

    def _send_all(self, data: bytes) -> None:
        if self._binding is None:
            raise ConnectionError("LiNeP trunk session is not bound")
        # CANCEL can be sent from the event-loop thread while the worker ACKs.
        with self._send_lock:
            signed = sign_envelope(
                data,
                self._binding,
                MessageDirection.INITIATOR_TO_RESPONDER,
                self._out_seq,
                self._key_id,
                self._key,
            )
            super()._send_all(signed)
            self._out_seq += 1

    def _recv_envelope(self) -> bytes:
        header = self._recv_exact(32)
        decoded = decode_header(header)
        if decoded is None or not decoded.flags & 1 or decoded.payload_len > 32 * 1024 * 1024:
            raise ConnectionError("Invalid or unsigned LiNeP trunk frame")
        raw = header + self._recv_exact(24 + decoded.payload_len)
        ok, auth, payload, _ = verify_envelope(
            raw,
            self._binding,
            MessageDirection.RESPONDER_TO_INITIATOR,
            self._key,
        )
        if (
            not ok
            or auth is None
            or (auth.key_id != self._key_id or auth.auth_seq != self._in_seq + 1)
        ):
            raise ConnectionError("LiNeP SL1 authentication or sequence check failed")
        self._in_seq = auth.auth_seq
        # Upstream plain codecs must not see the authentication extension.
        return header[:7] + bytes([header[7] & ~1]) + header[8:] + payload
