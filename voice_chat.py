"""
NATOS Voice Chat Module
Integrated voice chat with CHAiMERA orchestration support.
Uses WebRTC signaling via SocketIO for peer-to-peer audio.
"""

import time
import uuid
from datetime import datetime


class VoiceChatManager:
    """Manages voice chat rooms and WebRTC signaling for NATOS network."""

    def __init__(self):
        self.rooms = {}
        self.peers = {}
        self.active_channels = {}

    def create_room(self, room_name=None):
        """Create a new voice chat room."""
        room_id = str(uuid.uuid4())[:8]
        if room_name is None:
            room_name = f"natos-voice-{room_id}"
        self.rooms[room_id] = {
            "id": room_id,
            "name": room_name,
            "created_at": datetime.now().isoformat(),
            "peers": [],
            "max_peers": 8,
            "active": True,
            "muted_peers": [],
        }
        return self.rooms[room_id]

    def join_room(self, room_id, peer_id, peer_name="Anonymous"):
        """Add a peer to a voice chat room."""
        if room_id not in self.rooms:
            return {"error": "Room not found"}
        room = self.rooms[room_id]
        if len(room["peers"]) >= room["max_peers"]:
            return {"error": "Room is full"}
        peer_info = {
            "id": peer_id,
            "name": peer_name,
            "joined_at": datetime.now().isoformat(),
            "muted": False,
            "speaking": False,
            "audio_level": 0.0,
        }
        room["peers"].append(peer_info)
        self.peers[peer_id] = {"room_id": room_id, "info": peer_info}
        return {"status": "joined", "room": room, "peer": peer_info}

    def leave_room(self, room_id, peer_id):
        """Remove a peer from a voice chat room."""
        if room_id not in self.rooms:
            return {"error": "Room not found"}
        room = self.rooms[room_id]
        room["peers"] = [p for p in room["peers"] if p["id"] != peer_id]
        self.peers.pop(peer_id, None)
        if len(room["peers"]) == 0:
            room["active"] = False
        return {"status": "left", "room_id": room_id}

    def toggle_mute(self, room_id, peer_id):
        """Toggle mute state for a peer."""
        if room_id not in self.rooms:
            return {"error": "Room not found"}
        for peer in self.rooms[room_id]["peers"]:
            if peer["id"] == peer_id:
                peer["muted"] = not peer["muted"]
                return {"status": "toggled", "muted": peer["muted"]}
        return {"error": "Peer not found"}

    def update_audio_level(self, peer_id, level):
        """Update speaking/audio level for a peer."""
        if peer_id in self.peers:
            info = self.peers[peer_id]["info"]
            info["audio_level"] = max(0.0, min(1.0, level))
            info["speaking"] = level > 0.1
            return True
        return False

    def get_room_status(self, room_id):
        """Get current status of a voice chat room."""
        if room_id not in self.rooms:
            return {"error": "Room not found"}
        room = self.rooms[room_id]
        return {
            "id": room["id"],
            "name": room["name"],
            "active": room["active"],
            "peer_count": len(room["peers"]),
            "peers": room["peers"],
        }

    def list_rooms(self):
        """List all active voice chat rooms."""
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "peer_count": len(r["peers"]),
                "active": r["active"],
            }
            for r in self.rooms.values()
            if r["active"]
        ]

    def get_status(self):
        """Get overall voice chat system status."""
        active_rooms = [r for r in self.rooms.values() if r["active"]]
        total_peers = sum(len(r["peers"]) for r in active_rooms)
        return {
            "active_rooms": len(active_rooms),
            "total_peers": total_peers,
            "rooms": self.list_rooms(),
        }
