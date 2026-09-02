import tomllib
from pathlib import Path

from app.version import __version__


def test_public_and_package_versions_are_consistent() -> None:
    repository_root = Path(__file__).parents[2]
    public_version = (repository_root / "VERSION").read_text(encoding="utf-8").strip()
    package_config = tomllib.loads(
        (repository_root / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert __version__ == public_version
    assert package_config["project"]["version"] == public_version.replace("-rc", "rc")
