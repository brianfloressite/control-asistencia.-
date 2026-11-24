"""Comandos de consola: `flask seed` carga catálogos, usuarios iniciales y datos de demostración."""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import click
from app.extensions import db
from app.datos import modelos as m
from app.negocio.servicios.seguridad_service import AuthService, PERFILES


def cargar_datos(demo=True, hoy=None):
    hoy = hoy or date.today()
    if m.Perfil.query.first():
        return False
    perfiles = {n: m.Perfil(nombre=n, descripcion=d) for n, d in zip(PERFILES, [
        "Usuarios, sincronización y bitácora", "Dashboard y reportes", "Personal, turnos, reglas, bonos y medidas",
        "Valida marcas y audita inconsistencias", "Marca por contingencia y consulta su historial"])}
    db.session.add_all(perfiles.values())
    areas = {n: m.Area(nombre=n) for n in ["Administración", "Velatorio", "Traslados", "Atención al cliente"]}
    cargos = {n: m.Cargo(nombre=n) for n in ["Jefe de RR. HH.", "Supervisor", "Asesor funerario", "Conductor", "Personal de velatorio", "Gerente"]}
    db.session.add_all(list(areas.values()) + list(cargos.values()))
    hor = {
        "Mañana": m.Horario(nombre="Mañana", hora_entrada=time(8), hora_salida=time(16), tolerancia_min=10),
        "Tarde": m.Horario(nombre="Tarde", hora_entrada=time(14), hora_salida=time(22), tolerancia_min=10),
        "Guardia 24 h": m.Horario(nombre="Guardia 24 h", hora_entrada=time(8), hora_salida=time(8), tolerancia_min=10, es_guardia_24h=True),
        "Administrativo": m.Horario(nombre="Administrativo", hora_entrada=time(9), hora_salida=time(18), tolerancia_min=5),
    }
    db.session.add_all(hor.values())
    reloj = m.RelojBiometrico(nombre="Reloj sede principal", ip="192.168.1.201", puerto=4370)
    db.session.add(reloj)
    db.session.flush()

    gente = [("40112233", "Fabiola", "Cadillo Ramos", "Administración", "Gerente", "Administrativo"),
             ("41223344", "Estefania", "Orellana Díaz", "Administración", "Jefe de RR. HH.", "Administrativo"),
             ("42334455", "Brayan", "Flores Quispe", "Velatorio", "Supervisor", "Mañana"),
             ("43445566", "Juan", "Pérez Huamán", "Velatorio", "Personal de velatorio", "Mañana"),
             ("44556677", "Rosa", "Mendoza Ccori", "Atención al cliente", "Asesor funerario", "Tarde"),
             ("45667788", "Luis", "Torres Vega", "Traslados", "Conductor", "Guardia 24 h"),
             ("46778899", "Carmen", "Salas Rojas", "Atención al cliente", "Asesor funerario", "Mañana"),
             ("47889900", "Miguel", "Rivas León", "Traslados", "Conductor", "Tarde")]
    colabs = []
    for i, (dni, nom, ape, area, cargo, h) in enumerate(gente):
        c = m.Colaborador(dni=dni, nombres=nom, apellidos=ape, id_area=areas[area].id_area, id_cargo=cargos[cargo].id_cargo,
                          codigo_biometrico=str(101 + i), fecha_ingreso=date(2024, 3, 1) + timedelta(days=37 * i))
        db.session.add(c)
        colabs.append((c, hor[h]))
    db.session.flush()
    for c, _ in colabs[3:]:
        c.id_supervisor = colabs[2][0].id_colaborador

    clave = AuthService.hash_password("Asistencia2026")
    cuentas = [("admin", "Administrador", None), ("gerencia", "Gerencia", 0), ("rrhh", "RR.HH.", 1), ("supervisor", "Supervisor", 2),
               ("jperez", "Colaborador", 3), ("rmendoza", "Colaborador", 4)]
    usuarios = {}
    for u, p, idx in cuentas:
        usuarios[u] = m.Usuario(username=u, id_perfil=perfiles[p].id_perfil, password_hash=clave,
                                id_colaborador=colabs[idx][0].id_colaborador if idx is not None else None)
        db.session.add(usuarios[u])
    db.session.flush()
    db.session.add(m.ReglaNegocio(tolerancia_min=10, monto_bono=Decimal("150.00"), max_tardanzas_bono=1, tardanzas_alerta=3,
                                  faltas_alerta=2, vigencia_desde=date(hoy.year, 1, 1), vigente=True, id_usuario=usuarios["rrhh"].id_usuario))
    inicio = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
    fin = (hoy.replace(day=28) + timedelta(days=40)).replace(day=1) - timedelta(days=1)
    for c, h in colabs:
        if h.es_guardia_24h:  # guardias de 24 h: un día de guardia cada tres días
            d = inicio
            while d <= fin:
                db.session.add(m.TurnoAsignado(id_colaborador=c.id_colaborador, id_horario=h.id_horario, fecha_inicio=d, fecha_fin=d))
                d += timedelta(days=3)
        else:
            db.session.add(m.TurnoAsignado(id_colaborador=c.id_colaborador, id_horario=h.id_horario, fecha_inicio=inicio, fecha_fin=fin))
    if not demo:
        db.session.commit()
        return True

    # Marcas biométricas simuladas (con algunas tardanzas, faltas y abandonos) para demostrar los módulos
    rnd = random.Random(2026)
    dia = inicio
    contingencia_hoy = {c.id_colaborador for c, h in colabs[3:7] if not h.es_guardia_24h}
    ahora_real = datetime.now()
    while dia <= hoy:
        for idx, (c, h) in enumerate(colabs):
            if h.es_guardia_24h and (dia - inicio).days % 3:
                continue
            if dia == hoy and c.id_colaborador in contingencia_hoy:
                continue  # hoy el reloj no tuvo energía: estos colaboradores marcaron por contingencia
            r = rnd.random()
            if r < 0.03 + 0.03 * (idx == 3):
                continue  # falta
            ent = datetime.combine(dia, h.hora_entrada) + timedelta(minutes=rnd.randint(-12, 6))
            if r > 0.9 - 0.12 * (idx == 3):
                ent += timedelta(minutes=rnd.randint(15, 45))  # tardanza
            sal = datetime.combine(dia, h.hora_salida) + (timedelta(days=1) if h.es_guardia_24h else timedelta()) + timedelta(minutes=rnd.randint(0, 20))
            if ent > ahora_real:
                continue
            db.session.add(m.Marca(id_colaborador=c.id_colaborador, fecha_hora=ent.replace(second=rnd.randint(0, 59)), tipo="ENTRADA",
                                   origen="BIOMETRICO", id_reloj=reloj.id_reloj, estado="APROBADA"))
            if sal < ahora_real:
                db.session.add(m.Marca(id_colaborador=c.id_colaborador, fecha_hora=sal.replace(second=rnd.randint(0, 59)), tipo="SALIDA",
                                       origen="BIOMETRICO", id_reloj=reloj.id_reloj, estado="APROBADA"))
        dia += timedelta(days=1)
    disp = m.DispositivoAutorizado(nombre="Celular supervisor velatorio", tipo="CELULAR", identificador="demo-celular-001")
    falla = m.ReporteFalla(id_reloj=reloj.id_reloj, tipo_falla="ENERGIA", descripcion="Corte de luz en la sede",
                           fecha_hora=datetime.combine(hoy, time(7, 40)))
    db.session.add_all([disp, falla])
    db.session.flush()
    db.session.add(m.ReporteFallaColaborador(id_reporte=falla.id_reporte, id_colaborador=colabs[3][0].id_colaborador))
    for c, h in colabs[3:7]:
        if not h.es_guardia_24h:
            db.session.add(m.Marca(id_colaborador=c.id_colaborador, fecha_hora=datetime.combine(hoy, h.hora_entrada) - timedelta(minutes=rnd.randint(1, 9)),
                                   tipo="ENTRADA", origen="CONTINGENCIA", id_dispositivo=disp.id_dispositivo, id_reporte=falla.id_reporte,
                                   motivo="Reloj sin energía", ip_origen="192.168.1.50", estado="PENDIENTE"))
    for k in range(3, 0, -1):  # historial de sincronizaciones automáticas
        ini = datetime.combine(hoy - timedelta(days=k), time(23, 30))
        db.session.add(m.SincronizacionLog(id_reloj=reloj.id_reloj, tipo="AUTOMATICA", inicio=ini, fin=ini + timedelta(seconds=14),
                                           marcas_descargadas=rnd.randint(14, 18), estado="EXITOSA"))
    ini = datetime.combine(hoy, time(7, 45))
    db.session.add(m.SincronizacionLog(id_reloj=reloj.id_reloj, tipo="AUTOMATICA", inicio=ini, fin=ini + timedelta(seconds=5), estado="ERROR",
                                       mensaje="Reloj no disponible: timed out (corte de energía en la sede)"))
    for u in ("admin", "rrhh", "supervisor"):
        db.session.add(m.Bitacora(id_usuario=usuarios[u].id_usuario, accion="LOGIN", modulo="Seguridad", detalle="Inicio de sesión",
                                  ip="192.168.1.10", fecha_hora=datetime.now() - timedelta(hours=rnd.randint(1, 30))))
    db.session.commit()
    return True


def registrar_comandos(app):
    @app.cli.command("seed")
    @click.option("--sin-demo", is_flag=True, help="Solo catálogos y usuarios, sin marcas de demostración.")
    def seed(sin_demo):
        """Carga perfiles, catálogos, usuarios iniciales y datos de demostración."""
        if cargar_datos(demo=not sin_demo):
            click.echo("Datos iniciales cargados. Usuarios: admin, gerencia, rrhh, supervisor, jperez, rmendoza (clave: Asistencia2026)")
        else:
            click.echo("La base de datos ya tiene datos; no se cargó nada.")
