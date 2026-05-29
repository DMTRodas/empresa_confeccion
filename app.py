import oracledb 
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'empresa_confeccion_secret_key_2024'

def get_db_connection():
    try:
        dsn = oracledb.makedsn('localhost', '1521', service_name='XE')
        connection = oracledb.connect(
            user='empresa_confeccion', 
            password='empresa123', 
            dsn=dsn
        )
        return connection
    except Exception as e:
        print(f"❌ Error de conexión a Oracle: {e}")
        flash(f'Error de conexión a la base de datos: {str(e)}', 'error')
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        contrasena = request.form['contrasena']
       
        print(f"🔐 Login inteligente: '{usuario}'")
        
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión a la base de datos', 'error')
            return render_template('login.html')
        
        try:
            cursor = conn.cursor()
            
            # PRIMERO: Buscar como EMPLEADO (incluye admins)
            cursor.execute("""
                SELECT e.empleado_id, e.nombre, e.puesto, e.usuario, s.nombre as sede
                FROM empleado e
                JOIN sede s ON e.sede_id = s.sede_id
                WHERE (e.usuario = :usuario OR e.email = :usuario) 
                AND e.contrasena = :contrasena 
                AND e.activo = 1
            """, usuario=usuario, contrasena=contrasena)
            
            empleado = cursor.fetchone()
            
            if empleado:
                session['user_id'] = empleado[0]
                session['user_nombre'] = empleado[1]
                session['user_puesto'] = empleado[2]
                session['user_sede'] = empleado[4]
                session['user_type'] = 'empleado'
                
                print(f"Empleado encontrado: {empleado[1]} - Puesto: {empleado[2]}")
                
                if empleado[2] == 'admin':
                    flash('¡Bienvenido al Panel de Administración!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash(f'👨‍💼 ¡Bienvenido {empleado[1]}!', 'success')
                    return redirect(url_for('empleado_portal'))
            
            cursor.execute("""
                SELECT cliente_id, nombre_empresa, contacto_principal, email
                FROM cliente 
                WHERE (email = :usuario OR contacto_principal = :usuario) 
                AND contrasena = :contrasena 
                AND activo = 1
            """, usuario=usuario, contrasena=contrasena)
            
            cliente = cursor.fetchone()
            
            if cliente:
                session['user_id'] = cliente[0]
                session['user_nombre'] = cliente[1]
                session['user_contacto'] = cliente[2]
                session['user_email'] = cliente[3]
                session['user_type'] = 'cliente'
                
                flash(f'👥 ¡Bienvenido {cliente[1]}!', 'success')
                return redirect(url_for('cliente_portal'))

            flash('Usuario o contraseña incorrectos', 'error')
            print(f"Login falló para: {usuario}")
            
        except Exception as e:
            flash(f'Error en el login: {str(e)}', 'error')
            print(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('admin/dashboard.html')
    
    try:
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM producto WHERE activo = 1")
        stats['total_productos'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM cliente WHERE activo = 1")
        stats['total_clientes'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM empleado WHERE activo = 1")
        stats['total_empleados'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sede")
        stats['total_sedes'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM orden 
            WHERE estado IN ('pendiente', 'confirmada', 'en_produccion')
        """)
        stats['ordenes_activas'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT SUM(i.cantidad_disponible * p.precio_unitario_usd)
            FROM inventario i
            JOIN producto p ON i.producto_id = p.producto_id
        """)
        stats['valor_inventario'] = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT 
                o.orden_id, 
                o.tipo, 
                o.estado, 
                c.nombre_empresa,
                o.fecha_creacion,
                o.total,
                -- Información de productos (primer producto como ejemplo)
                (SELECT p.nombre FROM orden_detalle od 
                JOIN producto p ON od.producto_id = p.producto_id 
                WHERE od.orden_id = o.orden_id AND ROWNUM = 1) as producto_ejemplo,
                (SELECT SUM(od.cantidad) FROM orden_detalle od 
                WHERE od.orden_id = o.orden_id) as cantidad_total
            FROM orden o
            LEFT JOIN cliente c ON o.cliente_id = c.cliente_id
            ORDER BY o.fecha_creacion DESC
            FETCH FIRST 5 ROWS ONLY
        """)
        
        ordenes_recientes = []
        for row in cursor:
            ordenes_recientes.append({
                'id': row[0], 
                'tipo': row[1], 
                'estado': row[2],
                'cliente': row[3] or 'N/A', 
                'producto': row[6] or 'Múltiples productos',  
                'cantidad': row[7] or 0,  
                'fecha': row[4],
                'total': float(row[5]) if row[5] else 0
            })
        
        cursor.close()
        conn.close()
        
        return render_template('admin/dashboard.html', 
                             stats=stats, 
                             ordenes_recientes=ordenes_recientes)
                             
    except Exception as e:
        flash(f'Error al cargar dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html')

@app.route('/admin/productos')
def admin_productos():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        return render_template('admin/productos.html', productos=[], sedes=[])

    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.PRODUCTO_ID, p.NOMBRE, p.DESCRIPCION, p.PRECIO_UNITARIO_USD,
                   c.NOMBRE as CATEGORIA, p.ES_MATERIA_PRIMA, p.ACTIVO,
                   p.UNIDAD_MEDIDA
            FROM PRODUCTO p
            JOIN CATEGORIA_PRODUCTO c ON p.CATEGORIA_ID = c.CATEGORIA_ID
            ORDER BY p.PRODUCTO_ID
        """)
        
        productos = []
        for row in cursor:
            productos.append({
                'id': row[0], 
                'nombre': row[1], 
                'descripcion': row[2],
                'precio': row[3], 
                'categoria': row[4],
                'es_materia_prima': 'Sí' if row[5] == 1 else 'No',
                'activo': '✅' if row[6] == 1 else '❌',
                'unidad': row[7]
            })

        cursor.execute("SELECT sede_id, nombre FROM sede ORDER BY nombre")
        sedes = [{'id': row[0], 'nombre': row[1]} for row in cursor]

        cursor.close()
        conn.close()
        return render_template('admin/productos.html', productos=productos, sedes=sedes)

    except Exception as e:
        flash(f'Error al cargar productos: {str(e)}', 'error')
        return render_template('admin/productos.html', productos=[], sedes=[])
    

@app.route('/admin/productos/crear', methods=['POST'])
def crear_producto():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT SEQ_PRODUCTO.NEXTVAL FROM DUAL")
        producto_id = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT CATEGORIA_ID FROM CATEGORIA_PRODUCTO 
            WHERE NOMBRE = :categoria
        """, categoria=data['categoria'])
        
        categoria_result = cursor.fetchone()
        if not categoria_result:
            return jsonify({'success': False, 'error': 'Categoría no válida'}), 400
            
        categoria_id = categoria_result[0]
        
        cursor.execute("""
            INSERT INTO PRODUCTO (
                PRODUCTO_ID, CATEGORIA_ID, NOMBRE, DESCRIPCION, 
                UNIDAD_MEDIDA, PRECIO_UNITARIO_USD, ES_MATERIA_PRIMA, ACTIVO
            ) VALUES (
                :id, :categoria_id, :nombre, :descripcion, 
                :unidad_medida, :precio, :es_materia_prima, :activo
            )
        """, 
            id=producto_id,
            categoria_id=categoria_id,
            nombre=data['nombre'],
            descripcion=data.get('descripcion', ''),
            unidad_medida=data['unidad_medida'],
            precio=float(data['precio']),
            es_materia_prima=1 if data.get('es_materia_prima') else 0,
            activo=1 if data.get('activo', True) else 0
        )
        
        sede_id = data.get('sede_id')
        stock_inicial = data.get('stock_inicial', 0)
        
        if sede_id and stock_inicial is not None:
            cursor.execute("SELECT SEQ_INVENTARIO.NEXTVAL FROM DUAL")
            inventario_id = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO INVENTARIO (
                    INVENTARIO_ID, SEDE_ID, PRODUCTO_ID, 
                    CANTIDAD_DISPONIBLE, CANTIDAD_RESERVADA, PUNTO_REORDEN
                ) VALUES (
                    :id, :sede_id, :producto_id, :cantidad, 0, 10
                )
            """, 
                id=inventario_id,
                sede_id=int(sede_id),
                producto_id=producto_id,
                cantidad=int(stock_inicial)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'producto_id': producto_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/productos/<int:producto_id>/editar', methods=['POST'])
def editar_producto(producto_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT CATEGORIA_ID FROM CATEGORIA_PRODUCTO 
            WHERE NOMBRE = :categoria
        """, categoria=data['categoria'])
        
        categoria_result = cursor.fetchone()
        if not categoria_result:
            return jsonify({'success': False, 'error': 'Categoría no válida'}), 400
            
        categoria_id = categoria_result[0]
        
        cursor.execute("""
            UPDATE PRODUCTO 
            SET NOMBRE = :nombre,
                DESCRIPCION = :descripcion,
                UNIDAD_MEDIDA = :unidad_medida,
                PRECIO_UNITARIO_USD = :precio,
                CATEGORIA_ID = :categoria_id,
                ES_MATERIA_PRIMA = :es_materia_prima,
                ACTIVO = :activo
            WHERE PRODUCTO_ID = :id
        """, 
            nombre=data['nombre'],
            descripcion=data.get('descripcion', ''),
            unidad_medida=data['unidad_medida'],
            precio=float(data['precio']),
            categoria_id=categoria_id,
            es_materia_prima=1 if data.get('es_materia_prima') else 0,
            activo=1 if data.get('activo', True) else 0,
            id=producto_id
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/productos/<int:producto_id>/eliminar', methods=['POST'])
def eliminar_producto(producto_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"Intentando eliminar producto ID: {producto_id}")
        
        cursor.execute("SELECT COUNT(*) FROM PRODUCTO WHERE PRODUCTO_ID = :id", id=producto_id)
        if cursor.fetchone()[0] == 0:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
        
        cursor.execute("SELECT COUNT(*) FROM ORDEN_DETALLE WHERE PRODUCTO_ID = :id", id=producto_id)
        ordenes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM INVENTARIO WHERE PRODUCTO_ID = :id", id=producto_id)
        inventario_count = cursor.fetchone()[0]
        
        print(f"Órdenes en detalle: {ordenes_count}, Inventario: {inventario_count}")
        
        if ordenes_count > 0 or inventario_count > 0:
            cursor.execute("UPDATE PRODUCTO SET ACTIVO = 0 WHERE PRODUCTO_ID = :id", id=producto_id)
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': f'Producto desactivado. Tiene {ordenes_count} órdenes y {inventario_count} registros de inventario.',
                'desactivado': True
            })
        
        cursor.execute("DELETE FROM PRODUCTO WHERE PRODUCTO_ID = :id", id=producto_id)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Producto eliminado correctamente'})
        
    except Exception as e:
        print(f"Error completo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/productos/<int:producto_id>')
def obtener_producto(producto_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.PRODUCTO_ID, p.NOMBRE, p.DESCRIPCION, p.PRECIO_UNITARIO_USD,
                   c.NOMBRE as CATEGORIA, p.ES_MATERIA_PRIMA, p.ACTIVO, p.UNIDAD_MEDIDA
            FROM PRODUCTO p
            JOIN CATEGORIA_PRODUCTO c ON p.CATEGORIA_ID = c.CATEGORIA_ID
            WHERE p.PRODUCTO_ID = :id
        """, id=producto_id)
        
        producto = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if producto:
            return jsonify({
                'success': True,
                'producto': {
                    'id': producto[0],
                    'nombre': producto[1],
                    'descripcion': producto[2] or '',
                    'precio': float(producto[3]),
                    'categoria': producto[4],
                    'es_materia_prima': bool(producto[5]),
                    'activo': bool(producto[6]),
                    'unidad_medida': producto[7]
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/clientes')
def admin_clientes():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('admin/clientes.html', clientes=[])
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cliente_id, nombre_empresa, contacto_principal, 
                   telefono, email, direccion, activo
            FROM cliente 
            ORDER BY nombre_empresa
        """)
        
        clientes = []
        for row in cursor:
            clientes.append({
                'id': row[0], 'empresa': row[1], 'contacto': row[2],
                'telefono': row[3], 'email': row[4], 'direccion': row[5],
                'activo': '✅' if row[6] == 1 else '❌'
            })
        
        cursor.close()
        conn.close()
        
        return render_template('admin/clientes.html', clientes=clientes)
        
    except Exception as e:
        flash(f'Error al cargar clientes: {str(e)}', 'error')
        return render_template('admin/clientes.html', clientes=[])
    
@app.route('/admin/clientes/crear', methods=['POST'])
def crear_cliente():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute("SELECT seq_cliente.NEXTVAL FROM DUAL")
        cliente_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO cliente (cliente_id, nombre_empresa, contacto_principal, 
                               email, telefono, direccion, activo)
            VALUES (:id, :empresa, :contacto, :email, :telefono, :direccion, 1)
        """, 
            id=cliente_id,
            empresa=data['empresa'],
            contacto=data['contacto'],
            email=data.get('email', ''),
            telefono=data.get('telefono', ''),
            direccion=data.get('direccion', '')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'cliente_id': cliente_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/clientes/<int:id>')
def obtener_cliente(id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cliente_id, nombre_empresa, contacto_principal, 
                   telefono, email, direccion, activo
            FROM cliente 
            WHERE cliente_id = :id
        """, id=id)
        
        cliente = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if cliente:
            return jsonify({
                'success': True, 
                'cliente': {
                    'id': cliente[0],
                    'empresa': cliente[1],
                    'contacto': cliente[2],
                    'telefono': cliente[3],
                    'email': cliente[4],
                    'direccion': cliente[5],
                    'activo': cliente[6]
                }
            })
        return jsonify({'success': False, 'error': 'Cliente no encontrado'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/clientes/<int:id>/editar', methods=['POST'])
def editar_cliente(id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT cliente_id FROM cliente WHERE cliente_id = :id", id=id)
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Cliente no encontrada'}), 404
        
        cursor.execute("""
            UPDATE cliente SET 
                nombre_empresa = :empresa,
                contacto_principal = :contacto,
                telefono = :telefono,
                email = :email,
                direccion = :direccion
            WHERE cliente_id = :id
        """, 
            id=id,
            empresa=data['empresa'],
            contacto=data['contacto'],
            telefono=data.get('telefono', ''),
            email=data.get('email', ''),
            direccion=data.get('direccion', '')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
    

@app.route('/admin/clientes/<int:id>/eliminar', methods=['POST'])
def eliminar_cliente(id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT cliente_id FROM cliente WHERE cliente_id = :id", id=id)
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Cliente no encontrado'}), 404
        
        cursor.execute("""
            UPDATE cliente SET activo = 0 WHERE cliente_id = :id
        """, id=id)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/admin/inventario/<int:inventario_id>/ajustar', methods=['POST'])
def ajustar_inventario(inventario_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE INVENTARIO 
            SET CANTIDAD_DISPONIBLE = :nuevo_stock
            WHERE INVENTARIO_ID = :id
        """, 
            nuevo_stock=data['nuevo_stock'],
            id=inventario_id
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/admin/inventario/transferir', methods=['POST'])
def transferir_stock():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.CANTIDAD_DISPONIBLE, i.PRODUCTO_ID, i.SEDE_ID, 
                   p.NOMBRE as PRODUCTO_NOMBRE, s.NOMBRE as SEDE_ORIGEN_NOMBRE
            FROM INVENTARIO i
            JOIN PRODUCTO p ON i.PRODUCTO_ID = p.PRODUCTO_ID
            JOIN SEDE s ON i.SEDE_ID = s.SEDE_ID
            WHERE i.INVENTARIO_ID = :origen_id
        """, origen_id=data['origen_id'])
        
        resultado = cursor.fetchone()
        stock_disponible = resultado[0]
        producto_id = resultado[1]
        sede_origen_id = resultado[2]
        producto_nombre = resultado[3]
        sede_origen_nombre = resultado[4]
        
        if stock_disponible < data['cantidad']:
            return jsonify({
                'success': False, 
                'error': f'Stock insuficiente. Disponible: {stock_disponible}'
            }), 400
        
        cursor.execute("""
            SELECT SEDE_ID, NOMBRE FROM SEDE WHERE NOMBRE = :sede_destino
        """, sede_destino=data['sede_destino'])
        
        sede_destino_result = cursor.fetchone()
        if not sede_destino_result:
            return jsonify({'success': False, 'error': 'Sede destino no encontrada'}), 400
            
        sede_destino_id = sede_destino_result[0]
        sede_destino_nombre = sede_destino_result[1]
        
        cursor.execute("""
            SELECT INVENTARIO_ID, CANTIDAD_DISPONIBLE 
            FROM INVENTARIO 
            WHERE SEDE_ID = :sede_id AND PRODUCTO_ID = :producto_id
        """, sede_id=sede_destino_id, producto_id=producto_id)
        
        destino = cursor.fetchone()
        
        if destino:
            inventario_destino_id = destino[0]
            cursor.execute("""
                UPDATE INVENTARIO 
                SET CANTIDAD_DISPONIBLE = CANTIDAD_DISPONIBLE + :cantidad
                WHERE INVENTARIO_ID = :destino_id
            """, cantidad=data['cantidad'], destino_id=inventario_destino_id)
        else:
            cursor.execute("SELECT SEQ_INVENTARIO.NEXTVAL FROM DUAL")
            inventario_destino_id = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO INVENTARIO (
                    INVENTARIO_ID, SEDE_ID, PRODUCTO_ID, 
                    CANTIDAD_DISPONIBLE, CANTIDAD_RESERVADA, PUNTO_REORDEN
                ) VALUES (
                    :id, :sede_id, :producto_id, :cantidad, 0, 10
                )
            """, 
                id=inventario_destino_id,
                sede_id=sede_destino_id,
                producto_id=producto_id,
                cantidad=data['cantidad']
            )
    
        cursor.execute("""
            UPDATE INVENTARIO 
            SET CANTIDAD_DISPONIBLE = CANTIDAD_DISPONIBLE - :cantidad
            WHERE INVENTARIO_ID = :origen_id
        """, cantidad=data['cantidad'], origen_id=data['origen_id'])
        
        cursor.execute("SELECT SEQ_MOVIMIENTO.NEXTVAL FROM DUAL")
        movimiento_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO MOVIMIENTO_MATERIA_PRIMA (
                MOVIMIENTO_ID, PRODUCTO_ID, CANTIDAD,
                SEDE_ORIGEN_ID, SEDE_DESTINO_ID, ESTADO,
                EMPLEADO_RESPONSABLE
            ) VALUES (
                :movimiento_id, :producto_id, :cantidad,
                :sede_origen_id, :sede_destino_id, 'entregado',
                :empleado_id
            )
        """,
            movimiento_id=movimiento_id,
            producto_id=producto_id,
            cantidad=data['cantidad'],
            sede_origen_id=sede_origen_id,
            sede_destino_id=sede_destino_id,
            empleado_id=session['user_id']
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Transferencia completada: {data["cantidad"]} unidades de {producto_nombre} de {sede_origen_nombre} a {sede_destino_nombre}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/inventario/<int:inventario_id>/historial')
def obtener_historial_inventario(inventario_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.PRODUCTO_ID, i.SEDE_ID, p.NOMBRE, s.NOMBRE
            FROM INVENTARIO i
            JOIN PRODUCTO p ON i.PRODUCTO_ID = p.PRODUCTO_ID
            JOIN SEDE s ON i.SEDE_ID = s.SEDE_ID
            WHERE i.INVENTARIO_ID = :inventario_id
        """, inventario_id=inventario_id)
        
        info_inventario = cursor.fetchone()
        if not info_inventario:
            return jsonify({'success': False, 'error': 'Inventario no encontrado'}), 404
            
        producto_id = info_inventario[0]
        sede_id = info_inventario[1]
        producto_nombre = info_inventario[2]
        sede_nombre = info_inventario[3]
    
        cursor.execute("""
            SELECT m.MOVIMIENTO_ID, m.CANTIDAD, m.ESTADO,
                   TO_CHAR(m.FECHA_CREACION, 'DD/MM/YYYY HH24:MI'),
                   so.NOMBRE as SEDE_ORIGEN, 
                   sd.NOMBRE as SEDE_DESTINO,
                   e.NOMBRE as EMPLEADO
            FROM MOVIMIENTO_MATERIA_PRIMA m
            JOIN SEDE so ON m.SEDE_ORIGEN_ID = so.SEDE_ID
            JOIN SEDE sd ON m.SEDE_DESTINO_ID = sd.SEDE_ID
            JOIN EMPLEADO e ON m.EMPLEADO_RESPONSABLE = e.EMPLEADO_ID
            WHERE m.PRODUCTO_ID = :producto_id
            ORDER BY m.FECHA_CREACION DESC
        """, producto_id=producto_id)
        
        movimientos = []
        for row in cursor:
            tipo = 'TRANSFERENCIA' if row[4] != row[5] else 'AJUSTE'
            movimientos.append({
                'id': row[0],
                'tipo': tipo,
                'cantidad': row[1],
                'estado': row[2],
                'fecha': row[3],
                'sede_origen': row[4],
                'sede_destino': row[5],
                'empleado': row[6]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'movimientos': movimientos,
            'producto': producto_nombre,
            'sede': sede_nombre
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/admin/inventario')
def admin_inventario():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        return render_template('admin/inventario.html', inventario=[], sedes_unique=[], categorias_unique=[])

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.INVENTARIO_ID, s.NOMBRE as SEDE, p.NOMBRE as PRODUCTO,
                   i.CANTIDAD_DISPONIBLE, i.CANTIDAD_RESERVADA, i.PUNTO_REORDEN,
                   p.PRECIO_UNITARIO_USD, c.NOMBRE as CATEGORIA
            FROM INVENTARIO i
            JOIN SEDE s ON i.SEDE_ID = s.SEDE_ID
            JOIN PRODUCTO p ON i.PRODUCTO_ID = p.PRODUCTO_ID
            JOIN CATEGORIA_PRODUCTO c ON p.CATEGORIA_ID = c.CATEGORIA_ID
            ORDER BY s.NOMBRE, p.NOMBRE
        """)
        
        inventario = []
        sedes = set()
        categorias = set()
        
        for row in cursor:
            estado = "✅ Suficiente" if row[3] > row[5] else "⚠️ Reordenar" if row[3] > 0 else "❌ Sin Stock"
            
            inventario.append({
                'id': row[0], 'sede': row[1], 'producto': row[2],
                'disponible': row[3], 'reservado': row[4], 'punto_reorden': row[5],
                'precio': row[6], 'categoria': row[7], 'estado': estado
            })
            
            sedes.add(row[1])
            categorias.add(row[7])

        cursor.close()
        conn.close()
        
        return render_template('admin/inventario.html', 
                             inventario=inventario,
                             sedes_unique=sorted(sedes),
                             categorias_unique=sorted(categorias))

    except Exception as e:
        flash(f'Error al cargar inventario: {str(e)}', 'error')
        return render_template('admin/inventario.html', inventario=[], sedes_unique=[], categorias_unique=[])
    

@app.route('/admin/ordenes')
def admin_ordenes():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    tipo_filter = request.args.get('tipo', '')
    estado_filter = request.args.get('estado', '')
    search_filter = request.args.get('search', '')
    
    conn = get_db_connection()
    if not conn:
        return render_template('admin/ordenes.html', ordenes=[])
    
    try:
        cursor = conn.cursor()

        query = """
            SELECT 
                o.orden_id, 
                o.tipo, 
                o.estado, 
                c.nombre_empresa as cliente,
                s.nombre as sede,
                e.nombre as responsable,
                o.fecha_creacion,
                o.fecha_estimada,
                o.total,
                -- Información de productos
                (SELECT COUNT(*) FROM orden_detalle od WHERE od.orden_id = o.orden_id) as cantidad_productos,
                (SELECT NVL(SUM(od.cantidad), 0) FROM orden_detalle od WHERE od.orden_id = o.orden_id) as cantidad_total,
                (SELECT LISTAGG(p.nombre, ', ') WITHIN GROUP (ORDER BY p.nombre) 
                 FROM orden_detalle od 
                 JOIN producto p ON od.producto_id = p.producto_id 
                 WHERE od.orden_id = o.orden_id) as productos_nombres
            FROM orden o
            LEFT JOIN cliente c ON o.cliente_id = c.cliente_id
            LEFT JOIN sede s ON o.sede_id = s.sede_id
            LEFT JOIN empleado e ON o.empleado_responsable = e.empleado_id
            WHERE 1=1
        """
        
        params = []
        
        if tipo_filter:
            query += " AND o.tipo = :tipo"
            params.append(tipo_filter)
        
        if estado_filter:
            query += " AND o.estado = :estado"
            params.append(estado_filter)
        
        if search_filter:
            query += """ AND (o.orden_id LIKE :search 
                          OR c.nombre_empresa LIKE :search 
                          OR o.orden_id IN (
                              SELECT od.orden_id 
                              FROM orden_detalle od 
                              JOIN producto p ON od.producto_id = p.producto_id 
                              WHERE p.nombre LIKE :search
                          ))"""
            params.append(f'%{search_filter}%')
        
        query += " ORDER BY o.fecha_creacion DESC"
        
        cursor.execute(query, params)
        
        ordenes = []
        for row in cursor:
            ordenes.append({
                'id': row[0], 
                'tipo': row[1], 
                'estado': row[2],
                'cliente': row[3] or 'N/A', 
                'sede': row[4] or 'N/A',
                'responsable': row[5] or 'N/A',
                'fecha_creacion': row[6],
                'fecha_estimada': row[7],
                'total': float(row[8]) if row[8] else 0,
                'cantidad_productos': row[9] or 0,
                'cantidad_total': float(row[10]) if row[10] else 0,
                'productos': row[11] or 'Sin productos'
            })
        
        cursor.close()
        conn.close()
        
        return render_template('admin/ordenes.html', 
                             ordenes=ordenes,
                             tipo_filter=tipo_filter,
                             estado_filter=estado_filter,
                             search_filter=search_filter)
        
    except Exception as e:
        flash(f'Error al cargar órdenes: {str(e)}', 'error')
        return render_template('admin/ordenes.html', ordenes=[])
    except Exception as e:
        flash(f'Error al cargar órdenes: {str(e)}', 'error')
        return render_template('admin/ordenes.html', ordenes=[])
    
    
@app.route('/api/ordenes/<int:orden_id>/detalles')
def api_orden_detalles(orden_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.nombre as producto,
                od.cantidad,
                od.precio_unitario,
                od.subtotal,
                p.unidad_medida
            FROM orden_detalle od
            JOIN producto p ON od.producto_id = p.producto_id
            WHERE od.orden_id = :1
        """, (orden_id,))
        
        detalles = []
        for row in cursor:
            detalles.append({
                'producto': row[0],
                'cantidad': float(row[1]) if row[1] else 0,
                'precio_unitario': float(row[2]) if row[2] else 0,
                'subtotal': float(row[3]) if row[3] else 0,
                'unidad': row[4] or 'unidades'
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(detalles)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/admin/ordenes/<int:orden_id>/actualizar-estado', methods=['POST'])
def actualizar_estado_orden(orden_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'success': False, 'error': 'Estado no proporcionado'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT orden_id, estado FROM orden WHERE orden_id = :1", (orden_id,))
        orden = cursor.fetchone()
        
        if not orden:
            return jsonify({'success': False, 'error': 'Orden no encontrada'}), 404
        
        estado_actual = orden[1]
        
        transiciones_validas = {
            'pendiente': ['confirmada', 'cancelada'],
            'confirmada': ['en_produccion', 'pendiente', 'cancelada'],
            'en_produccion': ['completada', 'confirmada'],
            'completada': [],
            'cancelada': []
        }
        
        if nuevo_estado not in transiciones_validas.get(estado_actual, []):
            return jsonify({
                'success': False, 
                'error': f'No se puede cambiar de {estado_actual} a {nuevo_estado}'
            }), 400
        
        mensaje_inventario = ""
        
        if nuevo_estado == 'confirmada' and estado_actual == 'pendiente':
            success, msg = reservar_stock_orden(orden_id)
            if not success:
                return jsonify({'success': False, 'error': msg}), 400
            mensaje_inventario = f" | {msg}"
            
        elif nuevo_estado == 'cancelada' and estado_actual == 'confirmada':
            success, msg = liberar_stock_orden(orden_id)
            if not success:
                return jsonify({'success': False, 'error': msg}), 400
            mensaje_inventario = f" | {msg}"
            
        elif nuevo_estado == 'completada' and estado_actual == 'en_produccion':
            success, msg = completar_stock_orden(orden_id)
            if not success:
                return jsonify({'success': False, 'error': msg}), 400
            mensaje_inventario = f" | {msg}"
        cursor.execute("""
            UPDATE orden 
            SET estado = :1 
            WHERE orden_id = :2
        """, (nuevo_estado, orden_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Estado actualizado a {nuevo_estado}{mensaje_inventario}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/ordenes/<int:orden_id>/cancelar', methods=['POST'])
def admin_cancelar_orden(orden_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT orden_id, estado FROM orden WHERE orden_id = :1", (orden_id,))
        orden = cursor.fetchone()
        
        if not orden:
            return jsonify({'success': False, 'error': 'Orden no encontrada'}), 404
        
        estado_actual = orden[1]
        

        mensaje_inventario = ""
        if estado_actual == 'confirmada':
            success, msg = liberar_stock_orden(orden_id)
            if not success:
                return jsonify({'success': False, 'error': msg}), 400
            mensaje_inventario = f" | {msg}"
            
        cursor.execute("""
            UPDATE orden 
            SET estado = 'cancelada' 
            WHERE orden_id = :1
        """, (orden_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Orden cancelada correctamente{mensaje_inventario}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/admin/ordenes/<int:orden_id>/verificar-stock')
def verificar_stock_orden_endpoint(orden_id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    success, message = verificar_stock_orden(orden_id)
    return jsonify({'success': success, 'message': message})
    
def reservar_stock_orden(orden_id):
    """
    Reservar stock cuando una orden se confirma
    """
    conn = get_db_connection()
    if not conn:
        return False, "Error de conexión a la base de datos"
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT od.producto_id, od.cantidad, o.sede_id
            FROM orden_detalle od
            JOIN orden o ON od.orden_id = o.orden_id
            WHERE od.orden_id = :1
        """, (orden_id,))
        
        items = cursor.fetchall()
        
        for producto_id, cantidad, sede_id in items:
            cursor.execute("""
                SELECT inventario_id, cantidad_disponible, cantidad_reservada
                FROM inventario 
                WHERE producto_id = :1 AND sede_id = :2
            """, (producto_id, sede_id))
            
            inventario = cursor.fetchone()
            
            if inventario:
                inventario_id, disponible, reservado = inventario
                
                if disponible < cantidad:
                    return False, f"Stock insuficiente para producto ID {producto_id}. Disponible: {disponible}, Requerido: {cantidad}"
                
                cursor.execute("""
                    UPDATE inventario 
                    SET cantidad_disponible = cantidad_disponible - :1,
                        cantidad_reservada = cantidad_reservada + :2
                    WHERE inventario_id = :3
                """, (cantidad, cantidad, inventario_id))
            else:
                return False, f"No hay inventario para el producto ID {producto_id} en la sede {sede_id}"
        
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Stock reservado correctamente"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error reservando stock: {str(e)}"

def liberar_stock_orden(orden_id):
    """
    Liberar stock reservado cuando una orden se cancela
    """
    conn = get_db_connection()
    if not conn:
        return False, "Error de conexión a la base de datos"
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT od.producto_id, od.cantidad, o.sede_id
            FROM orden_detalle od
            JOIN orden o ON od.orden_id = o.orden_id
            WHERE od.orden_id = :1
        """, (orden_id,))
        
        items = cursor.fetchall()
        
        for producto_id, cantidad, sede_id in items:
            cursor.execute("""
                SELECT inventario_id, cantidad_reservada
                FROM inventario 
                WHERE producto_id = :1 AND sede_id = :2
            """, (producto_id, sede_id))
            
            inventario = cursor.fetchone()
            
            if inventario:
                inventario_id, reservado = inventario
                
                if reservado < cantidad:
                    cantidad = reservado 
                

                cursor.execute("""
                    UPDATE inventario 
                    SET cantidad_disponible = cantidad_disponible + :1,
                        cantidad_reservada = cantidad_reservada - :2
                    WHERE inventario_id = :3
                """, (cantidad, cantidad, inventario_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Stock liberado correctamente"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error liberando stock: {str(e)}"

def completar_stock_orden(orden_id):
    """
    Restar stock reservado cuando una orden se completa
    """
    conn = get_db_connection()
    if not conn:
        return False, "Error de conexión a la base de datos"
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT od.producto_id, od.cantidad, o.sede_id
            FROM orden_detalle od
            JOIN orden o ON od.orden_id = o.orden_id
            WHERE od.orden_id = :1
        """, (orden_id,))
        
        items = cursor.fetchall()
        
        for producto_id, cantidad, sede_id in items:
            cursor.execute("""
                SELECT inventario_id, cantidad_reservada
                FROM inventario 
                WHERE producto_id = :1 AND sede_id = :2
            """, (producto_id, sede_id))
            
            inventario = cursor.fetchone()
            
            if inventario:
                inventario_id, reservado = inventario
                
                if reservado < cantidad:
                    cantidad = reservado 
                
                cursor.execute("""
                    UPDATE inventario 
                    SET cantidad_reservada = cantidad_reservada - :1
                    WHERE inventario_id = :2
                """, (cantidad, inventario_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Stock completado correctamente"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error completando stock: {str(e)}"
    

def verificar_stock_orden(orden_id):
    """
    Verificar si hay stock suficiente para una orden
    """
    conn = get_db_connection()
    if not conn:
        return False, "Error de conexión"
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT od.producto_id, od.cantidad, o.sede_id, p.nombre
            FROM orden_detalle od
            JOIN orden o ON od.orden_id = o.orden_id
            JOIN producto p ON od.producto_id = p.producto_id
            WHERE od.orden_id = :1
        """, (orden_id,))
        
        items = cursor.fetchall()
        problemas = []
        
        for producto_id, cantidad, sede_id, nombre_producto in items:
            cursor.execute("""
                SELECT cantidad_disponible
                FROM inventario 
                WHERE producto_id = :1 AND sede_id = :2
            """, (producto_id, sede_id))
            
            inventario = cursor.fetchone()
            
            if not inventario:
                problemas.append(f"❌ {nombre_producto}: No existe en inventario")
            else:
                disponible = inventario[0]
                if disponible < cantidad:
                    problemas.append(f"❌ {nombre_producto}: Disponible {disponible}, Requerido {cantidad}")
        
        cursor.close()
        conn.close()
        
        if problemas:
            return False, " | ".join(problemas)
        else:
            return True, "Stock suficiente disponible"
            
    except Exception as e:
        return False, f"Error verificando stock: {str(e)}"

@app.route('/admin/sedes')
def admin_sedes():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('admin/sedes.html', sedes=[], paises=[])
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.sede_id, s.nombre, p.nombre as pais, s.tipo, 
                   s.direccion, s.capacidad_almacenaje, s.telefono, s.email
            FROM sede s
            JOIN pais p ON s.pais_id = p.pais_id
            ORDER BY s.nombre
        """)
        
        sedes = []
        for row in cursor:
            sedes.append({
                'id': row[0],
                'nombre': row[1],
                'pais': row[2],
                'tipo': row[3],
                'direccion': row[4],
                'capacidad': row[5] or 0,
                'telefono': row[6],
                'email': row[7]
            })
        cursor.execute("SELECT pais_id, nombre FROM pais ORDER BY nombre")
        paises = [{'id': row[0], 'nombre': row[1]} for row in cursor]
        
        cursor.close()
        conn.close()
        
        return render_template('admin/sedes.html', sedes=sedes, paises=paises)
        
    except Exception as e:
        flash(f'Error al cargar sedes: {str(e)}', 'error')
        return render_template('admin/sedes.html', sedes=[], paises=[])
    
@app.route('/admin/sedes/<int:id>')
def obtener_sede(id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.*, p.nombre as pais_nombre 
            FROM sede s 
            LEFT JOIN pais p ON s.pais_id = p.pais_id 
            WHERE s.sede_id = :id
        """, id=id)
        
        sede = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if sede:
            return jsonify({
                'success': True, 
                'sede': {
                    'id': sede[0],
                    'pais_id': sede[1],
                    'nombre': sede[2],
                    'tipo': sede[3],
                    'direccion': sede[4],
                    'capacidad_almacenaje': sede[5],
                    'telefono': sede[6],
                    'email': sede[7]
                }
            })
        return jsonify({'success': False, 'error': 'Sede no encontrada'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/sedes/crear', methods=['POST'])
def crear_sede():
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SEQ_SEDE.NEXTVAL FROM DUAL")
        sede_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO sede (sede_id, pais_id, nombre, tipo, direccion, 
                            capacidad_almacenaje, telefono, email)
            VALUES (:id, :pais_id, :nombre, :tipo, :direccion, 
                   :capacidad, :telefono, :email)
        """, 
            id=sede_id,
            pais_id=data['pais_id'],
            nombre=data['nombre'],
            tipo=data['tipo'],
            direccion=data.get('direccion', ''),
            capacidad=data.get('capacidad_almacenaje', 0),
            telefono=data.get('telefono', ''),
            email=data.get('email', '')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'sede_id': sede_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    


@app.route('/admin/sedes/<int:id>/editar', methods=['POST'])
def editar_sede(id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT sede_id FROM sede WHERE sede_id = :id", id=id)
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Sede no encontrada'}), 404

        cursor.execute("""
            UPDATE sede SET 
                pais_id = :pais_id,
                nombre = :nombre,
                tipo = :tipo,
                direccion = :direccion,
                capacidad_almacenaje = :capacidad,
                telefono = :telefono,
                email = :email
            WHERE sede_id = :id
        """, 
            id=id,
            pais_id=data['pais_id'],
            nombre=data['nombre'],
            tipo=data['tipo'],
            direccion=data.get('direccion', ''),
            capacidad=data.get('capacidad_almacenaje', 0),
            telefono=data.get('telefono', ''),
            email=data.get('email', '')
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/sedes/<int:id>/eliminar', methods=['POST'])
def eliminar_sede(id):
    if 'user_type' not in session or session.get('user_puesto') != 'admin':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT sede_id FROM sede WHERE sede_id = :id", id=id)
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Sede no encontrada'}), 404

        cursor.execute("DELETE FROM sede WHERE sede_id = :id", id=id)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/cliente')
def cliente_portal():
    if 'user_type' not in session or session['user_type'] != 'cliente':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('cliente/portal.html', productos=[], pedidos_pendientes=0, pedidos_completados=0, pedidos_cliente=[])
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.producto_id, p.nombre, p.descripcion, p.precio_unitario_usd, 
                   c.nombre as categoria, p.unidad_medida
            FROM producto p
            JOIN categoria_producto c ON p.categoria_id = c.categoria_id
            WHERE p.es_materia_prima = 0 AND p.activo = 1
            ORDER BY p.nombre
        """)
        
        productos = []
        for row in cursor:
            productos.append({
                'id': row[0], 'nombre': row[1], 'descripcion': row[2],
                'precio': row[3], 'categoria': row[4], 'unidad': row[5]
            })

        cursor.execute("""
            SELECT 
                o.orden_id,
                o.estado,
                o.fecha_creacion,
                o.observaciones,
                o.total,
                -- Información de productos
                (SELECT LISTAGG(p.nombre, ', ') WITHIN GROUP (ORDER BY p.nombre) 
                 FROM orden_detalle od 
                 JOIN producto p ON od.producto_id = p.producto_id 
                 WHERE od.orden_id = o.orden_id) as productos_nombres,
                (SELECT SUM(od.cantidad) FROM orden_detalle od 
                 WHERE od.orden_id = o.orden_id) as cantidad_total
            FROM orden o
            WHERE o.cliente_id = :cliente_id
            ORDER BY o.fecha_creacion DESC
        """, cliente_id=session['user_id'])
        
        pedidos_cliente = []
        pedidos_pendientes = 0
        pedidos_completados = 0
        
        for row in cursor:
            pedidos_cliente.append({
                'id': row[0], 
                'estado': row[1], 
                'fecha_creacion': row[2],
                'observaciones': row[3],
                'total': float(row[4]) if row[4] else 0,
                'producto': row[5] or 'Múltiples productos', 
                'cantidad': row[6] or 0 
            })
            
            if row[1] in ['pendiente', 'confirmada', 'en_produccion']:
                pedidos_pendientes += 1
            elif row[1] == 'completada':
                pedidos_completados += 1
        
        cursor.close()
        conn.close()
        
        return render_template('cliente/portal.html', 
                             productos=productos,
                             pedidos_pendientes=pedidos_pendientes,
                             pedidos_completados=pedidos_completados,
                             pedidos_cliente=pedidos_cliente)
        
    except Exception as e:
        flash(f'Error al cargar portal: {str(e)}', 'error')
        return render_template('cliente/portal.html', productos=[], pedidos_pendientes=0, pedidos_completados=0, pedidos_cliente=[])

@app.route('/cliente/solicitar-pedido', methods=['POST'])
def solicitar_pedido():
    if 'user_type' not in session or session['user_type'] != 'cliente':
        flash('No autorizado para realizar esta acción', 'error')
        return redirect(url_for('login'))
    
    try:
        producto_id = request.form['producto_id']
        cantidad = request.form['cantidad']
        observaciones = request.form.get('observaciones', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT seq_orden.NEXTVAL FROM DUAL")
        orden_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO orden (orden_id, tipo, estado, cliente_id, sede_id, 
                             empleado_responsable, observaciones, subtotal, total)
            VALUES (:orden_id, 'VENTA', 'pendiente', :cliente_id, 1, 
                   1, :observaciones, 0, 0)
        """, orden_id=orden_id, cliente_id=session['user_id'], observaciones=observaciones)
        
        cursor.execute("""
            SELECT precio_unitario_usd FROM producto WHERE producto_id = :producto_id
        """, producto_id=producto_id)
        
        precio_result = cursor.fetchone()
        precio_unitario = precio_result[0] if precio_result else 0
        subtotal = float(cantidad) * precio_unitario
        
        cursor.execute("SELECT seq_orden_detalle_id.NEXTVAL FROM DUAL")
        detalle_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO orden_detalle (detalle_id, orden_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (:detalle_id, :orden_id, :producto_id, :cantidad, :precio_unitario, :subtotal)
        """, detalle_id=detalle_id, orden_id=orden_id, producto_id=producto_id, 
           cantidad=cantidad, precio_unitario=precio_unitario, subtotal=subtotal)

        cursor.execute("""
            UPDATE orden SET 
                subtotal = (SELECT SUM(subtotal) FROM orden_detalle WHERE orden_id = :orden_id),
                total = (SELECT SUM(subtotal) FROM orden_detalle WHERE orden_id = :orden_id)
            WHERE orden_id = :orden_id
        """, orden_id=orden_id)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('✅ Pedido solicitado correctamente. Nuestro equipo te contactará para confirmar.', 'success')
        return redirect(url_for('cliente_portal'))
        
    except Exception as e:
        flash(f'❌ Error al solicitar pedido: {str(e)}', 'error')
        return redirect(url_for('cliente_portal'))

@app.route('/cliente/cancelar-pedido/<int:orden_id>', methods=['POST'])
def cancelar_pedido(orden_id):
    if 'user_type' not in session or session['user_type'] != 'cliente':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT orden_id, estado, cliente_id 
            FROM orden 
            WHERE orden_id = :orden_id AND cliente_id = :cliente_id
        """, orden_id=orden_id, cliente_id=session['user_id'])
        
        pedido = cursor.fetchone()
        
        if not pedido:
            return jsonify({'success': False, 'error': 'Pedido no encontrado'}), 404
        
        estado_actual = pedido[1]
     
        estados_cancelables = ['pendiente', 'confirmada']
        if estado_actual not in estados_cancelables:
            return jsonify({
                'success': False, 
                'error': f'No se puede cancelar un pedido en estado "{estado_actual}"'
            }), 400

        cursor.execute("""
            UPDATE orden 
            SET estado = 'cancelada' 
            WHERE orden_id = :orden_id
        """, orden_id=orden_id)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Pedido cancelado correctamente'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/empleado')
def empleado_portal():
    if 'user_type' not in session or session['user_type'] != 'empleado':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    return render_template('empleado/portal.html')

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask con Oracle...")
    print("📊 Accede en: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)