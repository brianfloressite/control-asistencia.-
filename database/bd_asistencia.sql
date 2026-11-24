-- =====================================================================
-- bd_asistencia · Sistema Web de Control de Asistencia (Funeraria Del Castillo)
-- Script DDL para MySQL 8.0 (InnoDB, utf8mb4). Equivale a la migración Alembic inicial.
-- Uso: mysql -u root -p < database/bd_asistencia.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS bd_asistencia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bd_asistencia;

-- Tabla area
CREATE TABLE area (
	id_area SMALLINT NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(60) NOT NULL, 
	estado BOOL NOT NULL, 
	PRIMARY KEY (id_area), 
	UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla cargo
CREATE TABLE cargo (
	id_cargo SMALLINT NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(60) NOT NULL, 
	estado BOOL NOT NULL, 
	PRIMARY KEY (id_cargo), 
	UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla dispositivo_autorizado
CREATE TABLE dispositivo_autorizado (
	id_dispositivo SMALLINT NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(60) NOT NULL, 
	tipo ENUM('PC','CELULAR') NOT NULL, 
	identificador VARCHAR(100) NOT NULL, 
	activo BOOL NOT NULL, 
	PRIMARY KEY (id_dispositivo), 
	UNIQUE (identificador)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla horario
CREATE TABLE horario (
	id_horario SMALLINT NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(50) NOT NULL, 
	hora_entrada TIME NOT NULL, 
	hora_salida TIME NOT NULL, 
	tolerancia_min SMALLINT NOT NULL, 
	es_guardia_24h BOOL NOT NULL, 
	PRIMARY KEY (id_horario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla perfil
CREATE TABLE perfil (
	id_perfil SMALLINT NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(30) NOT NULL, 
	descripcion VARCHAR(150), 
	PRIMARY KEY (id_perfil), 
	UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla reloj_biometrico
CREATE TABLE reloj_biometrico (
	id_reloj SMALLINT NOT NULL AUTO_INCREMENT, 
	nombre VARCHAR(50) NOT NULL, 
	ip VARCHAR(45) NOT NULL, 
	puerto INTEGER NOT NULL, 
	activo BOOL NOT NULL, 
	PRIMARY KEY (id_reloj)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla colaborador
CREATE TABLE colaborador (
	id_colaborador INTEGER NOT NULL AUTO_INCREMENT, 
	dni VARCHAR(8) NOT NULL, 
	nombres VARCHAR(60) NOT NULL, 
	apellidos VARCHAR(80) NOT NULL, 
	id_area SMALLINT NOT NULL, 
	id_cargo SMALLINT NOT NULL, 
	id_supervisor INTEGER, 
	codigo_biometrico VARCHAR(20) NOT NULL, 
	fecha_ingreso DATE NOT NULL, 
	estado ENUM('ACTIVO','CESADO') NOT NULL, 
	fecha_cese DATE, 
	motivo_cese VARCHAR(150), 
	PRIMARY KEY (id_colaborador), 
	UNIQUE (dni), 
	FOREIGN KEY(id_area) REFERENCES area (id_area), 
	FOREIGN KEY(id_cargo) REFERENCES cargo (id_cargo), 
	FOREIGN KEY(id_supervisor) REFERENCES colaborador (id_colaborador), 
	UNIQUE (codigo_biometrico)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla reporte_falla
CREATE TABLE reporte_falla (
	id_reporte INTEGER NOT NULL AUTO_INCREMENT, 
	id_reloj SMALLINT NOT NULL, 
	tipo_falla ENUM('ENERGIA','RED','LECTURA') NOT NULL, 
	descripcion VARCHAR(255), 
	fecha_hora DATETIME NOT NULL, 
	estado ENUM('ABIERTO','CERRADO') NOT NULL, 
	PRIMARY KEY (id_reporte), 
	FOREIGN KEY(id_reloj) REFERENCES reloj_biometrico (id_reloj)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla marca
CREATE TABLE marca (
	id_marca BIGINT NOT NULL AUTO_INCREMENT, 
	id_colaborador INTEGER NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	tipo ENUM('ENTRADA','SALIDA') NOT NULL, 
	origen ENUM('BIOMETRICO','CONTINGENCIA') NOT NULL, 
	id_reloj SMALLINT, 
	id_dispositivo SMALLINT, 
	id_reporte INTEGER, 
	motivo VARCHAR(150), 
	ip_origen VARCHAR(45), 
	estado ENUM('PENDIENTE','APROBADA','RECHAZADA') NOT NULL, 
	PRIMARY KEY (id_marca), 
	CONSTRAINT uq_marca UNIQUE (id_colaborador, fecha_hora, tipo), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador), 
	FOREIGN KEY(id_reloj) REFERENCES reloj_biometrico (id_reloj), 
	FOREIGN KEY(id_dispositivo) REFERENCES dispositivo_autorizado (id_dispositivo), 
	FOREIGN KEY(id_reporte) REFERENCES reporte_falla (id_reporte)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_marca_colab_fecha ON marca (id_colaborador, fecha_hora);

-- Tabla reporte_falla_colaborador
CREATE TABLE reporte_falla_colaborador (
	id_reporte INTEGER NOT NULL, 
	id_colaborador INTEGER NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	PRIMARY KEY (id_reporte, id_colaborador), 
	FOREIGN KEY(id_reporte) REFERENCES reporte_falla (id_reporte), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla turno_asignado
CREATE TABLE turno_asignado (
	id_turno INTEGER NOT NULL AUTO_INCREMENT, 
	id_colaborador INTEGER NOT NULL, 
	id_horario SMALLINT NOT NULL, 
	fecha_inicio DATE NOT NULL, 
	fecha_fin DATE NOT NULL, 
	PRIMARY KEY (id_turno), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador), 
	FOREIGN KEY(id_horario) REFERENCES horario (id_horario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_turno_asignado_id_colaborador ON turno_asignado (id_colaborador);

-- Tabla usuario
CREATE TABLE usuario (
	id_usuario INTEGER NOT NULL AUTO_INCREMENT, 
	id_colaborador INTEGER, 
	id_perfil SMALLINT NOT NULL, 
	username VARCHAR(40) NOT NULL, 
	password_hash VARCHAR(60) NOT NULL, 
	estado ENUM('ACTIVO','INACTIVO','BLOQUEADO') NOT NULL, 
	intentos_fallidos SMALLINT NOT NULL, 
	ultimo_acceso DATETIME, 
	creado_en DATETIME NOT NULL, 
	PRIMARY KEY (id_usuario), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador), 
	FOREIGN KEY(id_perfil) REFERENCES perfil (id_perfil), 
	UNIQUE (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla bitacora
CREATE TABLE bitacora (
	id_bitacora BIGINT NOT NULL AUTO_INCREMENT, 
	id_usuario INTEGER, 
	fecha_hora DATETIME NOT NULL, 
	accion VARCHAR(30) NOT NULL, 
	modulo VARCHAR(40) NOT NULL, 
	detalle VARCHAR(255), 
	ip VARCHAR(45), 
	PRIMARY KEY (id_bitacora), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_bitacora_fecha_hora ON bitacora (fecha_hora);

-- Tabla inconsistencia
CREATE TABLE inconsistencia (
	id_inconsistencia BIGINT NOT NULL AUTO_INCREMENT, 
	id_colaborador INTEGER NOT NULL, 
	id_turno INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	tipo ENUM('TARDANZA','FALTA','OMISION','ABANDONO') NOT NULL, 
	minutos INTEGER NOT NULL, 
	estado ENUM('DETECTADA','POR_JUSTIFICAR','JUSTIFICADA','CONFIRMADA') NOT NULL, 
	observacion VARCHAR(255), 
	PRIMARY KEY (id_inconsistencia), 
	CONSTRAINT uq_inconsistencia UNIQUE (id_colaborador, fecha, tipo), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador), 
	FOREIGN KEY(id_turno) REFERENCES turno_asignado (id_turno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE INDEX ix_inconsistencia_fecha ON inconsistencia (fecha);

-- Tabla regla_negocio
CREATE TABLE regla_negocio (
	id_regla SMALLINT NOT NULL AUTO_INCREMENT, 
	tolerancia_min SMALLINT NOT NULL, 
	monto_bono NUMERIC(8, 2) NOT NULL, 
	max_tardanzas_bono SMALLINT NOT NULL, 
	tardanzas_alerta SMALLINT NOT NULL, 
	faltas_alerta SMALLINT NOT NULL, 
	vigencia_desde DATE NOT NULL, 
	vigente BOOL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	PRIMARY KEY (id_regla), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla sincronizacion_log
CREATE TABLE sincronizacion_log (
	id_sync INTEGER NOT NULL AUTO_INCREMENT, 
	id_reloj SMALLINT NOT NULL, 
	id_usuario INTEGER, 
	tipo ENUM('AUTOMATICA','MANUAL') NOT NULL, 
	inicio DATETIME NOT NULL, 
	fin DATETIME, 
	marcas_descargadas INTEGER NOT NULL, 
	estado ENUM('EXITOSA','ERROR') NOT NULL, 
	mensaje VARCHAR(255), 
	PRIMARY KEY (id_sync), 
	FOREIGN KEY(id_reloj) REFERENCES reloj_biometrico (id_reloj), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla alerta_disciplinaria
CREATE TABLE alerta_disciplinaria (
	id_alerta INTEGER NOT NULL AUTO_INCREMENT, 
	id_colaborador INTEGER NOT NULL, 
	id_regla SMALLINT NOT NULL, 
	tipo ENUM('TARDANZAS','FALTAS') NOT NULL, 
	cantidad SMALLINT NOT NULL, 
	fecha_generacion DATE NOT NULL, 
	estado ENUM('ACTIVA','ATENDIDA','DESCARTADA') NOT NULL, 
	motivo_descarte VARCHAR(255), 
	PRIMARY KEY (id_alerta), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador), 
	FOREIGN KEY(id_regla) REFERENCES regla_negocio (id_regla)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla justificacion
CREATE TABLE justificacion (
	id_justificacion INTEGER NOT NULL AUTO_INCREMENT, 
	id_inconsistencia BIGINT NOT NULL, 
	motivo VARCHAR(255) NOT NULL, 
	ruta_evidencia VARCHAR(255), 
	fecha_registro DATETIME NOT NULL, 
	estado ENUM('PENDIENTE','APROBADA','RECHAZADA') NOT NULL, 
	PRIMARY KEY (id_justificacion), 
	FOREIGN KEY(id_inconsistencia) REFERENCES inconsistencia (id_inconsistencia)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla liquidacion_bono
CREATE TABLE liquidacion_bono (
	id_liquidacion INTEGER NOT NULL AUTO_INCREMENT, 
	anio SMALLINT NOT NULL, 
	mes SMALLINT NOT NULL, 
	id_regla SMALLINT NOT NULL, 
	estado ENUM('BORRADOR','CERRADA') NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	fecha_cierre DATETIME, 
	PRIMARY KEY (id_liquidacion), 
	CONSTRAINT uq_liquidacion_periodo UNIQUE (anio, mes), 
	FOREIGN KEY(id_regla) REFERENCES regla_negocio (id_regla), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla bono_detalle
CREATE TABLE bono_detalle (
	id_detalle INTEGER NOT NULL AUTO_INCREMENT, 
	id_liquidacion INTEGER NOT NULL, 
	id_colaborador INTEGER NOT NULL, 
	tardanzas SMALLINT NOT NULL, 
	faltas SMALLINT NOT NULL, 
	abandonos SMALLINT NOT NULL, 
	apto BOOL NOT NULL, 
	monto NUMERIC(8, 2) NOT NULL, 
	PRIMARY KEY (id_detalle), 
	FOREIGN KEY(id_liquidacion) REFERENCES liquidacion_bono (id_liquidacion), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla medida_disciplinaria
CREATE TABLE medida_disciplinaria (
	id_medida INTEGER NOT NULL AUTO_INCREMENT, 
	id_alerta INTEGER NOT NULL, 
	id_colaborador INTEGER NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	tipo ENUM('AMONESTACION_VERBAL','AMONESTACION_ESCRITA','SUSPENSION','CESE') NOT NULL, 
	sustento TEXT NOT NULL, 
	fecha DATE NOT NULL, 
	ruta_carta_pdf VARCHAR(255), 
	estado ENUM('REGISTRADA','NOTIFICADA','CERRADA') NOT NULL, 
	PRIMARY KEY (id_medida), 
	FOREIGN KEY(id_alerta) REFERENCES alerta_disciplinaria (id_alerta), 
	FOREIGN KEY(id_colaborador) REFERENCES colaborador (id_colaborador), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabla validacion
CREATE TABLE validacion (
	id_validacion INTEGER NOT NULL AUTO_INCREMENT, 
	id_usuario INTEGER NOT NULL, 
	id_marca BIGINT, 
	id_justificacion INTEGER, 
	decision ENUM('APROBADA','RECHAZADA') NOT NULL, 
	observacion VARCHAR(255), 
	fecha_hora DATETIME NOT NULL, 
	PRIMARY KEY (id_validacion), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario), 
	FOREIGN KEY(id_marca) REFERENCES marca (id_marca), 
	FOREIGN KEY(id_justificacion) REFERENCES justificacion (id_justificacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
