from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from flask import session as flask_session
import random
import string
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item

app = Flask(__name__)

# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine
db_session = sessionmaker(bind=engine)
session = db_session()


@app.route('/')
@app.route('/catalog')
def catalog():
    categories = session.query(Category).all()
    latest_items = session.query(Item).order_by(Item.id.desc()).limit(10).all()
    return render_template('catalog.html', categories=categories, latest_items=latest_items)


@app.route('/login')
def login():
    login_state = ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(32))
    flask_session['login_state'] = login_state
    return render_template('login.html', login_state=login_state)


@app.route('/catalog/create', methods=['GET', 'POST'])
def catalog_create():
    if request.method == 'POST':
        if request.form['name']:
            category_name = request.form['name']
            category = session.query(Category).filter_by(name=category_name).one()
            if category:
                flash('Category Name already exists!')
            else:
                category = Category(name=request.form['name'])
                session.add(category)
                session.commit()
        else:
            flash('Category Name cannot be empty!')
        return redirect(url_for('catalog'))
    elif request.method == 'GET':
        return render_template('catalog_create.html')


@app.route('/catalog/<string:category_name>/items')
def catalog_items(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    if category:
        categories = session.query(Category).all()
        items = session.query(Item).filter_by(category_id=category.id).all()
        return render_template('catalog_items.html', categories=categories, category=category, items=items)
    else:
        flash('Category Name cannot be found!')
        return redirect(url_for('catalog'))


@app.route('/catalog/items/create', methods=['GET', 'POST'])
def catalog_items_create():
    if request.method == 'POST':
        if not request.form['title']:
            flash('Item Title cannot be empty!')
            return redirect(url_for('catalog_items_create'))
        if not request.form['category_id']:
            flash('Item Category cannot be empty!')
            return redirect(url_for('catalog_items_create'))
        category = session.query(Category).filter_by(id=request.form['category_id']).one()
        if not category:
            flash('Item Category does not exists!')
            return redirect(url_for('catalog_items_create'))
        item = session.query(Item).filter_by(title=request.form['title']).one()
        if item:
            flash('Item Title already exists!')
        else:
            item = Item(title=request.form['title'], description=request.form['description'],
                        category_id=request.form['category_id'])
            session.add(item)
            session.commit()
            flash('Item "%s" successfully created!' % item.title)
        return redirect(url_for('catalog'))
    elif request.method == 'GET':
        categories = session.query(Category).all()
        return render_template('catalog_items_create.html', categories=categories)


@app.route('/catalog/<string:category_name>/<string:item_title>')
def catalog_item(category_name, item_title):
    category = session.query(Category).filter_by(name=category_name).one()
    if category:
        item = session.query(Item).filter_by(title=item_title, category_id=category.id).one()
        if item:
            return render_template('catalog_item.html', category=category, item=item)
        else:
            flash('Item Title cannot be found!')
            return redirect(url_for('catalog'))
    else:
        flash('Item Category does not exists!')
        return redirect(url_for('catalog'))


@app.route('/catalog/<string:item_title>/edit', methods=['GET', 'POST'])
def catalog_item_edit(item_title):
    item = session.query(Item).filter_by(title=item_title).one()
    if item:
        if request.method == 'POST':
            if not request.form['title']:
                flash('Item Title cannot be empty!')
                return redirect(url_for('catalog_item_edit', item_title=item_title))
            if item_title != request.form['title']:
                existing_item = session.query(Item).filter_by(title=request.form['title']).one()
                if existing_item:
                    flash('Item Title already exists!')
                    return redirect(url_for('catalog_item_edit', item_title=item_title))
            item.title = request.form['title']
            item.category_id = request.form['category_id']
            item.description = request.form['description']
            session.add(item)
            session.commit()
            flash('Item successfully edited!')
            return redirect(url_for('catalog_item', category_name=item.category.name, item_title=item.title))
        elif request.method == 'GET':
            categories = session.query(Category).all()
            return render_template('catalog_item_edit.html', categories=categories, item=item)
    else:
        flash('Item Title cannot be found!')
        return redirect(url_for('catalog'))


@app.route('/catalog/<string:item_title>/delete', methods=['GET', 'POST'])
def catalog_item_delete(item_title):
    item = session.query(Item).filter_by(title=item_title).one()
    if item:
        if request.method == 'POST':
            session.delete(item)
            session.commit()
            flash('Item "%s" successfully deleted!' % item_title)
            return redirect(url_for('catalog'))
        elif request.method == 'GET':
            return render_template('catalog_item_delete.html', item=item)
    else:
        flash('Item Title cannot be found!')
        return redirect(url_for('catalog'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
