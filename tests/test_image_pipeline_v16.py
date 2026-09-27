import io
import sys
import types


def test_image_generator_has_provider_failover(monkeypatch):
    from src.media import image_generator as mod
    from src.media.image_providers import ProviderResult
    class Fake:
        name = "test_provider"
        def available(self): return True
        def generate(self, prompt, aspect_ratio="1:1", count=1):
            return ProviderResult(self.name, [b"png"])
    monkeypatch.setattr(mod, "PollinationsProvider", lambda: Fake())
    g = mod.ImageGenerator()
    assert g.available
    assert g.generate("NYRA portrait") == [b"png"]


def test_image_generator_reports_empty_result(monkeypatch):
    fake = types.ModuleType('integrations.photo_source')
    fake.last_error = 'no token'
    fake.generate_images_api = lambda prompt, ratio, count: None
    monkeypatch.setitem(sys.modules, 'integrations.photo_source', fake)
    from src.media.image_generator import ImageGenerator
    g = ImageGenerator()
    try:
        g.generate('NYRA portrait')
    except RuntimeError as exc:
        assert 'no images' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')


def test_image_request_variants_are_routed_before_ai():
    import ast, re
    source = open('src/telegram/adapter.py', encoding='utf-8').read()
    tree = ast.parse(source)
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_looks_like_self_image_request')
    fn = ast.Module(body=[method], type_ignores=[])
    ns = {'re': re}
    exec(compile(fn, 'adapter.py', 'exec'), ns)
    check = ns['_looks_like_self_image_request']
    assert check('عايزك صورة ليكي')
    assert check('عايزك تبعتيلي صورة')
    assert check('عايز اشوف صورة بتاعتك')
    assert check('وريني صورتك')
