"""Configuracao do projeto Django `portal` (MP Portal).

Backend unico: PostgreSQL. Segredo e modo de depuracao vem do ambiente e nao
possuem padrao permissivo: uma implantacao sem `DJANGO_SECRET_KEY` falha ao
subir, e `DEBUG` so liga quando pedido explicitamente.

O formato deste arquivo acompanha `financeiro/settings.py` do ControleBancario
de proposito -- e o segundo projeto Django da frota, e divergir na configuracao
sem motivo custaria a cada leitura futura.
"""

import os
from pathlib import Path

from sharedauth.secrets import resolver_segredo

BASE_DIR = Path(__file__).resolve().parent.parent


def _read_required_secret(name: str) -> str:
    """Le segredo por arquivo no Compose e so aceita ambiente no modo local.

    `REQUIRE_FILE_SECRETS=true` e o contrato do Compose operacional. A queda
    para variavel direta e mantida somente para comandos locais explicitos, que
    nao passam por esse contrato.

    A mecanica vem de `sharedauth.secrets`, compartilhada com os irmaos; o que
    continua sendo decisao deste projeto e quando a forma direta e aceitavel.
    """
    require_file = os.environ.get("REQUIRE_FILE_SECRETS", "false").lower() == "true"
    return resolver_segredo(name, aceitar_variavel=not require_file, obrigatorio=True)


def _lista_do_ambiente(nome: str) -> tuple[str, ...]:
    """Le uma variavel separada por virgula, descartando espacos e vazios."""
    return tuple(item.strip() for item in os.environ.get(nome, "").split(",") if item.strip())


# SECURITY WARNING: keep the secret key used in production secret!
# No Compose, a chave e lida de /run/secrets e a ausencia falha ao subir.
SECRET_KEY = _read_required_secret("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
# O padrao e desligado: a imagem de runtime nao pode expor tracebacks so porque
# a variavel nao foi informada.
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    # `django.contrib.admin` NAO entra, pela mesma razao escrita no
    # ControleBancario: `django.contrib.auth.admin` registra o modelo de
    # usuario automaticamente, entao uma conta `is_staff` editaria contas,
    # senhas e o proprio `is_superuser` por fora de qualquer trava, e
    # `/admin/login/` autenticaria senha por um caminho que nao e o `/login`
    # limitado pelo nginx central. A area administrativa deste projeto e a de
    # `contatos`, com autorizacao explicita e um conjunto de acoes fechado.
    #
    # Consequencia pratica: contas sao criadas por `manage.py createsuperuser`
    # e a senha e trocada por `manage.py changepassword`, nao por tela. Os dois
    # comandos vem de `django.contrib.auth` e nao dependem do admin.
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps do projeto
    "core",
    "contas",
    "contatos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serve o STATIC_ROOT gerado por `collectstatic`. Em
    # desenvolvimento esse diretorio nao existe (quem serve e o app
    # `staticfiles`), entao o middleware e inserido logo abaixo apenas quando ha
    # o que servir.
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.security.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portal.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "mp_portal"),
        "USER": os.environ.get("POSTGRES_USER", "mp_portal"),
        "PASSWORD": _read_required_secret("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# A aplicacao nunca deve conectar como 'postgres': e o superusuario
# administrativo do cluster, com privilegio sobre todo banco, nao so o proprio.
# Transformar uma configuracao perigosa em erro de subida vale mais que um risco
# silencioso -- mesma familia de validacao que `USE_HTTPS` tem abaixo.
if DATABASES["default"]["USER"] == "postgres":
    raise RuntimeError(
        "POSTGRES_USER nao pode ser 'postgres': e o superusuario administrativo "
        "do cluster. Defina POSTGRES_USER com uma conta dedicada da aplicacao "
        "(o compose.yaml ja usa 'mp_portal' como padrao)."
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# O backend com manifesto exige `collectstatic` previo (a etapa `migrate` do
# Compose faz isso). Em desenvolvimento os arquivos sao servidos direto de
# STATICFILES_DIRS, sem hash.
_USE_MANIFEST_STATIC = not DEBUG

if _USE_MANIFEST_STATIC:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if _USE_MANIFEST_STATIC
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Modelo de usuario proprio desde a primeira migracao. Trocar depois exige
# recriar o schema, e o custo hoje e uma classe vazia.
AUTH_USER_MODEL = "contas.UsuarioPortal"

# `/login` e nao `/entrar`: o nginx central do VPS aplica limite de taxa
# compartilhado exatamente a `POST /login` (ver `vps/nginx/conf.d/00-comum.conf`
# no repositorio `manutencao`). Nomear a rota assim herda essa protecao no dia
# da publicacao, sem configuracao nova.
LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/atendimento/"
LOGOUT_REDIRECT_URL = "/login"

# Endurecimento de transporte. E uma propriedade da implantacao, nao do modo de
# depuracao: a instalacao padrao publica em loopback sobre HTTP, onde cookies
# `Secure` simplesmente nao seriam enviados e o redirect para HTTPS levaria a
# uma porta que ninguem atende. Ligue junto com um proxy TLS a frente.
USE_HTTPS = os.environ.get("USE_HTTPS", "False").lower() == "true"
CSRF_TRUSTED_ORIGINS = list(_lista_do_ambiente("CSRF_TRUSTED_ORIGINS"))

if USE_HTTPS:
    if not CSRF_TRUSTED_ORIGINS:
        raise RuntimeError(
            "CSRF_TRUSTED_ORIGINS e obrigatoria quando USE_HTTPS=True. "
            "Informe as origens HTTPS publicas separadas por virgula."
        )
    if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
        raise RuntimeError("CSRF_TRUSTED_ORIGINS deve conter somente origens HTTPS validas.")

SESSION_COOKIE_NAME = "mp_portal_session"
SESSION_COOKIE_SECURE = USE_HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", 28800))  # 8 horas

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# `same-origin`, nao `no-referrer`. Sob `no-referrer` o navegador serializa o
# cabecalho `Origin` como `null` tambem em POST de mesma origem (Fetch spec), e
# a protecao CSRF do Django recusa a requisicao com 403 mesmo com o token
# correto. Aqui o custo seria dobrado: a rota de contato decide por `Origin`.
SECURE_REFERRER_POLICY = "same-origin"
CSRF_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_HTTPONLY = True

if USE_HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # O proxy TLS informa o esquema original; sem isso o Django veria HTTP e
    # entraria em loop de redirect.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# O corpo aceito e pequeno de proposito: este servico nao recebe upload nenhum,
# e um limite baixo transforma um POST gigante em 400 antes de virar trabalho.
DATA_UPLOAD_MAX_MEMORY_SIZE = 131072  # 128 KiB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 64
FILE_UPLOAD_MAX_MEMORY_SIZE = 0

# ---------------------------------------------------------------------------
# Recebimento de contato do site (achado L20 do LEVANTAMENTO_2026-09.md)
# ---------------------------------------------------------------------------

# Origens autorizadas a enviar `POST /contato`. VAZIO SIGNIFICA RECUSAR TUDO
# fora do modo de depuracao -- ver `contatos/origens.py`. Nao ha padrao com o
# dominio escrito: o site foi construido sem o dominio em arquivo nenhum (fase
# F5) e o portal nao vai reintroduzir esse acoplamento.
CONTATO_ORIGENS_PERMITIDAS = _lista_do_ambiente("CONTATO_ORIGENS_PERMITIDAS")

# Limite de envios por origem de rede numa janela deslizante. Nao substitui o
# limite do nginx: e a defesa que continua valendo quando o servico e acessado
# por outro caminho.
CONTATO_MAX_POR_JANELA = int(os.environ.get("CONTATO_MAX_POR_JANELA", 5))
CONTATO_JANELA_MINUTOS = int(os.environ.get("CONTATO_JANELA_MINUTOS", 15))

# Redes das quais `X-Forwarded-For` pode ser acreditado. VAZIO significa usar
# somente `REMOTE_ADDR` -- o padrao correto para a instalacao local e a unica
# escolha segura enquanto nao se sabe qual e a rede do proxy. No VPS, esta e a
# rede do nginx central.
CONTATO_PROXIES_CONFIAVEIS = _lista_do_ambiente("CONTATO_PROXIES_CONFIAVEIS")

# Prazo de retencao declarado no aviso de privacidade. O comando
# `manage.py expurgar_contatos` apaga o que passa disso; mudar o numero aqui
# sem mudar o aviso torna o aviso falso -- ha teste que compara os dois.
CONTATO_RETENCAO_DIAS = int(os.environ.get("CONTATO_RETENCAO_DIAS", 730))

# Canal pelo qual o titular exerce os direitos do art. 18 da LGPD. Sem isto o
# aviso de privacidade nao tem como ser cumprido, entao `manage.py check`
# REPROVA a subida fora do modo de depuracao (ver `contatos/apps.py`).
CONTATO_CANAL_TITULAR = os.environ.get("CONTATO_CANAL_TITULAR", "").strip()

# Tamanho maximo de cada campo de texto livre. O formulario do site nao impoe
# limite, e o banco nao deve ser o primeiro lugar a descobrir isso.
CONTATO_TAMANHO_MAXIMO_MENSAGEM = int(os.environ.get("CONTATO_TAMANHO_MAXIMO_MENSAGEM", 4000))

LOGGING = {
    "version": 1,
    # `True` desligaria loggers ja criados no processo -- inclusive o da
    # aplicacao. Foi exatamente o defeito latente que a fase F1 encontrou nos
    # `migrations/env.py` dos irmaos, e ele nao vai nascer de novo aqui.
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        # Rotacionado: o arquivo vive num volume do conteiner e cresceria sem
        # limite com FileHandler puro.
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "portal.log",
            "maxBytes": int(os.environ.get("LOG_MAX_BYTES", 5 * 1024 * 1024)),
            "backupCount": int(os.environ.get("LOG_BACKUP_COUNT", 5)),
            "encoding": "utf-8",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "portal": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
