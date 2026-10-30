from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from ..utils import create_or_update_user, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["kantree"] = {
    "title": "Kantree",
    "tagline": "Query your Kantree workspaces using SQL in real-time.",
    "url": "https://kantree.io/",
    "logo": "integrations/kantree/logo.png",
    "icon": "integrations/kantree/icon.png",
    "landing_url": "/kantree",
    "setup_url": "/kantree/setup"
}

oauth.register('kantree',
    api_base_url='https://kantree.io/api/1.0/',
    authorize_url='https://kantree.io/oauth/authorize',
    access_token_url='https://kantree.io/oauth/token',
    client_kwargs={
        'scope': "read_user read_workspace",
    })


blueprint = Blueprint('kantree', __name__, url_prefix='/kantree', template_folder='templates')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="kantree")


@blueprint.get('/login')
def login():
    if request.args.get("setup"):
        session["kantree_setup"] = True
    redirect_uri = url_for('kantree.login_callback', _external=True)
    return oauth.kantree.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
def login_callback():
    token = oauth.kantree.authorize_access_token()
    resp = oauth.kantree.get('me', token=token)
    resp.raise_for_status()
    sqldb = create_or_update_user(resp.json()['email'], "kantree", token)
    if not session.pop("kantree_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('kantree.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("kantree", lambda: url_for('kantree.login', setup=1))
def setup():
    resp = oauth.kantree.get(f'organizations')
    resp.raise_for_status()
    orgs = resp.json()

    if request.method == 'POST':
        org_id = int(request.form['org_id'])
        found = False
        for org in orgs:
            if org['id'] == org_id:
                found = True
                break
        if not found:
            abort(404)

        resp = oauth.kantree.get(f'organizations/{org_id}/projects')
        resp.raise_for_status()
        projects = resp.json()
        suggestion = None
        if projects:
            suggestion = f'SELECT * FROM "{projects[0]["title"]}"'

        init_script = [
            ('CREATE CREDENTIALS ON "https://kantree.io/api" REMOTE %s', (create_auth_url("kantree"),)),
            ('CREATE PAGINATION ON "https://kantree.io/api" AS page = header(X-Kantree-NextPage)', None),
            ('CREATE PAGINATION ON "https://kantree.io/api/1.0/projects/*/export/json" AS page = json(next)', None),
            (f"""CREATE SCHEMA WITH
                    TABLES AS (SELECT id, title AS name FROM "https://kantree.io/api/1.0/organizations/{org_id}/projects")
                    COLUMNS AS (WITH attrs AS (SELECT UNNEST(attributes) FROM "https://kantree.io/api/1.0/projects/$TABLE[id]") SELECT id, name FROM attrs)
                    ROWS AS (SELECT * FROM "https://kantree.io/api/1.0/projects/$TABLE[id]/export/json#data")
                """, None),
        ]

        sqldb = init_integration_db("kantree", org['name'], init_script, suggestion)

        return redirect(url_for("client", db=sqldb.slug))

    return render_template("kantree/setup.html", orgs=orgs)


app.register_blueprint(blueprint)
