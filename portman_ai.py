"""
PortMan.AI - Intelligent Port Switching & Container Routing for NATOS
Manages port allocation, localhost container routing, and dynamic port switching.
"""

import socket
import random
from datetime import datetime


class PortManAI:
    """PortMan.AI - AI-driven port management and container routing."""

    def __init__(self):
        self.port_map = {}
        self.container_routes = {}
        self.port_range = (5000, 5099)
        self.forwarding_rules = []
        self.active = False
        self._init_default_ports()

    def _init_default_ports(self):
        """Initialize default port allocations."""
        defaults = [
            {"service": "natos-core", "port": 5000, "protocol": "http",
             "container": "natos-main"},
            {"service": "telemetry-ws", "port": 5000, "protocol": "ws",
             "container": "natos-main"},
            {"service": "portman-mgmt", "port": 5001, "protocol": "http",
             "container": "portman-ai"},
            {"service": "sys-monitor", "port": 5002, "protocol": "http",
             "container": "sys-monitor"},
            {"service": "voice-signal", "port": 5003, "protocol": "ws",
             "container": "voice-chat"},
        ]
        for d in defaults:
            self.port_map[d["service"]] = {
                "service": d["service"],
                "port": d["port"],
                "protocol": d["protocol"],
                "container": d["container"],
                "status": "allocated",
                "allocated_at": datetime.now().isoformat(),
                "traffic_bytes": 0,
            }
        # Setup container routes
        containers = ["natos-main", "portman-ai", "sys-monitor", "voice-chat"]
        for cname in containers:
            self.container_routes[cname] = {
                "name": cname,
                "host": "127.0.0.1",
                "ports": [p["port"] for p in self.port_map.values()
                          if p["container"] == cname],
                "status": "running",
                "routing_mode": "direct",
            }

    def start(self):
        """Activate PortMan.AI port management."""
        self.active = True
        return {"status": "active", "managed_ports": len(self.port_map)}

    def stop(self):
        """Deactivate PortMan.AI."""
        self.active = False
        return {"status": "inactive"}

    def allocate_port(self, service_name, protocol="http", container=None):
        """Allocate a port for a service."""
        if service_name in self.port_map:
            return {"error": f"Service '{service_name}' already has port allocated"}
        # Find next available port
        used_ports = {p["port"] for p in self.port_map.values()}
        for port in range(self.port_range[0], self.port_range[1] + 1):
            if port not in used_ports:
                self.port_map[service_name] = {
                    "service": service_name,
                    "port": port,
                    "protocol": protocol,
                    "container": container or service_name,
                    "status": "allocated",
                    "allocated_at": datetime.now().isoformat(),
                    "traffic_bytes": 0,
                }
                return {"status": "allocated", "port": port,
                        "service": service_name}
        return {"error": "No ports available in range"}

    def release_port(self, service_name):
        """Release a port allocation."""
        if service_name not in self.port_map:
            return {"error": "Service not found"}
        port_info = self.port_map.pop(service_name)
        return {"status": "released", "port": port_info["port"]}

    def switch_port(self, service_name, new_port):
        """Switch a service to a different port."""
        if service_name not in self.port_map:
            return {"error": "Service not found"}
        if not (self.port_range[0] <= new_port <= self.port_range[1]):
            return {"error": f"Port must be in range {self.port_range}"}
        used = {p["port"] for n, p in self.port_map.items()
                if n != service_name}
        if new_port in used:
            return {"error": f"Port {new_port} already in use"}
        old_port = self.port_map[service_name]["port"]
        self.port_map[service_name]["port"] = new_port
        return {"status": "switched", "service": service_name,
                "old_port": old_port, "new_port": new_port}

    def add_forwarding_rule(self, source_port, dest_port, protocol="tcp"):
        """Add a port forwarding rule."""
        rule = {
            "id": len(self.forwarding_rules) + 1,
            "source_port": source_port,
            "dest_port": dest_port,
            "protocol": protocol,
            "host": "127.0.0.1",
            "active": True,
            "created_at": datetime.now().isoformat(),
        }
        self.forwarding_rules.append(rule)
        return {"status": "added", "rule": rule}

    def remove_forwarding_rule(self, rule_id):
        """Remove a port forwarding rule."""
        for i, rule in enumerate(self.forwarding_rules):
            if rule["id"] == rule_id:
                self.forwarding_rules.pop(i)
                return {"status": "removed", "rule_id": rule_id}
        return {"error": "Rule not found"}

    def add_container_route(self, container_name, host="127.0.0.1", ports=None):
        """Add a container route."""
        self.container_routes[container_name] = {
            "name": container_name,
            "host": host,
            "ports": ports or [],
            "status": "running",
            "routing_mode": "direct",
        }
        return {"status": "added", "container": container_name}

    def get_container_routes(self):
        """Get all container routing configurations."""
        return list(self.container_routes.values())

    def scan_port(self, port):
        """Check if a port is in use on localhost."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(('127.0.0.1', port))
                return {"port": port, "in_use": result == 0}
        except OSError:
            return {"port": port, "in_use": False, "error": "scan_failed"}

    def scan_port_range(self):
        """Scan managed port range for availability."""
        results = []
        for port in range(self.port_range[0], self.port_range[1] + 1):
            allocated_to = None
            for svc, info in self.port_map.items():
                if info["port"] == port:
                    allocated_to = svc
                    break
            results.append({
                "port": port,
                "allocated_to": allocated_to,
                "status": "allocated" if allocated_to else "free",
            })
        return results

    def get_status(self):
        """Get overall PortMan.AI status."""
        return {
            "active": self.active,
            "managed_ports": len(self.port_map),
            "port_range": list(self.port_range),
            "forwarding_rules": len(self.forwarding_rules),
            "container_routes": len(self.container_routes),
            "ports": list(self.port_map.values()),
            "containers": list(self.container_routes.values()),
            "rules": self.forwarding_rules,
        }
