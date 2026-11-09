"""
Aplicación de Inventario - Flask + SQLite
Una aplicación web simple para gestionar inventario de productos.
Corre en http://127.0.0.1:5001
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, g

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = 'inventory-app-secret-key-change-in-production'
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')

# Constantes
LOW_STOCK_THRESHOLD = 5  # Umbral de alerta de pocas existencias


def get_db():
    """
    Obtiene una conexión a la base de datos SQLite.
    La conexión se guarda en g (contexto de petición) para reutilizarla.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    return g.db


def close_db(e=None):
    """
    Cierra la conexión a la base de datos al final de la petición.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Inicializa la base de datos ejecutando el esquema SQL.
    Usa CREATE TABLE IF NOT EXISTS para que sea idempotente.
    Lee schema.sql con open() y encoding='utf-8' como se solicita.
    """
    db = get_db()
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    db.executescript(schema_sql)
    db.commit()


# Registrar funciones de ciclo de vida de la base de datos
app.teardown_appcontext(close_db)


@app.cli.command('init-db')
def init_db_command():
    """Comando CLI para inicializar la base de datos: flask init-db"""
    init_db()
    print('Base de datos inicializada.')


# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
def index():
    """
    Panel principal (Dashboard) con estadísticas del inventario.
    """
    db = get_db()
    
    # Total de productos
    total_products = db.execute('SELECT COUNT(*) as count FROM products').fetchone()['count']
    
    # Valor total del inventario (precio * cantidad)
    total_value_row = db.execute(
        'SELECT SUM(price * quantity) as total FROM products'
    ).fetchone()
    total_value = total_value_row['total'] if total_value_row['total'] else 0.0
    
    # Productos con pocas existencias (< 5)
    low_stock_products = db.execute(
        'SELECT * FROM products WHERE quantity < ? ORDER BY quantity ASC',
        (LOW_STOCK_THRESHOLD,)
    ).fetchall()
    
    # Categorías para el filtro en la lista de productos
    categories = db.execute(
        'SELECT DISTINCT category FROM products ORDER BY category'
    ).fetchall()
    
    return render_template(
        'index.html',
        total_products=total_products,
        total_value=total_value,
        low_stock_products=low_stock_products,
        low_stock_count=len(low_stock_products),
        categories=categories,
        LOW_STOCK_THRESHOLD=LOW_STOCK_THRESHOLD
    )


@app.route('/products')
def list_products():
    """
    Lista de productos con búsqueda por nombre y filtro por categoría.
    """
    db = get_db()
    
    # Parámetros de búsqueda y filtro
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    
    # Construir consulta dinámicamente
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if search:
        query += ' AND name LIKE ?'
        params.append(f'%{search}%')
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY name'
    
    products = db.execute(query, params).fetchall()
    
    # Obtener categorías para el filtro
    categories = db.execute(
        'SELECT DISTINCT category FROM products ORDER BY category'
    ).fetchall()
    
    return render_template(
        'products.html',
        products=products,
        categories=categories,
        search=search,
        selected_category=category,
        LOW_STOCK_THRESHOLD=LOW_STOCK_THRESHOLD
    )


@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    """
    Agregar un nuevo producto.
    GET: Muestra el formulario.
    POST: Procesa el formulario y guarda el producto.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        price = request.form.get('price', '0').strip()
        quantity = request.form.get('quantity', '0').strip()
        location = request.form.get('location', '').strip()
        
        # Validaciones básicas
        errors = []
        if not name:
            errors.append('El nombre es obligatorio.')
        if not category:
            errors.append('La categoría es obligatoria.')
        
        try:
            price = float(price)
            if price < 0:
                errors.append('El precio no puede ser negativo.')
        except ValueError:
            errors.append('El precio debe ser un número válido.')
        
        try:
            quantity = int(quantity)
            if quantity < 0:
                errors.append('La cantidad no puede ser negativa.')
        except ValueError:
            errors.append('La cantidad debe ser un número entero válido.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('product_form.html', 
                                   product=request.form, 
                                   action='add')
        
        # Insertar en base de datos
        db = get_db()
        cursor = db.execute(
            '''INSERT INTO products (name, description, category, price, quantity, location)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, description, category, price, quantity, location)
        )
        db.commit()
        
        # Registrar movimiento inicial si hay cantidad
        if quantity > 0:
            db.execute(
                '''INSERT INTO movements (product_id, type, quantity, reason)
                   VALUES (?, 'in', ?, 'Stock inicial')''',
                (cursor.lastrowid, quantity)
            )
            db.commit()
        
        flash('Producto agregado correctamente.', 'success')
        return redirect(url_for('list_products'))
    
    return render_template('product_form.html', product=None, action='add')


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    """
    Editar un producto existente.
    GET: Muestra el formulario con datos actuales.
    POST: Actualiza el producto.
    """
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('list_products'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        price = request.form.get('price', '0').strip()
        quantity = request.form.get('quantity', '0').strip()
        location = request.form.get('location', '').strip()
        
        # Validaciones
        errors = []
        if not name:
            errors.append('El nombre es obligatorio.')
        if not category:
            errors.append('La categoría es obligatoria.')
        
        try:
            price = float(price)
            if price < 0:
                errors.append('El precio no puede ser negativo.')
        except ValueError:
            errors.append('El precio debe ser un número válido.')
        
        try:
            quantity = int(quantity)
            if quantity < 0:
                errors.append('La cantidad no puede ser negativa.')
        except ValueError:
            errors.append('La cantidad debe ser un número entero válido.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            # Pasar datos del formulario para repoblar
            form_data = dict(product)
            form_data.update(request.form)
            return render_template('product_form.html', 
                                   product=form_data, 
                                   action='edit')
        
        # Actualizar en base de datos
        db.execute(
            '''UPDATE products 
               SET name = ?, description = ?, category = ?, price = ?, quantity = ?, location = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (name, description, category, price, quantity, location, product_id)
        )
        db.commit()
        
        flash('Producto actualizado correctamente.', 'success')
        return redirect(url_for('list_products'))
    
    return render_template('product_form.html', product=product, action='edit')


@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    """
    Eliminar un producto.
    Solo acepta POST para evitar eliminaciones accidentales por GET.
    """
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('list_products'))
    
    db.execute('DELETE FROM products WHERE id = ?', (product_id,))
    db.commit()
    
    flash('Producto eliminado correctamente.', 'success')
    return redirect(url_for('list_products'))


@app.route('/products/<int:product_id>/adjust', methods=['GET', 'POST'])
def adjust_stock(product_id):
    """
    Ajustar existencias (entradas y salidas) con registro de movimientos.
    GET: Muestra formulario de ajuste.
    POST: Procesa el ajuste y registra el movimiento.
    """
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('list_products'))
    
    if request.method == 'POST':
        movement_type = request.form.get('type')  # 'in' o 'out'
        quantity = request.form.get('quantity', '0').strip()
        reason = request.form.get('reason', '').strip()
        
        errors = []
        if movement_type not in ('in', 'out'):
            errors.append('Tipo de movimiento inválido.')
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                errors.append('La cantidad debe ser mayor a cero.')
        except ValueError:
            errors.append('La cantidad debe ser un número entero válido.')
        
        # Validar que no haya salida mayor a lo disponible
        if movement_type == 'out' and quantity > product['quantity']:
            errors.append(f'No hay suficiente stock. Disponible: {product["quantity"]}')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('adjust_form.html', product=product)
        
        # Calcular nueva cantidad
        new_quantity = product['quantity'] + quantity if movement_type == 'in' else product['quantity'] - quantity
        
        # Actualizar cantidad del producto
        db.execute(
            'UPDATE products SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (new_quantity, product_id)
        )
        
        # Registrar movimiento
        db.execute(
            '''INSERT INTO movements (product_id, type, quantity, reason)
               VALUES (?, ?, ?, ?)''',
            (product_id, movement_type, quantity, reason)
        )
        db.commit()
        
        action_text = 'entrada' if movement_type == 'in' else 'salida'
        flash(f'{action_text.capitalize()} de {quantity} unidades registrada correctamente.', 'success')
        return redirect(url_for('product_movements', product_id=product_id))
    
    return render_template('adjust_form.html', product=product)


@app.route('/products/<int:product_id>/movements')
def product_movements(product_id):
    """
    Ver historial de movimientos de un producto.
    """
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if not product:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('list_products'))
    
    movements = db.execute(
        '''SELECT * FROM movements WHERE product_id = ? ORDER BY created_at DESC''',
        (product_id,)
    ).fetchall()
    
    return render_template('movements.html', product=product, movements=movements)


# ==================== EJECUCIÓN ====================

if __name__ == '__main__':
    # Inicializar base de datos al arrancar si no existe
    with app.app_context():
        init_db()
    
    # Ejecutar en puerto 5001
    app.run(host='127.0.0.1', port=5001, debug=True)