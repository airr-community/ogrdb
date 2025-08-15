# Copyright William Lees
#
# This source code, and any executable file compiled or derived from it, is governed by the European Union Public License v. 1.2,
# the English version of which is available here: https://perma.cc/DK5U-NDVE
import json

import requests
from flask import url_for, render_template, request, flash
from jinja2 import TemplateNotFound
from flask_login import current_user, login_required, logout_user
from flask_security import SQLAlchemyUserDatastore
from flask_security.utils import hash_password
from werkzeug.utils import redirect

from db.misc_db import Committee
from db.userdb import User, Role
from forms.security import ExtendedRegisterForm, FirstAccountForm, ProfileForm, save_Profile
from head import app, security, db

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = security.init_app(app, user_datastore, confirm_register_form=ExtendedRegisterForm)



@app.route('/', methods=['GET', 'POST'])
def index():
    # Add the admin user, if we don't have one yet

    if user_datastore.find_role('Admin') is None:
        return redirect(url_for('create_user'))

    # Add the test role if we are in UAT

    if 'UAT' in app.config and app.config['UAT']:
        if not user_datastore.find_role('Test'):
            user_datastore.create_role(name = 'Test')
        tc = db.session.query(Committee).filter(Committee.species == 'Test').count()
        if tc < 1:
            test_ctee = Committee()
            test_ctee.species = 'Test'
            test_ctee.committee = 'Test Committee'
            db.session.add(test_ctee)
            db.session.commit()
        if current_user.is_authenticated and not current_user.has_role('Test'):
            user_datastore.add_role_to_user(current_user, 'Test')
            db.session.commit()

    # Get news from Wordpress

    news_items = []

    try:
        cat_url = None
        wp_url = app.config['WORDPRESS_NEWS_URL'] + app.config['WORDPRESS_REST']
        r = requests.get(wp_url + 'categories')
        if r.status_code == 200:
            resp = r.content.decode("utf-8")
            resp = json.loads(resp)

            for rec in resp:
                if rec['slug'] == 'ogrdb_news':
                    cat_url = '%sposts?categories=%s' % (wp_url, rec['id'])

        if cat_url:
            r = requests.get(cat_url + '&per_page=5')
            if r.status_code == 200:
                resp = r.content.decode("utf-8")
                resp = json.loads(resp)

                for item in resp:
                    news_items.append({
                    'date': item['date'].split('T')[0],
                    'title': item['title']['rendered'],
                    'excerpt': item['excerpt']['rendered'],
                    'link': item['link'],
                })
    except:
        pass

    return render_template('index.html', current_user=current_user, news_items=news_items)


@app.route('/render_page/<page>')
def render_page(page):
    try:
        if page.endswith('.html'):
            return render_template('static/%s' % page)
        else:
            return render_template('static/%s.html' % page)
    except TemplateNotFound:
        return "Page not found", 404


@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if user_datastore.find_role('Admin') is not None:
        return redirect('/')

    form = FirstAccountForm()

    if request.method == 'POST':
        if form.validate():
            user = user_datastore.create_user(email=form.email.data, password=hash_password(form.password.data), name=form.name.data, confirmed_at='2018-11-14')
            db.session.commit()
            user_datastore.create_role(name='Admin')
            user_datastore.add_role_to_user(user, 'Admin')
            db.session.commit()
            flash("User created")
            return redirect('/')

    return render_template('security/first_account.html', form=form)


@app.route('/help')
def help_page():
    """OGRDB Help and Documentation page with WordPress integration"""
    
    # Get help articles from WordPress with pagination to fetch all articles
    help_articles = []
    
    try:
        wp_url = app.config['WORDPRESS_NEWS_URL'] + app.config['WORDPRESS_REST']
        r = requests.get(wp_url + 'categories')
        if r.status_code == 200:
            resp = r.content.decode("utf-8")
            resp = json.loads(resp)

            # Find both OGRDB category IDs
            ogrdb_news_cat_id = None
            ogrdb_cat_id = None
            
            for rec in resp:
                if rec['slug'] == 'ogrdb_news':
                    ogrdb_news_cat_id = rec['id']
                elif rec['slug'] == 'ogrdb':
                    ogrdb_cat_id = rec['id']
            
            # Define categories to fetch from
            categories_to_fetch = []
            if ogrdb_news_cat_id:
                categories_to_fetch.append(ogrdb_news_cat_id)
            if ogrdb_cat_id:
                categories_to_fetch.append(ogrdb_cat_id)
            
            # Fetch articles from each category separately
            for cat_id in categories_to_fetch:
                cat_url = f'{wp_url}posts?categories={cat_id}'
                
                # Fetch all pages of articles for this category
                page = 1
                per_page = 100  # Maximum allowed by WordPress REST API
                
                while True:
                    paginated_url = f"{cat_url}&per_page={per_page}&page={page}&_embed"
                    r = requests.get(paginated_url)
                    
                    if r.status_code != 200:
                        break
                        
                    resp = r.content.decode("utf-8")
                    resp = json.loads(resp)
                    
                    # If no articles returned, we've reached the end
                    if not resp:
                        break

                    for item in resp:
                        # Check if we already have this article (avoid duplicates)
                        if any(article['id'] == item['id'] for article in help_articles):
                            continue
                            
                        # Extract tags from embedded data
                        tags = []
                        if '_embedded' in item and 'wp:term' in item['_embedded']:
                            # Tags are usually in the second array of wp:term
                            if len(item['_embedded']['wp:term']) > 1:
                                tags = [tag['slug'] for tag in item['_embedded']['wp:term'][1]]
                        
                        help_articles.append({
                            'id': item['id'],
                            'date': item['date'].split('T')[0],
                            'title': item['title']['rendered'],
                            'excerpt': item['excerpt']['rendered'],
                            'link': item['link'],
                            'tags': tags
                        })
                    
                    # If we got fewer articles than requested, we're on the last page
                    if len(resp) < per_page:
                        break
                        
                    page += 1
                    
                    # Safety valve to prevent infinite loops
                    if page > 50:  # Limit to 5000 articles max per category
                        break
                        
    except Exception as e:
        print(f"Error fetching WordPress help articles: {e}")
        pass

    # Sort articles by date (newest first)
    help_articles.sort(key=lambda x: x['date'], reverse=True)

    return render_template('help.html', current_user=current_user, help_articles=help_articles)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj = current_user)
    form.email = ''
    if request.method == 'POST':
        if form.validate():
            if 'disable_btn' in request.form:
                current_user.active = False
                save_Profile(db, current_user, form)
                flash('Account disabled.')
                logout_user()
                return redirect('/')
            else:
                save_Profile(db, current_user, form)
                flash('Profile updated.')

    return render_template('profile.html', form=form, current_user=current_user, url='profile')


