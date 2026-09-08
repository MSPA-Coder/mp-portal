from django.apps import AppConfig
from django.core.checks import register


class ContatosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contatos"
    verbose_name = "Contatos do site"

    def ready(self) -> None:
        from contatos.checks import verificar_configuracao_publica

        register(verificar_configuracao_publica)
