
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from mysql_db import MySQL
import mysql.connector
PERMITED_PARAMS = ['login', 'password', 'last_name', 'first_name', 'middle_name', 'role_id']
EDIT_PARAMS = ['last_name', 'first_name', 'middle_name', 'role_id']

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db = MySQL(app)

from auth import bp as auth_bp
from auth import init_login_manager, permission_check
from visits import bp as visits_bp

app.register_blueprint(auth_bp)
init_login_manager(app)

app.register_blueprint(visits_bp)

@app.before_request
def loger():
    if request.endpoint == 'static':
        return
    path = request.path
    user_id = getattr(current_user, 'id', None)
    query = 'INSERT INTO action_logs(user_id, path) VALUES (%s, %s);'
    try:
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, path))
            db.connection().commit()
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/users')
def users():
    query = 'SELECT users.*, roles.name AS role_name FROM users LEFT JOIN roles ON roles.id = users.role_id'
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        users_list = cursor.fetchall()
    
    return render_template('users.html', users_list=users_list)

@app.route('/users/new')
@login_required
@permission_check('create')
def users_new():
    roles_list = load_roles()
    return render_template('users_new.html', roles_list=roles_list, user={})

def load_roles():
    query = 'SELECT * FROM roles;'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query)
    roles = cursor.fetchall()
    cursor.close()
    return roles

def extract_params(params_list):
    params_dict = {}
    for param in params_list:
        params_dict[param] = request.form.get(param, None) or None
    return params_dict

@app.route('/users/create', methods=['POST'])
@login_required
@permission_check('create')
def create_user():
    params = extract_params(PERMITED_PARAMS)
    query = 'INSERT INTO users(login, password_hash, last_name, first_name, middle_name, role_id) VALUES (%(login)s, SHA2(%(password)s, 256), %(last_name)s, %(first_name)s, %(middle_name)s, %(role_id)s);'
    try:
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, params)
            db.connection().commit()
            flash('Успешно!', 'success')
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('При сохранении данных возникла ошибка.', 'danger')
        return render_template('users_new.html', user = params, roles_list = load_roles())
    
    return redirect(url_for('users'))

# create_user = login_required(create_user)

@app.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
@permission_check('edit')
def update_user(user_id):
    params = extract_params(EDIT_PARAMS)
    params['id'] = user_id
    if current_user.can('change_role'):
        query = ('UPDATE users SET last_name=%(last_name)s, first_name=%(first_name)s, '
                'middle_name=%(middle_name)s, role_id=%(role_id)s WHERE id=%(id)s;')
    else:
        del params['role_id']
        query = ('UPDATE users SET last_name=%(last_name)s, first_name=%(first_name)s, '
                'middle_name=%(middle_name)s WHERE id=%(id)s;')
    try:
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, params)
            db.connection().commit()
            flash('Успешно!', 'success')
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('При сохранении данных возникла ошибка.', 'danger')
        return render_template('users_edit.html', user = params, roles_list = load_roles())

    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit')
@login_required
@permission_check('edit')
def edit_user(user_id):
    query = 'SELECT * FROM users WHERE users.id = %s;'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('users_edit.html', user=user, roles_list = load_roles())


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@permission_check('delete')
def delete_user(user_id):
    query = 'DELETE FROM users WHERE users.id=%s;'
    try:
        cursor = db.connection().cursor(named_tuple=True)
        cursor.execute(query, (user_id,))
        db.connection().commit()
        cursor.close()
        flash('Пользователь успешно удален', 'success')
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('При удалении пользователя возникла ошибка.', 'danger')
    return redirect(url_for('users'))


@app.route('/user/<int:user_id>')
@permission_check('show')
def show_user(user_id):
    query = 'SELECT * FROM users WHERE users.id = %s;'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('users_show.html', user=user)


