import socket
from typing import Optional, Dict, Any

try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually connect, just determines outbound interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_service_info_payload(name: str, port: int) -> Dict[str, Any]:
    return {
        "name": name,
        "type": "_antigravity._tcp.local.",
        "port": port,
        "ip": get_local_ip()
    }

class DiscoveryService:
    def __init__(self, name: str = "Antigravity Bridge", port: int = 8765):
        self.name = name
        self.port = port
        self.zeroconf: Optional[Any] = None
        self.info: Optional[Any] = None

    def start(self) -> bool:
        if not ZEROCONF_AVAILABLE:
            print("[Discovery] zeroconf module not installed. Run 'pip install zeroconf' for automatic Wi-Fi discovery.")
            return False
        
        try:
            local_ip = get_local_ip()
            desc = {"version": "1.0.0", "path": "/ws"}
            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self.info = ServiceInfo(
                "_antigravity._tcp.local.",
                f"{self.name}._antigravity._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties=desc,
                server=f"{socket.gethostname()}.local."
            )
            self.zeroconf.register_service(self.info)
            print(f"[Discovery] mDNS service registered: {self.name} on {local_ip}:{self.port}")
            return True
        except Exception as e:
            print(f"[Discovery] Failed to register mDNS service: {e}")
            return False

    def stop(self):
        if self.zeroconf and self.info:
            try:
                self.zeroconf.unregister_service(self.info)
                self.zeroconf.close()
            except Exception:
                pass
            self.zeroconf = None
            self.info = None
