from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from ..utils import create_or_update_user, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["asana"] = {
    "title": "Asana",
    "tagline": "Query your Asana projects using SQL in real-time.",
    "url": "https://asana.io/",
    "logo": "integrations/asana/logo.png",
    "icon": "integrations/asana/icon.png",
    "landing_url": "/asana",
    "setup_url": "/asana/setup"
}

oauth.register('asana',
    api_base_url='https://app.asana.com/api/1.0/',
    authorize_url='https://app.asana.com/-/oauth_authorize',
    access_token_url='https://app.asana.com/-/oauth_token')


blueprint = Blueprint('asana', __name__, url_prefix='/asana')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="asana")


@blueprint.get('/login')
def login():
    if request.args.get("setup"):
        session["asana_setup"] = True
    redirect_uri = url_for('asana.login_callback', _external=True)
    return oauth.asana.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
def login_callback():
    token = oauth.asana.authorize_access_token()
    sqldb = create_or_update_user(token["data"]['email'], "asana", token)
    if not session.pop("asana_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('asana.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("asana", lambda: url_for('asana.login', setup=1))
def setup():
    init_script = [
        ('CREATE CREDENTIALS ON "https://app.asana.com/api/1.0" REMOTE %s', (create_auth_url("asana"),)),
        ('CREATE PAGINATION ON "https://app.asana.com/api/1.0" AS offset = json(next_page.offset)', None),
        (f"""CREATE SCHEMA WITH
                TABLES AS (SELECT gid, name FROM "https://app.asana.com/api/1.0/projects#data")
                ROWS AS (SELECT * FROM "https://app.asana.com/api/1.0/tasks#data" WHERE "?project" = '$TABLE[gid]')
            """, None),
    ]

    sqldb = init_integration_db("asana", "Asana", init_script)
    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
