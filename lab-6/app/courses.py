from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Course, Category, User, Review
from tools import CoursesFilter, ImageSaver

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

def params():
    return { p: request.form.get(p) or None for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

@bp.route('/')
def index():
    courses = CoursesFilter(**search_params()).perform()
    pagination = db.paginate(courses)
    courses = pagination.items
    categories = db.session.execute(db.select(Category)).scalars()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = Course()
    categories = db.session.execute(db.select(Category)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = Course()
    try:
        if f and f.filename:
            img = ImageSaver(f).save()

        image_id = img.id if img else None
        course = Course(**params(), background_image_id=image_id)
        db.session.add(course)
        db.session.commit()
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        db.session.rollback()
        categories = db.session.execute(db.select(Category)).scalars()
        users = db.session.execute(db.select(User)).scalars()
        return render_template('courses/new.html',
                            categories=categories,
                            users=users,
                            course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

@bp.route('/<int:course_id>')
def show(course_id):
    check_review = Review.query.filter_by(course_id=course_id, user_id=current_user.id).first()
    course_obj = db.get_or_404(Course, course_id)
    category_obj = db.get_or_404(Category, course_obj.category_id)
    reviewList = db.session.query(Review).filter(Review.course_id == course_id).limit(5)
    return render_template('courses/show.html', course=course_obj, reviewList=reviewList, check_review=check_review, course_id=course_id)

@bp.route('/<int:course_id>/reviews', methods=['GET', 'POST'])
def reviews(course_id):
    check_review = Review.query.filter_by(course_id=course_id, user_id=current_user.id).first() # здесь первое обращение к таблице review
    # что делает строка в таблицу review делаем запрос, фильтруем по ...
    if check_review:
        flash('Вы уже оставили отзыв.', 'danger')
        return redirect(url_for('courses.show', course_id=course_id))
    else:
        if request.method == 'POST':
            
            rating_value = int(request.form['rating'])
            text = request.form['text']

            review = Review(text=text, rating=rating_value, 
                        course_id=course_id, user_id=current_user.id)
            
            try:
                db.session.add(review)
                course = db.get_or_404(Course, course_id)
                course.rating_sum += rating_value
                course.rating_num += 1
                db.session.add(course)
                db.session.commit()
                flash(f'Отзыв успешно добавлен', 'success')
            except:
                db.session.rollback()
                flash(f'При сохранении отзыва произошла ошибка', 'danger')
            
            return redirect(url_for('courses.show', course_id=course_id))



    page = request.args.get('page', 1, type=int)
    reviews = Review.query.filter_by(course_id=course_id)
    reviews_filter = request.args.get('reviews_filter')
    d={'reviews_filter': reviews_filter, 'course_id': course_id}
    if reviews_filter == 'by_pos':
        reviews = reviews.order_by(Review.rating.desc())
    elif reviews_filter == 'by_neg':
        reviews = reviews.order_by(Review.rating.asc())
    else:
        reviews = reviews.order_by(Review.created_at.desc())
    pagination = reviews.paginate(page=page, count=5)
    reviews = pagination.items
    
    return render_template('courses/reviews.html', 
                           course_reviews=reviews, 
                           course_id=course_id, 
                           pagination=pagination, 
                           search_params = d, 
                           check_review=check_review
    )
