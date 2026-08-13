from pathlib import Path

import yaml


def main() -> None:
    data = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = set(data["services"])
    assert {"postgres", "redis", "api", "bot", "worker"}.issubset(services)
    assert data["services"]["api"]["environment"]["APP_PROCESS"] == "api"
    assert data["services"]["bot"]["environment"]["APP_PROCESS"] == "bot"
    assert data["services"]["worker"]["environment"]["APP_PROCESS"] == "worker"
    print("compose structure: ok")


if __name__ == "__main__":
    main()
