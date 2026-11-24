# Sistema Web de Control de Asistencia y Evaluación del Personal

Proyecto EFSRT 2 · Integración de los componentes de las capas de **datos, negocio y vista**
Organización: Funeraria Del Castillo (Lima) · Equipo: Grupo 4

Sistema web en **arquitectura de 3 capas** con Python 3 + Flask + MySQL 8, integrado con el reloj biométrico
ZKTeco y con un módulo web/móvil de marcado por contingencia. Implementa los 16 casos de uso (CU01–CU16).

## Estructura del repositorio

```
control-asistencia/
├── app/
│   ├── presentacion/            ← CAPA DE VISTA
│   │   ├── templates/           plantillas Jinja2 de las 16 pantallas (Bootstrap 5)
│   │   ├── static/              css, js y librerías locales (Bootstrap, Bootstrap Icons, Chart.js)
│   │   └── filtros.py           formato de fechas/montos y menú por perfil
│   ├── negocio/                 ← CAPA DE LÓGICA DE NEGOCIO
│   │   ├── controladores/       blueprints de Flask (rutas web y API REST /api/v1)
│   │   ├── servicios/           reglas del negocio por módulo (Service Layer)
│   │   ├── seguridad.py         control de acceso por perfiles
│   │   └── tareas.py            sincronización programada con APScheduler
│   ├── datos/                   ← CAPA DE ACCESO A DATOS
│   │   ├── modelos.py           22 modelos ORM (Flask-SQLAlchemy)
│   │   └── repositorios.py      consultas encapsuladas (patrón Repository)
│   ├── extensions.py            SQLAlchemy, Migrate, Login, CSRF, Bcrypt
│   ├── cli.py                   comando `flask seed` (datos iniciales y de demostración)
│   └── __init__.py              create_app (Application Factory)
├── config/                      ← CONFIGURACIÓN
│   ├── settings.py              configuración por entorno (desarrollo, pruebas, producción)
│   ├── gunicorn.conf.py         servidor WSGI de producción
│   ├── nginx.conf               proxy inverso con HTTPS
│   ├── asistencia.service       servicio systemd
│   └── backup_mysql.sh          respaldo diario de la base de datos (RNF10)
├── migrations/                  ← MIGRACIONES (Flask-Migrate / Alembic)
│   └── versions/                migración inicial: esquema bd_asistencia (22 tablas)
├── database/                    scripts SQL para MySQL 8 (DDL y datos iniciales)
├── tests/                       pruebas unitarias e de integración (pytest)
├── docs/capturas/               capturas de las pantallas del sistema
├── run.py · wsgi.py             puntos de entrada (desarrollo / producción)
├── requirements.txt · .env.example
```

## Flujo entre capas

`Vista (plantilla Jinja2)` → `Controlador (blueprint)` → `Servicio (regla de negocio)` → `Repositorio` → `Modelo ORM` → `MySQL`

Ejemplo CU06: `contingencia/marcar.html` → `marcacion_ctrl.marcar()` → `ContingenciaService.registrar_marca()`
(valida equipo autorizado, turno y hora del servidor) → `MarcaRepositorio` → tabla `marca`.

## Patrones de diseño aplicados

| Patrón | Dónde |
|---|---|
| MVC / Arquitectura en capas | `presentacion` (vista), `negocio/controladores` (controlador), `datos/modelos` (modelo) |
| Application Factory | `app/__init__.py → create_app()` |
| Service Layer | `app/negocio/servicios/*` |
| Repository | `app/datos/repositorios.py` |
| Blueprint (módulos) | un blueprint por módulo en `app/negocio/controladores/` |
| Strategy configurable | reglas de bono y sanción versionadas en `regla_negocio` |
| Scheduler / Observer | sincronización automática del reloj en `app/negocio/tareas.py` |
| Decorator | `@perfiles(...)` para el control de acceso |

## Instalación

```bash
git clone https://github.com/<usuario>/control-asistencia.git
cd control-asistencia
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # edite DATABASE_URL y SECRET_KEY
```

Base de datos MySQL 8:

```sql
CREATE DATABASE bd_asistencia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'asistencia'@'localhost' IDENTIFIED BY 'CLAVE';
GRANT ALL ON bd_asistencia.* TO 'asistencia'@'localhost';
```

Crear las tablas con las migraciones y cargar datos:

```bash
flask db upgrade        # aplica migrations/versions (22 tablas)
flask seed              # perfiles, catálogos, usuarios y datos de demostración
python run.py           # http://localhost:5000
```

Alternativa sin migraciones: `mysql -u root -p < database/bd_asistencia.sql` y `database/datos_iniciales.sql`.

Usuarios de demostración (clave `Asistencia2026`): `admin`, `gerencia`, `rrhh`, `supervisor`, `jperez`, `rmendoza`.

## Pruebas

```bash
pytest -v
```

28 pruebas: unitarias de los servicios (bloqueo por intentos, DNI y código biométrico únicos, cruce de turnos,
tardanzas, faltas, omisiones, abandono de guardia, reglas del bono, equipo no autorizado, sincronización sin
duplicados y con el reloj caído) y de integración (perfiles, flujo contingencia → validación → bono,
carta PDF, exportación PDF/Excel, API REST y bitácora).

## API REST (v1)

| Método | Ruta | Perfil | Descripción |
|---|---|---|---|
| GET | `/api/v1/salud` | público | estado del servicio |
| GET | `/api/v1/dashboard/indicadores?anio&mes&area` | Gerencia, RR. HH. | indicadores del dashboard |
| GET | `/api/v1/colaboradores?area` | RR. HH. | colaboradores activos |
| GET | `/api/v1/mi-asistencia?desde&hasta` | autenticado | historial del colaborador |
| POST | `/api/v1/marcas/contingencia` | autenticado + equipo autorizado | registra una marca (JSON `tipo`, `motivo`) |

## Seguridad

Contraseñas con bcrypt, bloqueo tras 5 intentos, control de acceso por perfil, protección CSRF en todos los
formularios, cookies de sesión `HttpOnly`/`SameSite`, cabeceras de seguridad, marcas inalterables (las correcciones
quedan en `validacion` con usuario, fecha y motivo), bitácora de auditoría y HTTPS mediante Nginx.
