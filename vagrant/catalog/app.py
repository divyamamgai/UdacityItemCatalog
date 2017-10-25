import random
import string
import json
import httplib2
import ssl
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, make_response
from flask import session as flask_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from sqlalchemy import create_engine
from sqlalchemy import exc as sqlalchemy_exc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, Item

app = Flask(__name__)

GOOGLE_CLIENT_ID = json.loads(open('google_client_secret.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
db_session = sessionmaker(bind=engine)
session = db_session()


def generate_random_token():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(32))


def get_user_id(email):
    """Get User ID using User Email"""
    user = session.query(User).filter_by(email=email).first()
    if user:
        return user.id
    else:
        return None


def create_user(name, email):
    """Create a new User using the details provided"""
    try:
        user = User(name=name, email=email)
        session.add(user)
        session.commit()
        return user.id
    except sqlalchemy_exc.IntegrityError:
        return None


def create_category(name, user_id):
    """Create a new Category using the details provided"""
    category = Category(name=name, user_id=user_id)
    session.add(category)
    session.commit()
    return category


@app.route('/login')
def login():
    if 'access_token' not in flask_session:
        login_state = generate_random_token()
        flask_session['login_state'] = login_state
        return render_template('login.html', login_state=login_state)
    else:
        return redirect(url_for('catalog'))


@app.route('/login/google/<string:login_state>', methods=['POST'])
def login_google(login_state):
    if login_state != flask_session.get('login_state'):
        response = make_response(json.dumps('Invalid login state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    auth_code = request.data

    try:
        # Exchange auth code received for access token using the Google App Client secrets.
        oauth_flow = flow_from_clientsecrets('google_client_secret.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(auth_code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = credentials.access_token
    h = httplib2.Http()
    try:
        # Request token info to make sure it is in valid state.
        token_info_result = json.loads(
            h.request('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token,
                      'GET')[1].decode('utf-8'))
    except ssl.SSLEOFError:
        response = make_response(json.dumps('Error occurred while requesting token info from Google Plus.'), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    if token_info_result.get('error') is not None:
        response = make_response(json.dumps(token_info_result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    google_plus_id = credentials.id_token['sub']

    if token_info_result.get('user_id') != google_plus_id:
        response = make_response(json.dumps('Token\'s user ID does not match given user ID.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if token_info_result.get('issued_to') != GOOGLE_CLIENT_ID:
        response = make_response(json.dumps('Token\'s client ID does not match app\'s.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = flask_session.get('access_token')
    stored_google_plus_id = flask_session.get('google_plus_id')
    if stored_access_token is not None and google_plus_id == stored_google_plus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    try:
        # Request user info using the access token.
        user_info_result = json.loads(
            h.request('https://www.googleapis.com/oauth2/v1/userinfo?access_token=%s&alt=json' % access_token,
                      'GET')[1].decode('utf-8'))
    except ssl.SSLEOFError:
        response = make_response(json.dumps('Error occurred while requesting user info from Google Plus.'), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    flask_session['provider'] = 'google'
    flask_session['access_token'] = access_token
    flask_session['google_plus_id'] = google_plus_id
    flask_session['name'] = user_info_result.get('name')
    flask_session['email'] = user_info_result.get('email')

    user_id = get_user_id(flask_session.get('email'))
    # If user does not exists create a new user.
    if not user_id:
        user_id = create_user(flask_session.get('name'), flask_session.get('email'))
        if not user_id:
            # If user creation failed delete already assigned session keys.
            del flask_session['provider']
            del flask_session['access_token']
            del flask_session['google_plus_id']
            del flask_session['name']
            del flask_session['email']
            response = make_response(json.dumps('Error occurred while creating user.'), 500)
            response.headers['Content-Type'] = 'application/json'
            return response

    flask_session['user_id'] = user_id

    response = make_response(json.dumps('User "%s" logged in successfully.' % flask_session.get('name')), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/login/facebook/<string:login_state>', methods=['POST'])
def login_facebook(login_state):
    if login_state != flask_session.get('login_state'):
        response = make_response(json.dumps('Invalid login state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    fb_exchange_token = request.data.decode('utf-8')

    # Load Facebook app credentials.
    facebook_client_secret = json.loads(open('facebook_client_secret.json', 'r').read())
    app_id = facebook_client_secret.get('web').get('app_id')
    app_secret = facebook_client_secret.get('web').get('app_secret')

    h = httplib2.Http()
    try:
        # Request access token using the exchange token received.
        # .decode('utf-8') converts the byte result to string.
        access_token_result = json.loads(
            h.request('https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token'
                      '&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, fb_exchange_token),
                      'GET')[1].decode('utf-8'))
    except ssl.SSLEOFError:
        response = make_response(json.dumps('Error occurred while requesting access token from Facebook.'), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = access_token_result.get('access_token')

    try:
        # Request user info using the access token received.
        user_info_result = json.loads(
            h.request('https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % access_token,
                      'GET')[1].decode('utf-8'))
    except ssl.SSLEOFError:
        response = make_response(json.dumps('Error occurred while requesting user info from Facebook.'), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    flask_session['provider'] = 'facebook'
    flask_session['access_token'] = access_token
    flask_session['facebook_id'] = user_info_result.get('id')
    flask_session['name'] = user_info_result.get('name')
    flask_session['email'] = user_info_result.get('email')

    user_id = get_user_id(flask_session.get('email'))
    if not user_id:
        user_id = create_user(flask_session.get('name'), flask_session.get('email'))
        if not user_id:
            del flask_session['provider']
            del flask_session['access_token']
            del flask_session['facebook_id']
            del flask_session['name']
            del flask_session['email']
            response = make_response(json.dumps('Error occurred while creating user.'), 500)
            response.headers['Content-Type'] = 'application/json'
            return response

    flask_session['user_id'] = user_id

    response = make_response(json.dumps('User "%s" logged in successfully.' % flask_session.get('name')), 200)
    response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/logout')
def logout():
    if 'access_token' in flask_session:
        if flask_session.get('provider') == 'google':
            logout_response = logout_google()
            if logout_response.status_code != 200:
                flash('Error occurred while trying to logout via Google Plus.')
                return redirect(url_for('catalog'))
        elif flask_session.get('provider') == 'facebook':
            logout_response = logout_facebook()
            if logout_response.status_code != 200:
                flash('Error occurred while trying to logout via Facebook.')
                return redirect(url_for('catalog'))

        # On successful logout delete session keys.
        del flask_session['name']
        del flask_session['email']
        del flask_session['user_id']
        del flask_session['provider']
        del flask_session['login_state']

        flash('You have been successfully logged out!')
        return redirect(url_for('catalog'))
    else:
        flash('You were not logged in!')
        return redirect(url_for('catalog'))


@app.route('/logout/google')
def logout_google():
    access_token = flask_session.get('access_token')
    if not access_token:
        response = make_response(json.dumps('User is not connected via Google Plus.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    h = httplib2.Http()
    try:
        revoke_token_result = h.request('https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token,
                                        'GET')[0].decode('utf-8')
    except ssl.SSLEOFError:
        response = make_response(json.dumps('Error occurred while requesting to revoke Google Plus token.', 500))
        response.headers['Content-Type'] = 'application/json'
        return response

    if revoke_token_result['status'] == '200':
        del flask_session['access_token']
        del flask_session['google_plus_id']

        response = make_response(json.dumps('Successfully disconnected from Google Plus.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke Google Plus token.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/logout/facebook')
def logout_facebook():
    access_token = flask_session.get('access_token')
    if not access_token:
        response = make_response(json.dumps('User is not connected via Facebook.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    h = httplib2.Http()
    try:
        revoke_token_result = h.request('https://graph.facebook.com/%s/permissions?access_token=%s' % (
            flask_session.get('facebook_id'), access_token), 'DELETE')[0]
    except ssl.SSLEOFError:
        response = make_response(json.dumps('Error occurred while requesting to revoke Facebook token.', 500))
        response.headers['Content-Type'] = 'application/json'
        return response

    if revoke_token_result['status'] == '200':
        del flask_session['access_token']
        del flask_session['facebook_id']

        response = make_response(json.dumps('Successfully disconnected from Facebook.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke Facebook token.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/catalog')
def catalog():
    categories = session.query(Category).all()
    latest_items = session.query(Item).order_by(Item.id.desc()).limit(10).all()
    return render_template('catalog.html', categories=categories, latest_items=latest_items,
                           flask_session=flask_session)


@app.route('/catalog.json')
def catalog_json():
    categories = session.query(Category).all()
    serialized_categories = []
    # For each serialized category add a property 'items' containing a list of items of that category.
    for category in categories:
        serialized_category = category.serialize
        items = session.query(Item).filter_by(category_id=category.id).all()
        serialized_category['items'] = [item.serialize for item in items]
        serialized_categories.append(serialized_category)
    users = session.query(User).all()
    serialized_users = [user.serialize for user in users]
    return jsonify(categories=serialized_categories, users=serialized_users)


@app.route('/catalog/create', methods=['GET', 'POST'])
def catalog_create():
    # Check if the user is logged in or not.
    if 'access_token' not in flask_session:
        flash('You need to be logged in to create categories!')
        return redirect(url_for('catalog'))
    if request.method == 'POST':
        if flask_session.get('form_token') != request.form.get('form_token'):
            flash('Form token miss match!')
            return redirect(url_for('catalog'))
        # Check if name is not empty.
        if request.form['name']:
            category_name = request.form['name']
            # Check if the Category name already exists or not.
            category = session.query(Category).filter_by(name=category_name).first()
            if category:
                flash('Category "%s" already exists!' % category_name)
            else:
                create_category(name=request.form['name'], user_id=flask_session.get('user_id'))
        else:
            flash('Category Name cannot be empty!')
        return redirect(url_for('catalog'))
    elif request.method == 'GET':
        flask_session['form_token'] = generate_random_token()
        return render_template('catalog_create.html', flask_session=flask_session)


@app.route('/catalog/<string:category_name>/items')
def catalog_items(category_name):
    category = session.query(Category).filter_by(name=category_name).first()
    # Check if Category exists or not.
    if category:
        categories = session.query(Category).all()
        items = session.query(Item).filter_by(category_id=category.id).all()
        return render_template('catalog_items.html', categories=categories, category=category, items=items,
                               flask_session=flask_session)
    else:
        flash('Category "%s" cannot be found!' % category_name)
        return redirect(url_for('catalog'))


@app.route('/catalog/<string:category_name>/items.json')
def catalog_items_json(category_name):
    category = session.query(Category).filter_by(name=category_name).first()
    if category:
        user = session.query(User).filter_by(id=category.user_id).first()
        items = session.query(Item).filter_by(category_id=category.id).all()
        serialized_items = [item.serialize for item in items]
        return jsonify(category_creator=user.serialize, items=serialized_items)
    else:
        return jsonify(error='Category not found')


@app.route('/catalog/<string:category_name>/<string:item_title>')
def catalog_item(category_name, item_title):
    category = session.query(Category).filter_by(name=category_name).first()
    if category:
        item = session.query(Item).filter_by(title=item_title, category_id=category.id).first()
        if item:
            return render_template('catalog_item.html', category=category, item=item, flask_session=flask_session)
        else:
            flash('Item "%s" cannot be found!' % item_title)
            return redirect(url_for('catalog'))
    else:
        flash('Category "%s" does not exists!' % category_name)
        return redirect(url_for('catalog'))


@app.route('/catalog/<string:category_name>/<string:item_title>.json')
def catalog_item_json(category_name, item_title):
    category = session.query(Category).filter_by(name=category_name).first()
    if category:
        item = session.query(Item).filter_by(title=item_title, category_id=category.id).first()
        if item:
            user = session.query(User).filter_by(id=item.user_id).first()
            return jsonify(item_creator=user.serialize, item=item.serialize)
        else:
            return jsonify(error='Item not found')
    else:
        return jsonify(error='Category not found')


@app.route('/catalog/items/create', methods=['GET', 'POST'])
def catalog_items_create():
    if 'access_token' not in flask_session:
        flash('You need to be logged in to create items!')
        return redirect(url_for('catalog'))
    if request.method == 'POST':
        if flask_session.get('form_token') != request.form.get('form_token'):
            flash('Form token miss match!')
            return redirect(url_for('catalog'))
        # Validate the required fields for item.
        if not request.form.get('title'):
            flash('Item Title cannot be empty!')
            return redirect(url_for('catalog_items_create'))
        if not request.form.get('category_id'):
            flash('Item Category cannot be empty!')
            return redirect(url_for('catalog_items_create'))
        category = session.query(Category).filter_by(id=request.form['category_id']).first()
        if not category:
            flash('Selected Category does not exists!')
            return redirect(url_for('catalog_items_create'))
        item_title = request.form.get('title')
        item = session.query(Item).filter_by(title=item_title).first()
        if item:
            flash('Item "%s" already exists!' % item_title)
            return redirect(url_for('catalog_items_create'))
        item = Item(title=request.form.get('title'), description=request.form.get('description'),
                    category_id=category.id, user_id=flask_session.get('user_id'))
        session.add(item)
        session.commit()
        flash('Item "%s" successfully created!' % item.title)
        return redirect(url_for('catalog'))
    elif request.method == 'GET':
        categories = session.query(Category).all()
        flask_session['form_token'] = generate_random_token()
        return render_template('catalog_items_create.html', categories=categories, flask_session=flask_session)


@app.route('/catalog/<string:item_title>/edit', methods=['GET', 'POST'])
def catalog_item_edit(item_title):
    if 'access_token' not in flask_session:
        flash('You need to be logged in to modify items!')
        return redirect(url_for('catalog'))
    item = session.query(Item).filter_by(title=item_title).first()
    if item:
        # Check if the logged in user is same as the creator.
        if item.user_id != flask_session.get('user_id'):
            flash('You cannot edit the item since it was not created by you!')
            return redirect(url_for('catalog'))
        if request.method == 'POST':
            if flask_session.get('form_token') != request.form.get('form_token'):
                flash('Form token miss match!')
                return redirect(url_for('catalog'))
            if not request.form.get('title'):
                flash('Item Title cannot be empty!')
                return redirect(url_for('catalog_item_edit', item_title=item_title))
            new_item_title = request.form.get('title')
            # If the item title has changed, validate that it is unique.
            if item_title != new_item_title:
                existing_item = session.query(Item).filter_by(title=new_item_title).first()
                if existing_item:
                    flash('Item "%s" already exists!' % new_item_title)
                    return redirect(url_for('catalog_item_edit', item_title=item_title))
            item.title = new_item_title
            item.category_id = request.form.get('category_id')
            item.description = request.form.get('description')
            session.add(item)
            session.commit()
            flash('Item successfully edited!')
            return redirect(url_for('catalog_item', category_name=item.category.name, item_title=item.title))
        elif request.method == 'GET':
            categories = session.query(Category).all()
            flask_session['form_token'] = generate_random_token()
            return render_template('catalog_item_edit.html', categories=categories, item=item,
                                   flask_session=flask_session)
    else:
        flash('Item "%s" cannot be found!' % item_title)
        return redirect(url_for('catalog'))


@app.route('/catalog/<string:item_title>/delete', methods=['GET', 'POST'])
def catalog_item_delete(item_title):
    if 'access_token' not in flask_session:
        flash('You need to be logged in to modify items!')
        return redirect(url_for('catalog'))
    item = session.query(Item).filter_by(title=item_title).first()
    if item:
        if item.user_id != flask_session.get('user_id'):
            flash('You cannot delete the item since it was not created by you!')
            return redirect(url_for('catalog'))
        if request.method == 'POST':
            if flask_session.get('form_token') != request.form.get('form_token'):
                flash('Form token miss match!')
                return redirect(url_for('catalog'))
            session.delete(item)
            session.commit()
            flash('Item "%s" successfully deleted!' % item_title)
            return redirect(url_for('catalog'))
        elif request.method == 'GET':
            flask_session['form_token'] = generate_random_token()
            return render_template('catalog_item_delete.html', item=item, flask_session=flask_session)
    else:
        flash('Item "%s" cannot be found!' % item_title)
        return redirect(url_for('catalog'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='localhost', port=5000)
