from flask import Flask, render_template, url_for, request, redirect

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Item, Category, db_url

engine = create_engine(db_url)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__, static_url_path='/static')


@app.route('/static/style.css/')
def load_css():
    return app.send_static_file('style.css')


@app.route('/')
def index():
    categories = session.query(Category).all()
    items = session.query(Item).order_by(desc(Item.id)).limit(20)

    return render_template('home.html', categories=categories, items=items)


@app.route('/category/<int:category_id>/')
def show_category(category_id):
    try:
        category = session.query(Category).filter_by(id=category_id).one()
        result = category.name

        return result

    except:
        return "404"


@app.route('/category/new/', methods=['POST', 'GET'])
def new_category():
    if request.method == 'GET':
        return render_template('new_category.html')

    if request.method == 'POST':
        name = request.form['name']
        new_category = Category(name=name)
        session.add(new_category)
        session.commit()
        return redirect(url_for('index'), code=301)


@app.route('/item/new/')
def new_item():
    return render_template('new_item.html')


if __name__ == '__main__':
    app.debug = True
    app.run(host='', port=8080)
