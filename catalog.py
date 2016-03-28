from flask import Flask, render_template, url_for

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Item, Category, db_url

engine = create_engine(db_url)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__)




@app.route('/')
def index():
    categories = session.query(Category).all()

    return render_template('home.html', categories=categories)


@app.route('/category/<int:category_id>/')
def show_category(category_id):
    try:
        category = session.query(Category).filter_by(id=category_id).one()
        result = category.name

        return result

    except:
        return "404"


if __name__ == '__main__':
    app.debug = True
    app.run(host='', port=8080)
