from __future__ import annotations
import re
import socket
from urllib.parse import urlparse
import requests

class LinkInspector:
    """Inspect a URL without logging in or executing its page in NYRA."""
    @staticmethod
    def inspect(url: str) -> dict:
        raw=(url or '').strip()
        if not re.match(r'^https?://', raw, re.I):
            raw='https://' + raw
        parsed=urlparse(raw)
        if not parsed.hostname:
            raise ValueError('invalid URL')
        try:
            ip=socket.gethostbyname(parsed.hostname)
        except Exception:
            ip=''
        try:
            r=requests.get(raw, timeout=15, allow_redirects=True, stream=True, headers={'User-Agent':'NYRA-AI-LinkTool/1.0'})
            final=r.url
            return {
                'url': raw,
                'final_url': final,
                'status': r.status_code,
                'content_type': r.headers.get('content-type',''),
                'server': r.headers.get('server',''),
                'redirected': final != raw,
                'hostname': parsed.hostname,
                'ip': ip,
                'https': parsed.scheme.lower() == 'https',
            }
        except Exception as exc:
            return {'url': raw,'hostname':parsed.hostname,'ip':ip,'https':parsed.scheme.lower()=='https','error':str(exc)}
