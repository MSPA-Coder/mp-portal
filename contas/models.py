"""Modelo de usuario do portal.

`AUTH_USER_MODEL` proprio existe por uma razao mecanica: troca-lo depois da
primeira migracao e recriar schema. Herdar de `AbstractUser` custa pouco e
deixa a porta aberta.

O que este modelo deliberadamente NAO tem: vinculo com "cliente". O portal
ainda nao tem modulo com dado por cliente, e uma tabela de tenant sem
consumidor seria estrutura especulativa -- ver
`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`.

O unico campo alem dos de `AbstractUser` e `recebe_novos_contatos`: a caixa de
entrada do atendimento (ADR 0005 fase 5). Ele tem leitor -- a view publica de
contato consulta por ele --, entao nao e especulacao; e a semente do "sistema
formal de perfis", reduzida a um booleano.

Contas sao criadas e editadas pela tela `/painel/contas/` (ADR 0005 fase 4),
restrita a `is_staff`; `createsuperuser`/`changepassword` continuam valendo.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class UsuarioPortal(AbstractUser):
    #: Quem recebe cada nova solicitacao do formulario publico. No maximo uma
    #: conta com isto ativo -- a tela de contas desmarca as outras ao salvar.
    #: So faz sentido em conta `is_staff` (so ela ve o atendimento).
    recebe_novos_contatos = models.BooleanField(
        default=False, verbose_name="recebe as novas solicitações de contato"
    )

    class Meta:
        verbose_name = "usuario do portal"
        verbose_name_plural = "usuarios do portal"
        db_table = "contas_usuario"

    @classmethod
    def caixa_de_atendimento(cls) -> UsuarioPortal | None:
        """A conta designada para receber contato novo, ou None se nao houver."""
        return cls.objects.filter(
            recebe_novos_contatos=True, is_active=True, is_staff=True
        ).first()
