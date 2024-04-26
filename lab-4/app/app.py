
from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from mysql_db import MySQL
import mysql.connector
import re
PERMITED_PARAMS = ['login', 'password', 'last_name', 'first_name', 'middle_name', 'role_id']
EDIT_PARAMS = ['last_name', 'first_name', 'middle_name', 'role_id']

app = Flask(__name__)
application = app

app.config.from_pyfile('config.py')

db = MySQL(app)  #инициализация расширения MySQL 

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице нужно авторизироваться.'
login_manager.login_message_category = 'warning'

class User(UserMixin):
    def __init__(self, user_id, user_login):
        self.id = user_id
        self.login = user_login

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        remember = request.form.get('remember_me') == 'on'

        query = 'SELECT * FROM users WHERE login = %s and password_hash = SHA2(%s, 256);'

        # 1' or '1' = '1' LIMIT 1#
        # user'#
        # query = f"SELECT * FROM users WHERE login = '{login}' and password_hash = SHA2('{password}', 256);"
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (login, password))
            # cursor.execute(query)
            # print(cursor.statement)
            user = cursor.fetchone()

        if user:
            login_user(User(user.id, user.login), remember = remember)
            flash('Вы успешно прошли аутентификацию!', 'success')
            param_url = request.args.get('next')
            return redirect(param_url or url_for('index'))
        flash('Введён неправильный логин или пароль.', 'danger')
    return render_template('login.html')

@app.route('/users')
def users():
    query = 'SELECT users.*, roles.name AS role_name FROM users LEFT JOIN roles ON roles.id = users.role_id'
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        users_list = cursor.fetchall()
    
    return render_template('users.html', users_list=users_list)

@app.route('/users/new')
@login_required
def users_new():
    roles_list = load_roles()
    return render_template('users_new.html', roles_list=roles_list, user={}, wrong_params = [])

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
        params_dict[param] = request.form[param] or None
    return params_dict

def check_password(password):
    wrong_point = ''
    has_uppercase = False
    has_lowercase = False
    has_digit = False
    if len(password) > 7: 
        if len(password) > 128:
            wrong_point += 'Длина пароля не может быть больше 128 символов. '
    else: 
        wrong_point += 'Длина пароля не может быть меньше 8 символов. '
    for char in password:
        if char.isalnum() or char in '~!@#$%^&*_-+()[]{}><\/|"\',.:;':
            if char.isupper():
                has_uppercase = True
            elif char.islower():
                has_lowercase = True
            elif char.isdigit():
                has_digit = True
        else:
            wrong_point += 'Пароль должен содержать только латинские или кириллические буквы, цифры или ~!@#$%^&*_-+()[]{}><\/|"\',.:; '
    if not has_uppercase:
        wrong_point += 'Пароль должен содержать минимум одну заглавную букву. '
    if not has_lowercase:
        wrong_point += 'Пароль должен содержать минимум одну строчную букву. '
    if not has_digit:
        wrong_point += 'Пароль должен содержать минимум одну цифру. '
    return wrong_point

def check_login(login):
    wrong_point = ''
    if len(login) < 5:
        wrong_point += 'Длина логина не может быть меньше 5 символов. '
    if not bool(re.match(r'^[a-zA-Z0-9]+$', login)):
        wrong_point += 'Логин должен состоять только из латинских букв и цифр. '
    return wrong_point

@app.route('/users/create', methods=['POST'])
@login_required
def create_user():
    params = extract_params(PERMITED_PARAMS)
    wrong_params = []
    wrong_login = ''
    wrong_password = ''
    # print(params)
    for key, value in params.items():
        if not value and key != 'middle_name':
            wrong_params.append(key)

    
    if params['login']:
        wrong_login = check_login(params['login'])
        if wrong_login:
            wrong_params.append('incorrect_login')

    if params['password']:
        wrong_password = check_password(params['password'])
        if wrong_password:
            wrong_params.append('incorrect_password')

        
    # print(wrong_params)
    if wrong_params:
        flash('Заполните корректно форму', 'danger')
        return render_template('users_new.html', user = params, roles_list = load_roles(), wrong_params = wrong_params, wrong_login = wrong_login, wrong_password = wrong_password)
    

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

@app.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    params = extract_params(EDIT_PARAMS)
    params['id'] = user_id
    wrong_params = []
    # print(params)
    for key, value in params.items():
        if not value and key != 'middle_name':
            wrong_params.append(key)
    if wrong_params:
        flash('Заполните корректно форму', 'danger')
        return render_template('users_edit.html', user = params, roles_list = load_roles(), wrong_params = wrong_params)

    query = ('UPDATE users SET last_name=%(last_name)s, first_name=%(first_name)s, '
             'middle_name=%(middle_name)s, role_id=%(role_id)s WHERE id=%(id)s;')
    try:
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, params)
            db.connection().commit()
            flash('Успешно!', 'success')
    except mysql.connector.errors.DatabaseError:
        db.connection().rollback()
        flash('При сохранении данных возникла ошибка.', 'danger')
        return render_template('users_edit.html', user = params, roles_list = load_roles(), wrong_params = wrong_params)

    return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit')
@login_required
def edit_user(user_id):
    query = 'SELECT * FROM users WHERE users.id = %s;'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('users_edit.html', user=user, roles_list = load_roles())


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
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
def show_user(user_id):
    query = 'SELECT * FROM users WHERE users.id = %s;'
    # query_role_name = 'SELECT name FROM roles WHERE roles.name = %s;'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    # cursor.execute(query_role_name, (user_id,))
    # print(user)
    cursor.close()
    return render_template('users_show.html', user=user)

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('index'))

@login_manager.user_loader
def load_user(user_id):
    query = 'SELECT * FROM users WHERE users.id = %s;'
    cursor = db.connection().cursor(named_tuple=True)
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user.id, user.login)
    return None

@app.route('/user/<int:user_id>/change_password', methods=['GET', 'POST'])
@login_required
def change_password(user_id):
    wrong_params = []
    wrong_password = ''
    if request.method == 'POST':
        old_password = request.form['oldpassword'] or wrong_params.append('none_old_password')
        new_password = request.form['newpassword'] or wrong_params.append('none_new_password')
        repeat_password = request.form['repeatpassword'] or wrong_params.append('none_repeat_password')
        # print(wrong_params)
        if wrong_params:
            # flash('Заполните все поля.', 'danger')
            return render_template('change_password.html', wrong_params = wrong_params)

        query = 'SELECT login FROM users WHERE id = %s and password_hash = SHA2(%s, 256);'
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, old_password))
            # print(cursor.statement)
            user = cursor.fetchone()

        if new_password:
            wrong_password = check_password(new_password)
            if wrong_password:
                wrong_params.append('incorrect_new_password')

        if new_password != repeat_password:
            wrong_params.append('repeat_password')

        if user and not wrong_params:
            query = 'UPDATE users SET password_hash = SHA2(%s, 256) WHERE id=%s;'
            try:
                with db.connection().cursor(named_tuple=True) as cursor:
                    cursor.execute(query, (new_password, user_id))
                    db.connection().commit()
                    flash('Пароль успешно изменён.', 'success')
                    return redirect(url_for('index'))
            except mysql.connector.errors.DatabaseError:
                db.connection().rollback()
                flash('При сохранении данных возникла ошибка.', 'danger')
        elif not user:
            wrong_params.append('old_password')

    return render_template('change_password.html', wrong_params = wrong_params, wrong_password = wrong_password)