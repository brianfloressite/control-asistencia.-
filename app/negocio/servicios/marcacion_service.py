"""Módulos de Integración Biométrica (CU05) y Marcado por Contingencia (CU06, CU07)."""
from datetime import datetime, timedelta
from flask import current_app
from app.datos import modelos as m
from app.datos.repositorios import (RelojRepositorio, SincronizacionRepositorio, ColaboradorRepositorio, MarcaRepositorio,
                                    DispositivoRepositorio, ReporteFallaRepositorio, TurnoRepositorio)
from app.negocio.servicios import ErrorNegocio
from app.negocio.servicios.seguridad_service import BitacoraService

TIPOS_FALLA = {"ENERGIA": "Corte de energía", "RED": "Caída de red", "LECTURA": "Falla de lectura dactilar o facial"}


class BiometricoService:
    """Sincroniza las marcas del reloj ZKTeco usando la librería pyzk (protocolo TCP/UDP 4370)."""

    @staticmethod
    def _leer_reloj(reloj):
        from zk import ZK  # importación diferida: solo se necesita al sincronizar
        zk = ZK(reloj.ip, port=reloj.puerto, timeout=current_app.config.get("ZK_TIMEOUT", 5))
        conn = zk.connect()
        try:
            conn.disable_device()
            return [(str(a.user_id), a.timestamp, "ENTRADA" if a.punch in (0, 4) else "SALIDA") for a in conn.get_attendance()]
        finally:
            conn.enable_device()
            conn.disconnect()

    @staticmethod
    def importar_registros(reloj, registros):
        """Consolida registros (codigo, fecha_hora, tipo) sin duplicados. Devuelve (nuevas, sin_colaborador)."""
        nuevas, huerfanas = 0, set()
        for codigo, fecha_hora, tipo in registros:
            colab = ColaboradorRepositorio.por_codigo(codigo)
            if colab is None:
                huerfanas.add(codigo)
                continue
            if MarcaRepositorio.existe(colab.id_colaborador, fecha_hora, tipo):
                continue
            MarcaRepositorio.agregar(m.Marca(id_colaborador=colab.id_colaborador, fecha_hora=fecha_hora, tipo=tipo,
                                             origen="BIOMETRICO", id_reloj=reloj.id_reloj, estado="APROBADA"))
            nuevas += 1
        return nuevas, huerfanas

    @classmethod
    def sincronizar(cls, reloj_id=None, usuario=None, lector=None):
        relojes = [RelojRepositorio.obtener(reloj_id)] if reloj_id else RelojRepositorio.activos()
        resultados = []
        for reloj in relojes:
            log = m.SincronizacionLog(id_reloj=reloj.id_reloj, id_usuario=usuario.id_usuario if usuario else None,
                                      tipo="MANUAL" if usuario else "AUTOMATICA", inicio=datetime.now(), estado="EXITOSA")
            SincronizacionRepositorio.agregar(log)
            try:
                registros = (lector or cls._leer_reloj)(reloj)
                nuevas, huerfanas = cls.importar_registros(reloj, registros)
                log.marcas_descargadas = nuevas
                if huerfanas:
                    log.mensaje = f"Códigos sin colaborador: {', '.join(sorted(huerfanas))[:200]}"
            except Exception as exc:  # reloj sin energía, caída de red, etc. Se reintenta en el siguiente ciclo
                SincronizacionRepositorio.deshacer()
                log = m.SincronizacionLog(id_reloj=reloj.id_reloj, id_usuario=usuario.id_usuario if usuario else None,
                                          tipo="MANUAL" if usuario else "AUTOMATICA", inicio=datetime.now(), estado="ERROR",
                                          mensaje=f"Reloj no disponible: {exc}"[:255])
                SincronizacionRepositorio.agregar(log)
            log.fin = datetime.now()
            BitacoraService.registrar(usuario.id_usuario if usuario else None, "SINCRONIZAR", "Biométrico",
                                      f"{reloj.nombre}: {log.estado} ({log.marcas_descargadas} marcas)", commit=False)
            SincronizacionRepositorio.guardar()
            resultados.append(log)
        return resultados


class ContingenciaService:
    @staticmethod
    def dispositivo_autorizado(identificador):
        return DispositivoRepositorio.autorizado(identificador)

    @staticmethod
    def registrar_marca(colaborador, tipo, motivo, identificador_dispositivo, ip=None, usuario=None):
        """CU06: marca con la hora del servidor (RNF5) solo desde equipos autorizados (RNF6)."""
        if colaborador is None:
            raise ErrorNegocio("Su usuario no está asociado a un colaborador.")
        dispositivo = DispositivoRepositorio.autorizado(identificador_dispositivo)
        if dispositivo is None:
            raise ErrorNegocio("Equipo no autorizado para marcar.")
        if tipo not in ("ENTRADA", "SALIDA"):
            raise ErrorNegocio("Seleccione entrada o salida.")
        if not (motivo or "").strip():
            raise ErrorNegocio("Indique el motivo de la contingencia.")
        ahora = datetime.now().replace(microsecond=0)
        if TurnoRepositorio.vigente(colaborador.id_colaborador, ahora.date()) is None:
            raise ErrorNegocio("No tiene un turno asignado para hoy.")
        if MarcaRepositorio.ultima_del_colaborador(colaborador.id_colaborador, tipo, ahora - timedelta(minutes=5)):
            raise ErrorNegocio(f"Ya registró una marca de {tipo.lower()} hace menos de 5 minutos.")
        reporte = ReporteFallaRepositorio.abierto_cualquiera(horas=12)
        marca = m.Marca(id_colaborador=colaborador.id_colaborador, fecha_hora=ahora, tipo=tipo, origen="CONTINGENCIA",
                        id_dispositivo=dispositivo.id_dispositivo, id_reporte=reporte.id_reporte if reporte else None,
                        motivo=motivo.strip()[:150], ip_origen=ip, estado="PENDIENTE")
        MarcaRepositorio.agregar(marca)
        BitacoraService.registrar(usuario.id_usuario if usuario else None, "MARCAR", "Contingencia",
                                  f"{tipo} {ahora:%H:%M:%S} desde {dispositivo.nombre}", ip, commit=False)
        MarcaRepositorio.guardar()
        return marca

    @staticmethod
    def reportar_falla(colaborador, tipo, descripcion, id_reloj, ip=None, usuario=None):
        """CU07: si ya existe un reporte abierto del mismo tipo en la última hora, vincula al colaborador."""
        if tipo not in TIPOS_FALLA:
            raise ErrorNegocio("Seleccione el tipo de falla.")
        if colaborador is None:
            raise ErrorNegocio("Su usuario no está asociado a un colaborador.")
        reloj = RelojRepositorio.obtener(int(id_reloj or 0)) or (RelojRepositorio.activos() or [None])[0]
        if reloj is None:
            raise ErrorNegocio("No hay un reloj biométrico registrado.")
        reporte = ReporteFallaRepositorio.abierto_reciente(tipo)
        nuevo = reporte is None
        if nuevo:
            reporte = m.ReporteFalla(id_reloj=reloj.id_reloj, tipo_falla=tipo, descripcion=(descripcion or "")[:255])
            ReporteFallaRepositorio.agregar(reporte)
            ReporteFallaRepositorio.guardar()
        if not any(rc.id_colaborador == colaborador.id_colaborador for rc in reporte.colaboradores):
            ReporteFallaRepositorio.agregar(m.ReporteFallaColaborador(id_reporte=reporte.id_reporte, id_colaborador=colaborador.id_colaborador))
        BitacoraService.registrar(usuario.id_usuario if usuario else None, "REPORTAR", "Contingencia",
                                  f"Falla {TIPOS_FALLA[tipo]} (#{reporte.id_reporte})", ip, commit=False)
        ReporteFallaRepositorio.guardar()
        return reporte, nuevo
