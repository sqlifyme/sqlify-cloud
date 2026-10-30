from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
import urllib.parse
from ..utils import create_or_update_user, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["gsheets"] = {
    "title": "Google Sheets",
    "tagline": "Query your Google Sheets using SQL in real-time.",
    "url": "https://google.com/",
    "logo": "integrations/gsheets/logo.svg",
    "icon": "integrations/gsheets/icon.webp",
    "landing_url": "/sheets",
    "setup_url": "/sheets/setup",
    "help_url": "/sheets/help",
    "hidden": True
}

app.config["OAUTH_TOKENS_INTEGRATION_ALIAS"]["gsheets"] = "google"

oauth.register('gsheets',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': "email https://www.googleapis.com/auth/spreadsheets.readonly"
    },
    authorize_params={
        'include_granted_scopes': 'true',
        'access_type': 'offline'
    })


blueprint = Blueprint('gsheets', __name__, url_prefix="/sheets", template_folder='templates')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="gsheets")


@blueprint.get('/help')
def help():
    return render_template("gsheets/help.html")


@blueprint.get('/login')
def login():
    if request.args.get("setup"):
        session["gsheets_setup"] = True
    redirect_uri = url_for('gsheets.login_callback', _external=True)
    return oauth.gsheets.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
def login_callback():
    token = oauth.gsheets.authorize_access_token()
    r = oauth.gmail.get('https://www.googleapis.com/oauth2/v1/userinfo')
    sqldb = create_or_update_user(r.json()["email"], "google", token)
    if not session.pop("gsheets_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for("gsheets.setup"))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("google", lambda: url_for('gsheets.login', setup="1"), scope="https://www.googleapis.com/auth/spreadsheets.readonly")
def setup():
    if request.method == 'POST':
        sheet_id = request.form['sheet_id']
        if sheet_id.startswith("https://docs.google.com/spreadsheets/d/"):
            parts = urllib.parse.urlparse(sheet_id)
            sheet_id = parts.path.strip("/").split("/")[2]

        resp = oauth.gsheets.get(f'https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}', params={"fields": "properties(title),sheets(properties(sheetId,title))"})
        resp.raise_for_status()
        book = resp.json()
        sheets = book["sheets"]
        suggestion = None
        if sheets:
            suggestion = f'SELECT * FROM "{sheets[0]["properties"]["title"]}"'

        init_script = [
            ('CREATE CREDENTIALS ON "gsheets://" REMOTE %s', (create_auth_url("gsheets"),)),
            (f"""CREATE SCHEMA WITH
                    TABLES AS (SELECT sheetId AS id, title AS name FROM "gsheets://{sheet_id}")
                    ROWS AS (SELECT * FROM "gsheets://{sheet_id}/$TABLE[id]{'?colnames=1' if request.form.get('colnames') == '1' else ''}")
            """, None)
        ]

        sqldb = init_integration_db("gsheets", book['properties']['title'], init_script, suggestion)

        return redirect(url_for("client", db=sqldb.slug))

    return render_template("gsheets/setup.html")


app.register_blueprint(blueprint)
