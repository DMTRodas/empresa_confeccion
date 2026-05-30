-- Ejecuta esto y dime qué ves:
SELECT table_name FROM user_tables;
SELECT column_name FROM user_tab_columns WHERE table_name = 'INVENTARIO';
SELECT column_name FROM user_tab_columns WHERE table_name = 'PRODUCTO';

SELECT * FROM user_tables;

-- ==========================================
-- CONECTAR PRIMERO como empresa_confeccion
-- ==========================================
-- En SQL Developer: 
-- Usuario: empresa_confeccion
-- Contraseña: empresa123
-- Puerto: 1521
-- SID: XE

-- ==========================================
-- CREAR TODAS LAS TABLAS
-- ==========================================

-- 1. Tabla PAIS
CREATE TABLE pais (
    pais_id NUMBER PRIMARY KEY,
    nombre VARCHAR2(100) NOT NULL,
    codigo_iso VARCHAR2(3),
    moneda VARCHAR2(50)
);

-- 2. Tabla SEDE
CREATE TABLE sede (
    sede_id NUMBER PRIMARY KEY,
    pais_id NUMBER NOT NULL,
    nombre VARCHAR2(100) NOT NULL,
    direccion VARCHAR2(200),
    tipo VARCHAR2(50),
    capacidad_almacenaje NUMBER,
    telefono VARCHAR2(20),
    email VARCHAR2(100)
);

-- 3. Tabla CATEGORIA_PRODUCTO
CREATE TABLE categoria_producto (
    categoria_id NUMBER PRIMARY KEY,
    nombre VARCHAR2(50) NOT NULL,
    descripcion VARCHAR2(200)
);

-- 4. Tabla PRODUCTO
CREATE TABLE producto (
    producto_id NUMBER PRIMARY KEY,
    categoria_id NUMBER NOT NULL,
    nombre VARCHAR2(100) NOT NULL,
    descripcion VARCHAR2(300),
    unidad_medida VARCHAR2(20) NOT NULL,
    precio_unitario_usd NUMBER(10,2),
    es_materia_prima NUMBER(1) DEFAULT 1,
    activo NUMBER(1) DEFAULT 1
);

-- 5. Tabla INVENTARIO
CREATE TABLE inventario (
    inventario_id NUMBER PRIMARY KEY,
    sede_id NUMBER NOT NULL,
    producto_id NUMBER NOT NULL,
    cantidad_disponible NUMBER(10,2) DEFAULT 0,
    cantidad_reservada NUMBER(10,2) DEFAULT 0,
    punto_reorden NUMBER(10,2) DEFAULT 0,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Tabla CLIENTE
CREATE TABLE cliente (
    cliente_id NUMBER PRIMARY KEY,
    nombre_empresa VARCHAR2(150) NOT NULL,
    contacto_principal VARCHAR2(100),
    email VARCHAR2(100),
    telefono VARCHAR2(20),
    direccion VARCHAR2(200),
    contrasena VARCHAR2(100),
    activo NUMBER(1) DEFAULT 1
);

-- 7. Tabla EMPLEADO
CREATE TABLE empleado (
    empleado_id NUMBER PRIMARY KEY,
    sede_id NUMBER NOT NULL,
    nombre VARCHAR2(100) NOT NULL,
    puesto VARCHAR2(50) NOT NULL,
    email VARCHAR2(100),
    telefono VARCHAR2(20),
    usuario VARCHAR2(50) UNIQUE,
    contrasena VARCHAR2(100),
    activo NUMBER(1) DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Tabla ORDEN
CREATE TABLE orden (
    orden_id NUMBER PRIMARY KEY,
    tipo VARCHAR2(20) NOT NULL,
    estado VARCHAR2(30) NOT NULL,
    cliente_id NUMBER,
    sede_id NUMBER NOT NULL,
    empleado_responsable NUMBER NOT NULL,
    subtotal NUMBER(10,2),
    total NUMBER(10,2),
    observaciones VARCHAR2(500),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_estimada DATE,
    fecha_completacion TIMESTAMP
);

-- 9. Tabla ORDEN_DETALLE
CREATE TABLE orden_detalle (
    detalle_id NUMBER PRIMARY KEY,
    orden_id NUMBER NOT NULL,
    producto_id NUMBER NOT NULL,
    cantidad NUMBER(10,2) NOT NULL,
    precio_unitario NUMBER(10,2),
    subtotal NUMBER(10,2)
);

-- 10. Tabla MOVIMIENTO_MATERIA_PRIMA
CREATE TABLE movimiento_materia_prima (
    movimiento_id NUMBER PRIMARY KEY,
    producto_id NUMBER NOT NULL,
    cantidad NUMBER(10,2) NOT NULL,
    sede_origen_id NUMBER NOT NULL,
    sede_destino_id NUMBER NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_estimada_entrega DATE,
    fecha_real_entrega TIMESTAMP,
    estado VARCHAR2(20) NOT NULL,
    empleado_responsable NUMBER NOT NULL
);

-- ==========================================
-- CREAR SECUENCIAS
-- ==========================================
CREATE SEQUENCE seq_pais START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_sede START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_categoria_producto START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_producto START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_inventario START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_cliente START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_empleado START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_orden START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_orden_detalle_id START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_movimiento START WITH 1 INCREMENT BY 1;

-- ==========================================
-- AGREGAR LLAVES FORÁNEAS
-- ==========================================
ALTER TABLE sede ADD CONSTRAINT fk_sede_pais FOREIGN KEY (pais_id) REFERENCES pais(pais_id);
ALTER TABLE producto ADD CONSTRAINT fk_producto_categoria FOREIGN KEY (categoria_id) REFERENCES categoria_producto(categoria_id);
ALTER TABLE inventario ADD CONSTRAINT fk_inventario_sede FOREIGN KEY (sede_id) REFERENCES sede(sede_id);
ALTER TABLE inventario ADD CONSTRAINT fk_inventario_producto FOREIGN KEY (producto_id) REFERENCES producto(producto_id);
ALTER TABLE orden ADD CONSTRAINT fk_orden_cliente FOREIGN KEY (cliente_id) REFERENCES cliente(cliente_id);
ALTER TABLE orden ADD CONSTRAINT fk_orden_sede FOREIGN KEY (sede_id) REFERENCES sede(sede_id);
ALTER TABLE orden ADD CONSTRAINT fk_orden_empleado FOREIGN KEY (empleado_responsable) REFERENCES empleado(empleado_id);
ALTER TABLE orden_detalle ADD CONSTRAINT fk_detalle_orden FOREIGN KEY (orden_id) REFERENCES orden(orden_id);
ALTER TABLE orden_detalle ADD CONSTRAINT fk_detalle_producto FOREIGN KEY (producto_id) REFERENCES producto(producto_id);
ALTER TABLE movimiento_materia_prima ADD CONSTRAINT fk_movimiento_producto FOREIGN KEY (producto_id) REFERENCES producto(producto_id);
ALTER TABLE movimiento_materia_prima ADD CONSTRAINT fk_movimiento_origen FOREIGN KEY (sede_origen_id) REFERENCES sede(sede_id);
ALTER TABLE movimiento_materia_prima ADD CONSTRAINT fk_movimiento_destino FOREIGN KEY (sede_destino_id) REFERENCES sede(sede_id);
ALTER TABLE movimiento_materia_prima ADD CONSTRAINT fk_movimiento_empleado FOREIGN KEY (empleado_responsable) REFERENCES empleado(empleado_id);

-- ==========================================
-- INSERTAR DATOS DE PRUEBA
-- ==========================================

-- Países
INSERT INTO pais (pais_id, nombre, codigo_iso, moneda) VALUES (seq_pais.NEXTVAL, 'Guatemala', 'GTM', 'Quetzal');
INSERT INTO pais (pais_id, nombre, codigo_iso, moneda) VALUES (seq_pais.NEXTVAL, 'México', 'MEX', 'Peso Mexicano');

-- Sedes
INSERT INTO sede (sede_id, pais_id, nombre, direccion, tipo) VALUES (seq_sede.NEXTVAL, 1, 'Fábrica Central GTM', 'Ciudad de Guatemala', 'fabrica');
INSERT INTO sede (sede_id, pais_id, nombre, direccion, tipo) VALUES (seq_sede.NEXTVAL, 1, 'Taller Norte GTM', 'Alta Verapaz', 'fabrica');

-- Categorías
INSERT INTO categoria_producto (categoria_id, nombre, descripcion) VALUES (seq_categoria_producto.NEXTVAL, 'Producto Final', 'Productos terminados para la venta');
INSERT INTO categoria_producto (categoria_id, nombre, descripcion) VALUES (seq_categoria_producto.NEXTVAL, 'Materia Prima', 'Materiales para producción');

-- Productos
INSERT INTO producto (producto_id, categoria_id, nombre, unidad_medida, precio_unitario_usd, es_materia_prima, activo) 
VALUES (seq_producto.NEXTVAL, 2, 'Tela Algodón', 'Metros', 5.50, 1, 1);

INSERT INTO producto (producto_id, categoria_id, nombre, unidad_medida, precio_unitario_usd, es_materia_prima, activo) 
VALUES (seq_producto.NEXTVAL, 2, 'Hilo Poliéster', 'Bobinas', 1.20, 1, 1);

INSERT INTO producto (producto_id, categoria_id, nombre, unidad_medida, precio_unitario_usd, es_materia_prima, activo) 
VALUES (seq_producto.NEXTVAL, 1, 'Camiseta Básica', 'Unidades', 15.00, 0, 1);

INSERT INTO producto (producto_id, categoria_id, nombre, unidad_medida, precio_unitario_usd, es_materia_prima, activo) 
VALUES (seq_producto.NEXTVAL, 1, 'Pantalón Casual', 'Unidades', 25.00, 0, 1);

-- Empleados (IMPORTANTE: el admin smiron)
INSERT INTO empleado (empleado_id, sede_id, nombre, puesto, usuario, contrasena, activo) 
VALUES (seq_empleado.NEXTVAL, 1, 'Stefano Miron', 'admin', 'smiron', 'contra123', 1);

INSERT INTO empleado (empleado_id, sede_id, nombre, puesto, usuario, contrasena, activo) 
VALUES (seq_empleado.NEXTVAL, 1, 'Ana Mancio', 'vendedor', 'amancio', 'contra123', 1);

-- Clientes
INSERT INTO cliente (cliente_id, nombre_empresa, contacto_principal, email, contrasena, activo) 
VALUES (seq_cliente.NEXTVAL, 'Eco Moda', 'Beatriz Pinzon', 'info@ecomoda.com', 'cliente123', 1);

INSERT INTO cliente (cliente_id, nombre_empresa, contacto_principal, email, contrasena, activo) 
VALUES (seq_cliente.NEXTVAL, 'Novo', 'Sofia Armas', 'ventas@novo.com', 'cliente123', 1);

-- Inventario
INSERT INTO inventario (inventario_id, sede_id, producto_id, cantidad_disponible, punto_reorden) 
VALUES (seq_inventario.NEXTVAL, 1, 1, 1000, 100);

INSERT INTO inventario (inventario_id, sede_id, producto_id, cantidad_disponible, punto_reorden) 
VALUES (seq_inventario.NEXTVAL, 1, 2, 500, 50);

INSERT INTO inventario (inventario_id, sede_id, producto_id, cantidad_disponible, punto_reorden) 
VALUES (seq_inventario.NEXTVAL, 1, 3, 200, 20);

INSERT INTO inventario (inventario_id, sede_id, producto_id, cantidad_disponible, punto_reorden) 
VALUES (seq_inventario.NEXTVAL, 1, 4, 150, 15);

-- Orden de prueba
INSERT INTO orden (orden_id, tipo, estado, cliente_id, sede_id, empleado_responsable, subtotal, total) 
VALUES (seq_orden.NEXTVAL, 'VENTA', 'pendiente', 1, 1, 1, 100, 100);

-- Detalle de orden
INSERT INTO orden_detalle (detalle_id, orden_id, producto_id, cantidad, precio_unitario, subtotal) 
VALUES (seq_orden_detalle_id.NEXTVAL, 1, 3, 5, 15.00, 75.00);

INSERT INTO orden_detalle (detalle_id, orden_id, producto_id, cantidad, precio_unitario, subtotal) 
VALUES (seq_orden_detalle_id.NEXTVAL, 1, 4, 1, 25.00, 25.00);

-- Movimiento de prueba
INSERT INTO movimiento_materia_prima (movimiento_id, producto_id, cantidad, sede_origen_id, sede_destino_id, estado, empleado_responsable) 
VALUES (seq_movimiento.NEXTVAL, 1, 50, 1, 2, 'entregado', 1);

COMMIT;

-- ==========================================
-- VERIFICACION
-- ==========================================

SELECT * FROM producto;

SELECT * FROM cliente;

SELECT * FROM orden;

SELECT * FROM inventario;

SELECT * FROM sede;








































