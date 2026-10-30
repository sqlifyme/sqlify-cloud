from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from ..utils import create_or_update_user, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["airtable"] = {
    "title": "Airtable",
    "tagline": "Query your Airtable databases using SQL in real-time.",
    "url": "https://airtable.com/",
    "logo": "integrations/airtable/logo.png",
    "icon": "integrations/airtable/icon.png",
    "landing_url": "/airtable",
    "setup_url": "/airtable/setup"
}

oauth.register('airtable',
    api_base_url='https://api.airtable.com/v0/',
    authorize_url='https://airtable.com/oauth2/v1/authorize',
    access_token_url='https://airtable.com/oauth2/v1/token',
    client_kwargs={
        'code_challenge_method': 'S256',
        'scope': "data.records:read schema.bases:read user.email:read",
    })


blueprint = Blueprint('airtable', __name__, url_prefix='/airtable', template_folder='templates')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="airtable")


@blueprint.get('/login')
def login():
    if request.args.get("setup"):
        session["airtable_setup"] = True
    redirect_uri = url_for('airtable.login_callback', _external=True)
    return oauth.airtable.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
def login_callback():
    token = oauth.airtable.authorize_access_token()
    resp = oauth.airtable.get('meta/whoami', token=token)
    resp.raise_for_status()
    sqldb = create_or_update_user(resp.json()['email'], "airtable", token)
    if not session.pop("airtable_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('airtable.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("airtable", lambda: url_for('airtable.login', setup=1))
def setup():
    resp = oauth.airtable.get(f'meta/bases')
    resp.raise_for_status()
    bases = resp.json()['bases']

    if request.method == 'POST':
        base_id = request.form['base_id']
        found = False
        for base in bases:
            if base['id'] == base_id:
                found = True
                break
        if not found:
            abort(404)

        resp = oauth.airtable.get(f'meta/bases/{base_id}/tables')
        resp.raise_for_status()
        tables = resp.json()['tables']
        suggestion = None
        if tables:
            suggestion = f'SELECT * FROM "{tables[0]["name"]}"'

        init_script = [
            ('CREATE CREDENTIALS ON "https://api.airtable.com" REMOTE %s', (create_auth_url("airtable"),)),
            ('CREATE PAGINATION ON "https://api.airtable.com" AS offset = json(offset)', None),
            ('CREATE SCHEME airtable AS https://api.airtable.com/v0/$PATH#records', None),
            (f"""CREATE SCHEMA WITH
                    TABLES AS (SELECT id, name FROM "https://api.airtable.com/v0/meta/bases/{base_id}/tables#tables")
                    COLUMNS AS (SELECT UNNEST(fields) FROM "https://api.airtable.com/v0/meta/bases/{base_id}/tables#tables" WHERE id = '$TABLE[id]')
                    ROWS AS (SELECT id, EXPAND(fields) FROM "https://api.airtable.com/v0/{base_id}/$TABLE[id]#records")
                """, None),
        ]

        sqldb = init_integration_db("airtable", base['name'], init_script, suggestion)

        return redirect(url_for("client", db=sqldb.slug))

    return render_template("airtable/setup.html", bases=bases)


app.register_blueprint(blueprint)
