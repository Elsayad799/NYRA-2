from __future__ import annotations
import hashlib, io, json
try:
    from PIL import Image
except Exception:
    Image=None

class MediaUnderstanding:
    """Ephemeral media inspection. Bytes are never persisted by this component."""
    def inspect_image(self, data: bytes, caption=''):
        meta={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()[:24],'caption':caption or ''}
        if Image:
            try:
                with Image.open(io.BytesIO(data)) as im:
                    meta.update({'format':im.format,'width':im.width,'height':im.height,'mode':im.mode})
            except Exception: pass
        return meta
    def summary(self, media_type, meta, caption=''):
        bits=[f'media={media_type}']
        if meta.get('width'): bits.append(f"size={meta['width']}x{meta['height']}")
        if meta.get('format'): bits.append(f"format={meta['format']}")
        if caption: bits.append(f'caption={caption[:300]}')
        return '; '.join(bits)
