from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Nucleo"

    def ready(self):
        from django.db.backends.signals import connection_created

        from core.papel_do_banco import conferir_papel

        connection_created.connect(conferir_papel, dispatch_uid="core.conferir_papel")
