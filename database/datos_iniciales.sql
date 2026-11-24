-- Datos iniciales mínimos (catálogos y usuario administrador). Para datos de demostración use: flask seed
USE bd_asistencia;
INSERT INTO perfil (nombre, descripcion) VALUES
 ('Administrador','Usuarios, sincronización y bitácora'),('Gerencia','Dashboard y reportes'),
 ('RR.HH.','Personal, turnos, reglas, bonos y medidas'),('Supervisor','Valida marcas y audita inconsistencias'),
 ('Colaborador','Marca por contingencia y consulta su historial');
INSERT INTO area (nombre, estado) VALUES ('Administración',1),('Velatorio',1),('Traslados',1),('Atención al cliente',1);
INSERT INTO cargo (nombre, estado) VALUES ('Jefe de RR. HH.',1),('Supervisor',1),('Asesor funerario',1),('Conductor',1),('Personal de velatorio',1),('Gerente',1);
INSERT INTO horario (nombre, hora_entrada, hora_salida, tolerancia_min, es_guardia_24h) VALUES
 ('Mañana','08:00:00','16:00:00',10,0),('Tarde','14:00:00','22:00:00',10,0),('Guardia 24 h','08:00:00','08:00:00',10,1),('Administrativo','09:00:00','18:00:00',5,0);
INSERT INTO reloj_biometrico (nombre, ip, puerto, activo) VALUES ('Reloj sede principal','192.168.1.201',4370,1);
-- Usuario inicial: admin / Asistencia2026 (contraseña cifrada con bcrypt). Cámbiela en el primer ingreso.
INSERT INTO usuario (id_perfil, username, password_hash, estado, intentos_fallidos, creado_en)
 VALUES ((SELECT id_perfil FROM perfil WHERE nombre='Administrador'), 'admin', '$2b$12$m4z1vCE1766./DdF8O7dUuTcYuwUFzx5JOm3ElKGPKWMv6.2focEO', 'ACTIVO', 0, NOW());
INSERT INTO regla_negocio (tolerancia_min, monto_bono, max_tardanzas_bono, tardanzas_alerta, faltas_alerta, vigencia_desde, vigente, id_usuario)
 VALUES (10, 150.00, 0, 3, 2, '2026-01-01', 1, (SELECT id_usuario FROM usuario WHERE username='admin'));
