"""Modelo de usuario do portal.

Existe por uma razao unica e suficiente: trocar `AUTH_USER_MODEL` depois da
primeira migracao e uma operacao de recriar schema. Herdar de `AbstractUser`
agora custa uma classe vazia e deixa a porta aberta para o dia em que o portal
tiver conta de cliente -- que e quando os campos de verdade vao aparecer.

O que este modelo deliberadamente NAO tem hoje, e o motivo: nenhum vinculo com
"cliente". O portal ainda nao tem modulo com dado por cliente, e uma tabela de
tenant sem consumidor seria estrutura especulativa -- ver
`docs/adr/0002-multiusuario-adiado-ate-existir-modulo.md`, que registra a forma
recomendada e o gatilho que deve fazer a decisao voltar a mesa.

Contas sao criadas por `manage.py createsuperuser` (ou `changepassword`), nao
por tela: o projeto nao instala `django.contrib.admin` e a area de atendimento
so le e triagem contatos.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser


class UsuarioPortal(AbstractUser):
    class Meta:
        verbose_name = "usuario do portal"
        verbose_name_plural = "usuarios do portal"
        db_table = "contas_usuario"
