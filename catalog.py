from flask import Flask, render_template, url_for, request, redirect, flash, \
    jsonify, make_response
from sqlalchemy import create_engine, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Item, Category, db_url, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import os


"""This is to validate the extension."""
valid_ext = [
    'png',
    'jpg',
    'jpeg',
    'gif'
]

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web'][
    'client_id']

engine = create_engine(db_url)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

app = Flask(__name__, static_url_path='/static')


def authorized(id):
    """This will return if the current user has permission to modify the
    item with the id or not."""
    if get_user() is not None:
        return get_user_id(get_user()['email']) == id
    else:
        return False


def already_a_user(user_email):
    """This will return where the email is already registered or not."""
    user_count = (session.query(func.count(User.id))).filter_by(
        email=user_email).scalar()
    return True if user_count > 0 else False


def create_user():
    """Will register the user based on the email address."""
    new_user = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(new_user)
    session.commit()
    return session.query(User).filter_by(email=login_session['email']).one().id


def get_user_info(user_id):
    """Returns the user object for the given user_id."""
    return session.query(User).filter_by(id=user_id).one()


def get_user_id(user_email):
    """Returns the user_id for the user with the given email."""
    return session.query(User).filter_by(email=user_email).one().id


def get_user():
    """Returns a user dictionary object from the session if logged in or
    None if logged out."""
    try:
        user = {
            'name': login_session['username'],
            'email': login_session['email'],
            'picture': login_session['picture']
        }

    except:
        user = None

    return user


@app.route('/')
def index():
    """Main page of the web app. We need to query all the categories and all
    the items and render it on using the layout. There will also be links to
    add more items as well as categories in here."""
    categories = session.query(Category).all()

    """Let's limit the items to be the latest 20 items."""
    items = session.query(Item).order_by(desc(Item.id)).limit(20)

    return render_template('home.html', categories=categories, items=items,
                           user=get_user())


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
                               main_category=main_category, user=get_user())

    except:
        """Trying to acces an invalid category"""
        flash(u'Category not found. Please try another.', 'warning')
        return redirect(url_for('index'))


@app.route('/category/new/', methods=['POST', 'GET'])
def new_category():
    """ Creates a new category if it is a POST request and provides the form
    for a new category if it is a GET request"""

    if request.method == 'GET':
        """GET request, so lets load the template with the form."""

        if get_user() is None:
            return redirect(url_for('login'))

        csrf_token = ''.join(random.choice(string.ascii_uppercase +
                                           string.digits)
                             for x in xrange(32))
        login_session['csrf_token'] = csrf_token

        return render_template('new_category.html', csrf_token=csrf_token,
                               user=get_user())

    if request.method == 'POST':
        """POST request, so lets process the form and add the new catagory."""

        if get_user() is None:
            return redirect(url_for('login'))

        name = None

        try:
            csrf_token = request.form['csrf_token']
            if csrf_token != login_session['csrf_token']:
                return redirect(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", code=301)

            name = request.form['name']
            name = name.strip()
            user_id = get_user_id(login_session['email'])
            category = Category(name=name, user_id=user_id)
            session.add(category)
            session.commit()
            flash("New category %s added!" % name, 'success')
            return redirect(url_for('index'), code=301)

        except:
            session.rollback()
            flash(u'Invalid name. Please try again.', 'warning')
            return render_template('new_category.html', name=name,
                                   user=get_user())


@app.route('/category/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    """Delete the selected category. But need to clear out the dependant
    items first."""

    if get_user() is None:
        return redirect(url_for('login'))

    try:
        """Let's delete all the items that belong to the said category by
        first locating the category."""
        deleting_category = session.query(Category).filter_by(
            id=category_id).one()

        if delete_category.user_id != get_user_id(login_session['email']):
            flash("This category belong to you!", 'danger')
            flash("Logging you out!", 'warning')
            return redirect(url_for('gdisconnect'))

        """Lets locate all the items that belong to the category."""
        items_for_category = session.query(Item).filter_by(
            category_id=category_id).all()

        """Now we just need to delete each of the items."""
        for item in items_for_category:
            if item.image_url is not None:
                os.remove(
                    os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'static/images/' + item.image_url))
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
        return redirect(url_for('show_category'), category_id=category_id,
                        user=get_user())


@app.route('/item/new/', methods=['POST', 'GET'])
def new_item():
    """Creates a new item if it is a POST request and loads the form to
    create one if it is a GET request."""
    if request.method == 'POST':
        if get_user() is None:
            return redirect(url_for('login'))

        item_title = None
        item_description = None
        item_category_id = None

        try:
            csrf_token = request.form['csrf_token']
            if csrf_token != login_session['csrf_token']:
                return redirect(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", code=301)

            user_id = get_user_id(login_session['email'])

            item_title = request.form['title']
            item_description = request.form['description']
            item_category_id = request.form['category']
            filename = None

            try:
                """Try to access the uploaded file and see if it has a valid
                extension."""
                file = request.files['file']
                ext = file.filename.split('.')[-1]
                if valid_ext.__contains__(ext):
                    filename = ''.join(random.choice(string.uppercase +
                                                     string.digits) for x in
                                       xrange(12))
                    filename = filename + file.filename
                    storage_path = os.path.dirname(os.path.realpath(__file__))
                    storage_path = os.path.join(storage_path, 'static/images')
                    file.save(os.path.join(storage_path, filename))

            except:
                pass

            new_item = Item(title=item_title, description=item_description,
                            category_id=item_category_id, user_id=user_id)

            """There was a filename associated that was valid with a valid
            extention, so need to save the file loaction in the image_url."""
            if filename is not None:
                new_item.image_url = filename

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
                                   categories=categories, user=get_user())

    if request.method == 'GET':
        """Send all the categories as options for the item."""
        if get_user() is None:
            return redirect(url_for('login'))

        categories = session.query(Category).all()
        categories_count = (session.query(func.count(Category.id))).scalar()
        if categories_count == 0:
            flash(u'There are no categories yet. Please create one first',
                  'warning')
            return redirect(url_for('new_category'))

        csrf_token = ''.join(random.choice(string.uppercase + string.digits)
                             for x in xrange(32))
        login_session['csrf_token'] = csrf_token
        return render_template('new_item.html', categories=categories,
                               csrf_token=csrf_token, user=get_user())


@app.route('/item/<int:item_id>/')
def show_item(item_id):
    """Shows the item referenced by item_id"""
    item = session.query(Item).filter_by(id=item_id).one()
    item_count = (session.query(func.count(Item.id))).scalar()
    if item_count == 0:
        flash("Item #%i not found. Please try again." % item_id, 'warning')
        return redirect(url_for('index'))

    return render_template('item.html', item=item, user=get_user(),
                           authorized=authorized(item.user_id))


@app.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    """Will delete the item only if the user is the owner of the item."""
    if get_user() is None:
        return redirect(url_for('login'))

    try:
        item = session.query(Item).filter_by(id=item_id).one()
        if not authorized(item.user_id):
            flash('You are not authorized to delete this item!', 'warning')
            return redirect(url_for('show_item', item_id=item_id))
        if item.image_url is not None:
            os.remove(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               'static/images/'+item.image_url))
            item.image_url = None
        session.delete(item)
        session.commit()
        flash("Deleted item %s!" % item.title, 'danger')
        return redirect(url_for('index'))

    except:
        session.rollback()
        flash("Could not delete item #%i." % item_id, 'warning')
        return redirect(url_for('index'))


@app.route('/item/<int:item_id>/edit/', methods=['POST', 'GET'])
def edit_item(item_id):
    """Creates a new item if it is a POST request and loads the form to
    create one if it is a GET request."""
    if request.method == 'POST':
        if get_user() is None:
            return redirect(url_for('login'))

        try:
            csrf_token = request.form['csrf_token']
            if csrf_token != login_session['csrf_token']:
                return redirect(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", code=301)

            item_title = request.form['title']
            item_description = request.form['description']
            item_category_id = request.form['category']
            item = session.query(Item).filter_by(id=item_id).one()
            category = session.query(Category).filter_by(
                id=item_category_id).one()

            filename = item.image_url

            try:
                """Similar to new item. This is access the file and if valid
                file and valid ext found, will update the file. If no file
                is found, will leave the image intact."""
                file = request.files['file']
                ext = file.filename.split('.')[-1]
                if valid_ext.__contains__(ext):
                    filename = ''.join(random.choice(string.uppercase +
                                                     string.digits) for x in
                                       xrange(12))
                    filename = filename + file.filename
                    storage_path = os.path.dirname(os.path.realpath(__file__))
                    storage_path = os.path.join(storage_path, 'static/images')
                    file.save(os.path.join(storage_path, filename))
                    if item.image_url is not None:
                        os.remove(os.path.join(
                            os.path.dirname(os.path.realpath(__file__)),
                            'static/images/' + item.image_url))

            except:
                pass

            item.image_url = filename
            delete_image = None
            try:
                delete_image = request.form['delete_image']

            except:
                pass

            if delete_image == 'on':
                if item.image_url is not None:
                    os.remove(os.path.join(
                        os.path.dirname(os.path.realpath(__file__)),
                        'static/images/' + item.image_url))
                    item.image_url = None

            print "2"

            if not authorized(item.user_id):
                flash('You are not authorized to delete this item!', 'warning')
                return redirect(url_for('show_item', item_id=item_id))

            print "3"

            item.title = item_title
            item.description = item_description
            item.category = category
            session.commit()
            flash("Edited the item %s!" % item.title, 'success')
            return redirect(
                url_for('index'))

        except:
            session.rollback()
            flash(u'Inavlid parameters. Please try again.', 'warning')
            return redirect(url_for('edit_item', item_id=item_id))

    if request.method == 'GET':
        """Send all the categories as options for the item."""
        if get_user() is None:
            return redirect(url_for('login'))

        item = session.query(Item).filter_by(id=item_id).one()
        item_count = (session.query(func.count(Item.id)).filter_by(
            id=item_id)).scalar()
        categories = session.query(Category).all()

        if item_count == 0:
            flash("Could not find item $%i. Please try again," % item_id,
                  'warning')
            return redirect(url_for('index'))

        csrf_token = ''.join(random.choice(string.uppercase + string.digits)
        for x in xrange(32))
        login_session['csrf_token'] = csrf_token

        return render_template('edit_item.html', item_id=item_id, item=item,
                               categories=categories, csrf_token=csrf_token,
                               user=get_user())


@app.route('/api/<int:category_id>/items/')
def json_items(category_id):
    """Returns a json containing all the items that belong to the category
    as referenced by the category_id."""
    items = session.query(Item).filter_by(category_id=category_id).all()

    return jsonify(items=[item.serialize() for item in items])


@app.route('/api/<int:item_id>/item/')
def json_item(item_id):
    """Returns the single item referenced by the item_id."""
    items = session.query(Item).filter_by(id=item_id).all()

    return jsonify(item=[item.serialize() for item in items])


@app.route('/api/all/')
def json_all():
    """Returns all the category and each item belonging to the categories."""

    """Get all the categories"""
    categories = session.query(Category).all()

    """Create an empty list to store the categories in."""
    result = []
    for category in categories:
        """Get all the items in each category at a time."""
        items = session.query(Item).filter_by(category_id=category.id).all()

        """Empty list to store the items."""
        category_items = []
        for item in items:
            """Serialize each item and add it to each categories list."""
            category_items.append(item.serialize())

        """Append a dictionary per category that has the serialized category
        as well as the list of serialized items that belongs to it."""
        result.append({
            'category': category.serialize(),
            'items': category_items
        })

    """Return the JSON."""
    return jsonify(result=result)


@app.route('/login/')
def login():
    csrf_token = ''.join(random.choice(string.uppercase + string.digits) for
                         x in xrange(32))
    login_session['csrf_token'] = csrf_token
    return render_template('login.html', csrf_token=csrf_token,
                           user=get_user())


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # if the csrf test fails, return 401
    if request.args.get('csrf_token') != login_session['csrf_token']:
        response = make_response(json.dumps('Invalid csrf_token', 401))
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)

    # if the flowexchange has an error there is an issue with the
    # authorization code
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the '
                                            'authorization code', 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    # by this time, we can access the access_token sent in by google.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    http = httplib2.Http()
    result = json.loads(http.request(url, 'GET')[1])

    # there was an error with the http request with the acces token
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error'), 500))
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps(
            'Token\'s user id does not match given user\'s id.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    # client id is not the same as the response from google. Issues to
    # someone else

    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps(
            'Token\'s client id does not match app\'s.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('User is already connected.', 200))
        response.headers['Content-Type'] = 'applcation/json'

    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    try:
        create_user()
        flash("Welcome to Catalog, %s!" % login_session['username'], 'success')
    except IntegrityError:
        session.rollback()
        flash("You have logged in as %s!" % login_session['username'],
              'success')
    response = jsonify({
        'result': 'successful',
        'url': '/'
    })
    response.headers['Content-Type'] = 'application/json'
    response.headers['status'] = '200'
    return response


@app.route('/logout/')
def gdisconnect():

    # if there are not users logged in
    if get_user() is None:
        flash("No user is logged in!", 'warning')
        return redirect(url_for('index'))

    credentials = login_session['credentials']
    access_token = credentials.access_token
    url = "https://accounts.google.com/o/oauth2/revoke?token=%s" % access_token
    http = httplib2.Http()
    result = http.request(url, 'GET')[0]
    print result

    # logout has happened succesfully or timeout has happened with the login
    if result['status'] == '200' or result['status'] == '400':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        flash("You have been successfully disconnected!", 'success')
        return redirect(url_for('index'))

    else:
        response = make_response(json.dumps('error', result['status']))
        response.headers['Content-Type'] = 'application/json'
        return response


if __name__ == '__main__':
    app.debug = True
    app.secret_key = "asdbkj132kj3bd24!#!#!1kfnF@$24FL"
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host='', port=8080)
