#!/usr/bin/env python3
"""
WebSocket broadcasting via HTTP trigger endpoint.
MCP handlers POST to /ws/emit, Flask route emits to WebSocket clients.
"""

from flask_socketio import SocketIO, emit
import time

socketio = None
connected_sids = set()
pending_events = []

def init_socketio(app):
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        logger=False,
        engineio_logger=False
    )

    @socketio.on("connect")
    def handle_connect():
        from flask import request
        sid = request.sid
        connected_sids.add(sid)
        print(f"🔌 WebSocket client connected: {sid} (total: {len(connected_sids)})")
        emit("server_info", {"version": "2.0.0", "timestamp": time.time()})

    @socketio.on("disconnect")
    def handle_disconnect():
        from flask import request
        sid = request.sid
        connected_sids.discard(sid)
        print(f"🔌 WebSocket client disconnected: {sid} (total: {len(connected_sids)})")

    @socketio.on("ping_test")
    def handle_ping(data):
        emit("pong_test", {"msg": "hello from server", "timestamp": time.time()})

    @socketio.on("check_events")
    def handle_check_events(data):
        """Client polls for pending events."""
        if pending_events:
            batch = [{"event": e, "data": d} for e, d in pending_events]
            pending_events.clear()
            emit("event_batch", {"events": batch})
            print(f"📡 Flushed {len(batch)} events via event_batch")

    # HTTP endpoint for internal emit trigger
    @app.route("/ws/emit", methods=["POST"])
    def ws_emit():
        from flask import request, jsonify
        data = request.get_json()
        event = data.get("event", "unknown")
        payload = data.get("payload", {})
        # Use server.manager to get all connected sids and send directly
        print(f"📡 Sending {event} to {len(connected_sids)} tracked clients: {connected_sids}")
        for sid in list(connected_sids):
            try:
                socketio.emit(event, payload, to=sid, namespace="/")
                print(f"  ✓ Sent to {sid}")
            except Exception as e:
                print(f"  ✗ Failed for {sid}: {e}")
        print(f"📡 HTTP-triggered emit: {event}")
        return jsonify({"ok": True})

    return socketio


def _broadcast(event, data):
    """Queue event for delivery via client polling."""
    pending_events.append((event, data))
    print(f"📡 Queued {event} ({len(pending_events)} pending)")


def broadcast_note_added(note_id, category, importance, preview="", entities=None, edges_created=0):
    _broadcast("note_added", {
        "id": note_id, "category": category, "importance": importance,
        "preview": preview[:200], "entities": entities or [],
        "edges_created": edges_created, "timestamp": time.time()
    })

def broadcast_note_updated(note_id, category, preview=""):
    _broadcast("note_updated", {
        "id": note_id, "category": category,
        "preview": preview[:200], "timestamp": time.time()
    })

def broadcast_note_deleted(note_id):
    _broadcast("note_deleted", {"id": note_id, "timestamp": time.time()})

def broadcast_search(query, result_count, top_ids, latency_ms):
    _broadcast("search_performed", {
        "query": query, "result_count": result_count,
        "top_ids": top_ids[:10], "latency_ms": round(latency_ms, 1),
        "timestamp": time.time()
    })

# HTTP polling endpoint (bypasses socketio transport issues)
from flask import jsonify

def register_http_poll(app):
    @app.route('/api/poll-events')
    def poll_events():
        import os
        from flask import request
        expected_key = os.environ.get("API_KEY", "")
        api_key = request.args.get('api_key', '')
        if expected_key and api_key != expected_key:
            return jsonify({"error": "unauthorized"}), 401
        if pending_events:
            batch = [{"event": e, "data": d} for e, d in pending_events]
            pending_events.clear()
            return jsonify({"events": batch})
        return jsonify({"events": []})
