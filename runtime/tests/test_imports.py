import importlib


def test_runtime_app_package_is_importable() -> None:
    runtime_app = importlib.import_module("runtime.app")
    assert runtime_app is not None


def test_runtime_shared_package_is_importable() -> None:
    shared_module = importlib.import_module("runtime.app.shared")
    assert shared_module is not None
