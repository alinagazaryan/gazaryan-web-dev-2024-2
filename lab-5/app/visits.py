
import io
from flask import render_template, Blueprint, request, send_file
from flask_login import current_user, login_required
from app import db, app
from math import ceil
from auth import permission_check, init_login_manager
PER_PAGE = 10

bp = Blueprint('visits', __name__, url_prefix='/visits')

init_login_manager(app)

def generate_report_file(records, fields):
    csv_content = '№,' + ','.join(fields) + '\n'
    for i, record in enumerate(records):
        values = [str(getattr(record, f, '')) for f in fields]
        csv_content += f'{i+1},' + ','.join(values) + '\n'
    f = io.BytesIO()
    f.write(csv_content.encode('utf-8'))
    f.seek(0)
    return f

@bp.route('/')
@login_required
def logging():
    page = request.args.get('page', 1, type = int)
    if current_user.is_authenticated and current_user.can('show_log'):
        query = ('SELECT action_logs.*, users.login '
                'FROM users RIGHT JOIN action_logs ON action_logs.user_id = users.id '
                'ORDER BY created_at DESC LIMIT %s OFFSET %s')
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (PER_PAGE, (page-1)*PER_PAGE))
            logs = cursor.fetchall()

        query = 'SELECT COUNT(*) AS count FROM action_logs'
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query)
            count = cursor.fetchone().count
    else:
        query = ('SELECT action_logs.*, users.login '
                'FROM users RIGHT JOIN action_logs ON action_logs.user_id = users.id '
                'WHERE users.id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s')
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (current_user.id, PER_PAGE, (page-1)*PER_PAGE))
            logs = cursor.fetchall()
        
        query = 'SELECT COUNT(*) AS count FROM action_logs WHERE user_id = %s'
        with db.connection().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (current_user.id,))
            count = cursor.fetchone().count
    
    last_page = ceil(count/PER_PAGE)

    return render_template('visits/logs.html', logs = logs, last_page = last_page, current_page = page)

@bp.route('/stat/pages')
@login_required
@permission_check('show_log')
def pages_stat():
    query = 'SELECT path, COUNT(*) as count FROM action_logs GROUP BY path ORDER BY count DESC;'
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        records = cursor.fetchall()
    if request.args.get('download_csv'):
        f = generate_report_file(records, ['path', 'count'])
        return send_file(f, mimetype='text/csv', as_attachment=True, download_name='pages_stat.csv')
    return render_template('visits/pages_stat.html', records=records)

@bp.route('/stat/users')
@login_required
@permission_check('show_log')
def users_stat():
    query = ('SELECT users.first_name, users.last_name, users.middle_name, COUNT(*) AS count '
        'FROM users ' 
        'RIGHT JOIN action_logs ON users.id = action_logs.user_id '
        'GROUP BY users.first_name, users.last_name, users.middle_name '
        'ORDER BY count DESC'
    )
    with db.connection().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        records = cursor.fetchall()
        print(records)
    if request.args.get('download_csv'):
        f = generate_report_file(records, ['first_name', 'last_name', 'count'])
        return send_file(f, mimetype='text/csv', as_attachment=True, download_name='users_stat.csv')
    return render_template('visits/users_stat.html', records=records)