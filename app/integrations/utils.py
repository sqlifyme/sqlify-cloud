from hyperflask import current_app, url_for, redirect
from hyperflask.utils.tokens import create_token
from hyperflask_users import signup, login as login_user, current_user
from app.models import db, UserOauthTokens, Database, User
import functools


def create_or_update_user(email, integration, token):
    if not current_user.is_authenticated:
        user = User.find_one(email=email)
        if not user:
            user = signup(email=email, signup_using=integration)
        else:
            login_user(user, login_using=integration)
    return activate_user_integration(integration, token)


def activate_user_integration(integration, token):
    UserOauthTokens.save_from_oauth(integration, token)
    return Database.find_one_for_current_user(integration=integration)


def create_auth_url(integration):
    token = create_token((current_app.config["SQLIFY_AUTH_SECRET"], current_user.id, integration))
    return url_for('db_auth', token=token, _external=True)


def integration_login_required(integration, route, scope=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(route())
            token = UserOauthTokens.find_one_for_current_user(integration=integration)
            if not token:
                return redirect(route())
            if scope and scope not in token.scope:
                return redirect(route())
            return func(*args, **kwargs)
        return wrapper
    return decorator


def init_integration_db(integration, name, init_script, suggestion=None):
    init_script_sql = ";\n".join([stmt for stmt, _ in init_script])
    with db:
        sqldb = Database.find_one_for_current_user(name=name, integration=integration)
        if not sqldb:
            sqldb = Database.create(current_user, name, integration=integration, suggestion=suggestion, init_script=init_script_sql)
        else:
            sqldb.suggestion = suggestion
            sqldb.init_script = init_script_sql
            sqldb.save()

        current_user.first_integration_completed = True
        current_user.save()

    with sqldb.connect() as cur:
        for stmt, params in init_script:
            if params:
                cur.execute(stmt, params)
            else:
                cur.execute(stmt)

    return sqldb
