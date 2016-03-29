from flask import Flask, render_template, url_for, request, redirect, flash

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Item, Category, db_url

engine = create_engine(db_url)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__, static_url_path='/static')



@app.route('/')
def index():
    """Main page of the web app. We need to query all the categories and all
    the items and render it on using the layout. There will also be links to
    add more items as well as categories in here."""
    categories = session.query(Category).all()

    """Let's limit the items to be the latest 20 items."""
    items = session.query(Item).order_by(desc(Item.id)).limit(20)

    return render_template('home.html', categories=categories, items=items)


@app.route('/category/<int:category_id>/items/')
def show_category(category_id):
    """This will list all the categories as well as all the items that are
    in the selected category. There will also be a link to delete the current
    category in here."""
    try:
        """First lets query all the categories, the selected category
        reference by category_id, all the items in the category and the
        items count for the category"""
        categories = session.query(Category).all()
        items = session.query(Item).filter_by(category_id=category_id).all()
        items_count = (session.query(func.count(Item.id))).filter_by(
            category_id=category_id).scalar()
        main_category = session.query(Category).filter_by(id=category_id).one()

        return render_template('category.html', categories=categories,
                               items=items, items_count=items_count,
                               main_category=main_category)

    except:
        flash(u'Category not found. Please try another.', 'warning')
        return redirect(url_for('index'))


@app.route('/category/new/', methods=['POST', 'GET'])
def new_category():
    """ Creates a new category if it is a POST request and provides the form
    for a new category if it is a GET request"""

    if request.method == 'GET':
        """GET request, so lets load the template with the form."""
        return render_template('new_category.html')

    if request.method == 'POST':
        """POST request, so lets process the form and add the new catagory."""
        try:
            name = request.form['name']
            name = name.strip()
            category = Category(name=name)
            session.add(category)
            session.commit()
            flash("New category %s added!" % name, 'success')
            return redirect(url_for('index'), code=301)

        except:
            session.rollback()
            flash(u'Invalid name. Please try again.', 'warning')
            return render_template('new_category.html', name=name)


@app.route('/category/<int:category_id>/delete')
def delete_category(category_id):
    """Delete the selected category. But need to clear out the dependant
    items first."""

    try:
        """Let's delete all the items that belong to the said category by
        first locating the category."""
        deleting_category = session.query(Category).filter_by(
            id=category_id).one()

        """Lets locate all the items that belong to the category."""
        items_for_category = session.query(Item).filter_by(
            category_id=category_id).all()

        """Now we just need to delete each of the items."""
        for item in items_for_category:
            session.delete(item)
            session.commit()

        """And then delete the category that contains them."""
        session.delete(deleting_category)
        session.commit()

        """Redirect back to the main page."""
        flash("Category %s and all its items deleted!" %
              deleting_category.name, 'danger')
        return redirect(url_for('index'), code=301)

    except Exception:
        session.rollback()
        flash("Could not delete category %s!" % deleting_category.name,
              'warning')
        return redirect(url_for('show_category'), category_id=category_id)


@app.route('/item/new/', methods=['POST', 'GET'])
def new_item():
    """Creates a new item if it is a POST request and loads the form to
    create one if it is a GET request."""
    if request.method == 'POST':
        try:
            item_title = request.form['title']
            item_description = request.form['description']
            item_category_id = request.form['category']
            new_item = Item(title=item_title, description=item_description,
                            category_id=item_category_id)
            session.add(new_item)
            session.commit()
            flash("Create new item %s!" % new_item.title, 'success')
            return redirect(
                url_for('index'))

        except:
            session.rollback()
            flash(u'Inavlid parameters. Please try again.', 'warning')
            categories = session.query(Category).all()
            return render_template('new_item.html', item_title=item_title,
                                   item_description=item_description,
                                   item_category_id=item_category_id,
                                   categories=categories)

    if request.method == 'GET':
        """Send all the categories as options for the item."""
        categories = session.query(Category).all()
        categories_count = (session.query(func.count(Category.id))).scalar()
        if categories_count == 0:
            flash(u'There are no categories yet. Please create one first',
                  'warning')
            return redirect(url_for('new_category'))
        return render_template('new_item.html', categories=categories)


@app.route('/item/<int:item_id>/')
def show_item(item_id):
    """Shows the item referenced by item_id"""
    item = session.query(Item).filter_by(id=item_id).one()
    item_count = (session.query(func.count(Item.id))).scalar()
    if item_count == 0:
        flash("Item #%i not found. Please try again." % item_id, 'warning')
        return redirect(url_for('index'))

    return render_template('item.html', item=item)


@app.route('/item/<int:item_id>/delete')
def delete_item(item_id):
    try:
        item = session.query(Item).filter_by(id=item_id).one()
        session.delete(item)
        session.commit()
        flash("Deleted item %s!" % item.title, 'danger')
        return redirect(url_for('index'))

    except:
        session.rollback()
        flash("Could not delete item #%i." % item_id, 'warning')
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.debug = True
    app.secret_key = "asdbkj132kj3bd24!#!#!1kfnF@$24FL"
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host='', port=8080)
