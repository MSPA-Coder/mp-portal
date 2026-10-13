# syntax=docker/dockerfile:1.7
# A tag da série 3.15 acompanha correções de segurança. A CI semanal reconstrói
# com `--pull` e testa o site com a imagem atualizada.
FROM python:3.15-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN --mount=type=secret,id=local_ca,required=false \
    if [ -f /run/secrets/local_ca ]; then \
        cp /run/secrets/local_ca /usr/local/share/ca-certificates/local-root-ca.crt; \
        update-ca-certificates; \
    fi

# Correcoes de seguranca da base e das ferramentas de empacotamento.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip setuptools msgpack urllib3

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir --upgrade uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# Duas fases. Primeiro so as dependencias, numa camada que so se invalida
# quando `uv.lock` muda.
#
# O FLAG E `--locked`, E A DIFERENCA IMPORTA. `--frozen` apenas usa o lock sem
# olhar o `pyproject.toml`: com o lock desatualizado ele sai com SUCESSO e
# instala as versoes antigas, em silencio. `--locked` REPROVA.
#
# `sharedauth` vem de repositorio Git, e o lock o prende ao COMMIT, nao a tag.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --extra dev

# `quality` e a unica imagem do projeto: roda Ruff e a suite, e tambem o
# gerador (`docker compose run --rm gerar`). Nada daqui vai para a hospedagem --
# o que vai e a pasta `dist/site` que o gerador produz.
FROM base AS quality

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --extra dev

# pip inclui cópias de urllib3/msgpack e um SBOM embutido. Atualiza também o
# código que o pip importa nas instalações presentes nesta imagem.
RUN python - <<'PY'
import importlib.metadata
import json
import shutil
from pathlib import Path

global_site = Path("/usr/local/lib/python3.15/site-packages")
quality_site = Path("/opt/venv/lib/python3.15/site-packages")
global_distributions = {
    distribution.metadata["Name"].lower(): distribution.version
    for distribution in importlib.metadata.distributions(path=[str(global_site)])
}
wanted = ("msgpack", "setuptools", "urllib3")
versions = {
    name: global_distributions[name]
    for name in wanted
}

for site in (global_site, quality_site):
    vendor = site / "pip/_vendor"
    if not vendor.is_dir():
        continue
    for name in ("msgpack", "urllib3"):
        target = vendor / name
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(global_site / name, target)

    bom_path = vendor / "bom.cdx.json"
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
    replacements = {}
    for component in bom["components"]:
        name = component["name"].lower()
        if name not in versions:
            continue
        old_ref = component.get("bom-ref") or component.get("purl")
        new_ref = f"pkg:pypi/{name}@{versions[name]}"
        component["version"] = versions[name]
        component["purl"] = new_ref
        component["bom-ref"] = new_ref
        if old_ref:
            replacements[old_ref] = new_ref

    for dependency in bom["dependencies"]:
        if dependency.get("ref") in replacements:
            dependency["ref"] = replacements[dependency["ref"]]
        if "dependsOn" in dependency:
            dependency["dependsOn"] = [
                replacements.get(reference, reference)
                for reference in dependency["dependsOn"]
            ]
    bom_path.write_text(json.dumps(bom, indent=2) + "\n", encoding="utf-8")
PY

ENV PYTHONPATH=/workspace \
    RUFF_CACHE_DIR=/tmp/ruff-cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache"

CMD ["sh", "-c", "ruff check . && ruff format --check . && pytest"]
