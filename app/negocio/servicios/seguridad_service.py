"""Módulo de Seguridad y Usuarios: autenticación (CU01), usuarios (CU02) y bitácora (CU16)."""
from datetime import datetime
from flask import current_app
from app.extensions import bcrypt
from app.datos import modelos as m
from app.datos.repositorios import UsuarioRepositorio, PerfilRepositorio, BitacoraRepositorio, ColaboradorRepositorio
from app.negocio.servicios import ErrorNegocio

PERFILES = ["Administrador", "Gerencia", "RR.HH.", "Supervisor", "Colaborador"]


class BitacoraService:
    @staticmethod
    def registrar(usuario_id, accion, modulo, detalle="", ip=None, commit=True):
        BitacoraRepositorio.agregar(m.Bitacora(id_usuario=usuario_id, accion=accion, modulo=modulo,
                                               detalle=(detalle or "")[:255], ip=ip))
        if commit:
            BitacoraRepositorio.guardar()

    @staticmethod
    def consultar(id_usuario=None, accion=None, desde=None, hasta=None):
        if desde and hasta and desde > hasta:
            raise ErrorNegocio("La fecha de inicio no puede ser posterior a la fecha de fin.")
        return BitacoraRepositorio.buscar(id_usuario, accion, desde, hasta)


class AuthService:
    @staticmethod
    def hash_password(clave):
        return bcrypt.generate_password_hash(clave).decode("utf-8")

    @staticmethod
    def autenticar(username, clave, ip=None):
        """Valida credenciales con bcrypt; bloquea la cuenta tras N intentos fallidos (RNF3)."""
        if not username or not clave:
            raise ErrorNegocio("Ingrese usuario y contraseña.")
        usuario = UsuarioRepositorio.por_username(username.strip())
        if usuario is None:
            raise ErrorNegocio("Usuario o contraseña incorrectos.")
        if usuario.estado != "ACTIVO":
            raise ErrorNegocio("Usuario inactivo o bloqueado. Contacte al administrador.")
        if not bcrypt.check_password_hash(usuario.password_hash, clave):
            usuario.intentos_fallidos += 1
            maximo = current_app.config.get("MAX_INTENTOS_LOGIN", 5)
            if usuario.intentos_fallidos >= maximo:
                usuario.estado = "BLOQUEADO"
                BitacoraService.registrar(usuario.id_usuario, "BLOQUEO", "Seguridad", "Bloqueo por intentos fallidos", ip, commit=False)
            UsuarioRepositorio.guardar()
            raise ErrorNegocio("Usuario o contraseña incorrectos.")
        usuario.intentos_fallidos = 0
        usuario.ultimo_acceso = datetime.now()
        BitacoraService.registrar(usuario.id_usuario, "LOGIN", "Seguridad", "Inicio de sesión", ip, commit=False)
        UsuarioRepositorio.guardar()
        return usuario


class UsuarioService:
    @staticmethod
    def listar():
        return UsuarioRepositorio.todos()

    @staticmethod
    def perfiles():
        return [PerfilRepositorio.por_nombre(n) for n in PERFILES if PerfilRepositorio.por_nombre(n)]

    @staticmethod
    def guardar(datos, actor, ip=None, id_usuario=None):
        username = (datos.get("username") or "").strip()
        if len(username) < 4:
            raise ErrorNegocio("El nombre de usuario debe tener al menos 4 caracteres.")
        perfil = PerfilRepositorio.obtener(int(datos.get("id_perfil") or 0))
        if perfil is None:
            raise ErrorNegocio("Seleccione un perfil válido.")
        existente = UsuarioRepositorio.por_username(username)
        if existente and existente.id_usuario != id_usuario:
            raise ErrorNegocio("El nombre de usuario ya existe.")
        id_colab = int(datos["id_colaborador"]) if datos.get("id_colaborador") else None
        if id_colab and ColaboradorRepositorio.obtener(id_colab) is None:
            raise ErrorNegocio("El colaborador seleccionado no existe.")
        clave = datos.get("password") or ""
        if id_usuario:
            usuario = UsuarioRepositorio.obtener(id_usuario)
            accion = "ACTUALIZAR"
        else:
            if len(clave) < 8:
                raise ErrorNegocio("La contraseña inicial debe tener al menos 8 caracteres.")
            usuario = m.Usuario()
            UsuarioRepositorio.agregar(usuario)
            accion = "CREAR"
        usuario.username, usuario.id_perfil, usuario.id_colaborador = username, perfil.id_perfil, id_colab
        if clave:
            if len(clave) < 8:
                raise ErrorNegocio("La contraseña debe tener al menos 8 caracteres.")
            usuario.password_hash = AuthService.hash_password(clave)
        estado = datos.get("estado") or "ACTIVO"
        if estado != usuario.estado:
            usuario.intentos_fallidos = 0
        usuario.estado = estado
        BitacoraService.registrar(actor.id_usuario, accion, "Usuarios", f"Usuario {username} ({perfil.nombre})", ip, commit=False)
        UsuarioRepositorio.guardar()
        return usuario

    @staticmethod
    def cambiar_estado(id_usuario, estado, actor, ip=None):
        usuario = UsuarioRepositorio.obtener(id_usuario)
        if usuario is None:
            raise ErrorNegocio("Usuario no encontrado.")
        if usuario.id_usuario == actor.id_usuario and estado != "ACTIVO":
            raise ErrorNegocio("No puede desactivar su propio usuario.")
        usuario.estado = estado
        usuario.intentos_fallidos = 0
        BitacoraService.registrar(actor.id_usuario, "ESTADO", "Usuarios", f"{usuario.username} → {estado}", ip, commit=False)
        UsuarioRepositorio.guardar()
