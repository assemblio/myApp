from flask import Blueprint, render_template, \
    session, redirect, url_for, request

import json
from arda.mod_admin.forms.user_form import UserForm
from arda.mod_admin.forms.settings_form import SettingsForm
from arda.mod_admin.forms.portfolio_form import PortfolioForm
from arda import mongo, utils, bcrypt
from bson import json_util, ObjectId
from arda.mod_admin.models.user_model import Users, Role
from flask.ext.security import login_user, login_required, logout_user, current_user
from arda import user_datastore
mod_admin = Blueprint('admin', __name__, url_prefix='/admin')


@mod_admin.route('/users', methods=['GET'])
@login_required
def users():
    '''
    List users
    '''
    if current_user.has_role('Admin'):
        users = mongo.db.users.find({})
        json_obj = build_contacts_cursor(users)
        return render_template('mod_admin/users.html', results=json_obj['results'])
    else:
        return redirect(url_for('customers.customers'))


@mod_admin.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    '''
    Create user
    '''
    user_form = UserForm()
    from arda import bcrypt
    # If we do a get request, we are just requesting the page.
    if request.method == "GET":
        if current_user.has_role('Admin'):
            return render_template(
                'mod_admin/edit_user.html',
                form=user_form,
                action=url_for('admin.create_user'),
                display_pass_field=False
            )
        else:
            return redirect(url_for('customers.customers'))

    elif request.method == "POST":
        if current_user.has_role('Admin'):
            user_form = UserForm(request.form)
            user_data = user_form.data
            user = Users(
                last_name=user_data['last_name'],
                first_name=user_data['first_name'],
                email=user_data['email'],
                password=bcrypt.generate_password_hash(user_data['password'], rounds=12)
            )
            user.save()
            default_role = user_datastore.find_role(user_data['role'])
            user_datastore.add_role_to_user(user, default_role)
            #mongo.db.users.insert(user_doc)

            return redirect(url_for('admin.users'))
        else:
            return redirect(url_for('customers.customers'))
    return render_template('mod_admin/edit_user.html', form=user_form)


@mod_admin.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    '''
    Edit user
    '''
    if request.method == "GET":
        if current_user.has_role('Admin'):
            user_doc = mongo.db.users.find_one({'_id': ObjectId(user_id)})

            # Populate the user form of the user we are editing.
            user_form = UserForm()
            user_form.first_name.data = user_doc['first_name']
            user_form.last_name.data = user_doc['last_name']
            user_form.email.data = user_doc['email']
            user_form.role.data = user_doc['role']

            return render_template(
                'mod_admin/edit_user.html',
                form=user_form,
                action=url_for('admin.edit_user',
                user_id=user_doc['_id']),
                display_pass_field=True
            )
        else:
            return redirect(url_for('customers.customers'))
    elif request.method == "POST":
        if current_user.has_role('Admin'):
            user_form = UserForm(request.form)

            mongo.db.users.update(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'first_name': user_form.first_name.data,
                        'last_name': user_form.last_name.data,
                        'email': user_form.email.data,
                        'role': user_form.role.data
                    }
                }
            )

            return redirect(url_for('admin.users'))
        else:
            return redirect(url_for('customers.customers'))

@mod_admin.route('/users/delete/<user_id>', methods=['GET'])
@login_required
def delete_user(user_id):
    '''
    Delete user
    '''
    users = mongo.db.users.remove({'_id': ObjectId(user_id)})
    return redirect(url_for('admin.users'))


@mod_admin.route('/change/password', methods=['POST'])
@login_required
def change_password():

    user_id = current_user['id']
    user = mongo.db.users.find_one({'_id': json_util.loads(user_id)})

    old_password = request.form['oldPassword']
    new_password = bcrypt.generate_password_hash(request.form['newPassword'], rounds=12)

    if not bcrypt.check_password_hash(user["password"], old_password):
        error = "Error!Password didn't change!"
        users = mongo.db.users.find({})
        json_obj = build_contacts_cursor(users)

        return render_template('mod_admin/users.html', message=error, results=json_obj['results'])
    else:
        mongo.db.users.update(
            {'_id': json_util.loads(user_id)},
            {"$set": {'password': new_password}
        })

        return redirect(url_for('admin.users'))


@mod_admin.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    '''
    A page to configure CRM settings (e.g. remove/add types of services)
    '''
    portfolio = None

    if request.method == 'GET':
        settings_doc = mongo.db.settings.find_one({'_id': 0})
        portfolio = []

        if settings_doc is None:
            settings_doc = utils.get_default_settings()

        elif 'portfolio' in settings_doc:
            portfolio = settings_doc['portfolio']

        settings_form = SettingsForm()
        settings_form.site_title.data = settings_doc['site_title']
        settings_form.site_tagline.data = settings_doc['site_tagline']
        settings_form.site_navbar_title.data = settings_doc['site_navbar_title']
        settings_form.landingpage_banner_image_url.data = settings_doc['landingpage_banner_image_url']
        settings_form.web_url.data = settings_doc['web_url']
        settings_form.fb_url.data = settings_doc['fb_url']
        settings_form.tw_url.data = settings_doc['tw_url']
        settings_form.li_url.data = settings_doc['li_url']

    if request.method == 'POST':
        if current_user.has_role('Admin'):
            settings_form = SettingsForm(request.form)
            settings_data = settings_form.data

            mongo.db.settings.update({'_id': 0}, {'$set': settings_data}, True)

            # Update session with new settings data.
            session['settings'] = settings_form.data
        else:
            return redirect(url_for('customers.customers'))

    portfolio_form = PortfolioForm()
    return render_template('mod_admin/settings.html', form=settings_form, pf_form=portfolio_form, portfolio=portfolio)


@mod_admin.route('/settings/portfolio/update', methods=['POST'])
@login_required
def settings_portfolio_update():
    portfolio_form = PortfolioForm(request.form)
    portfolio_data = portfolio_form.data
    portfolio_data['id'] = utils.get_doc_id()

    mongo.db.settings.update({'_id': 0}, {'$push': {'portfolio': portfolio_data}})

    session['settings']['portfolio'] = portfolio_data

    return redirect(url_for('admin.settings'))


@mod_admin.route('/settings/portfolio/delete/<item_id>', methods=['GET'])
@login_required
def settings_portfolio_delete(item_id):

    settings = mongo.db.settings.find_one({'_id': 0})
    porfolio = []

    for item in settings['portfolio']:
        if item['id'] != item_id:
            porfolio.append(item)

    mongo.db.settings.update(
        {'_id': 0},
        {
            '$set': {
                'portfolio':  porfolio
            }
        }
    )

    session['settings']['portfolio'] = porfolio

    return redirect(url_for('admin.settings'))


def build_contacts_cursor(cursor):
    ''' Builds a JSON response for a given cursor
    '''
    response = json.loads('{}')
    response_to_append_to = response['results'] = []

    for idx, itm in enumerate(cursor):
        response_to_append_to.append(itm)

    return response
