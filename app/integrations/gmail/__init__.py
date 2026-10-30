from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from ..utils import create_or_update_user, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["gmail"] = {
    "title": "Gmail",
    "tagline": "Query your Google Sheets using SQL in real-time.",
    "url": "https://gmil.com/",
    "logo": "integrations/gmail/logo.png",
    "icon": "integrations/gmail/icon.png",
    "landing_url": "/gmail",
    "setup_url": "/gmail/setup",
    "help_url": "/gmail/help",
    "hidden": True
}

app.config["OAUTH_TOKENS_INTEGRATION_ALIAS"]["gmail"] = "google"

oauth.register('gmail',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': "email https://www.googleapis.com/auth/gmail.metadata",
    },
    authorize_params={
        'include_granted_scopes': 'true',
        'access_type': 'offline'
    })


blueprint = Blueprint('gmail', __name__, url_prefix="/gmail", template_folder='templates')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="gmail")


@blueprint.get('/help')
def help():
    return render_template("gmail/help.html")


@blueprint.get('/login')
def login():
    if request.args.get("setup"):
        session["gmail_setup"] = True
    redirect_uri = url_for('gmail.login_callback', _external=True)
    return oauth.gmail.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
def login_callback():
    token = oauth.gmail.authorize_access_token()
    r = oauth.gmail.get('https://www.googleapis.com/oauth2/v1/userinfo')
    sqldb = create_or_update_user(r.json()["email"], "google", token)
    if not session.pop("gmail_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for("gmail.setup"))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("google", lambda: url_for('gmail.login', setup="1"), scope="https://www.googleapis.com/auth/gmail.metadata")
def setup():
    resp = oauth.gmail.get('https://www.googleapis.com/oauth2/v1/userinfo')
    resp.raise_for_status()
    email = resp.json()['email']
    suggestion = 'SELECT * FROM "INBOX"'

    init_script = [
        ('CREATE CREDENTIALS ON "https://gmail.googleapis.com/gmail/v1" REMOTE %s', (create_auth_url("gmail"),)),
        ('CREATE PAGINATION ON "https://gmail.googleapis.com/gmail/v1/users/me/messages" AS pageToken = json(nextPageToken)', None),
        ("CREATE ALIAS threads AS https://gmail.googleapis.com/gmail/v1/users/me/threads/{id}?format=metadata#messages", None),
        ("CREATE ALIAS messages AS https://gmail.googleapis.com/gmail/v1/users/me/messages#messages", None),
        ("""CREATE SCHEMA WITH
                TABLES AS (SELECT id, name FROM "https://gmail.googleapis.com/gmail/v1/users/me/labels#labels")
                ROWS AS (
                    WITH m AS (
                        SELECT EXPAND(payload->headers, 'name', 'value')
                        FROM "https://gmail.googleapis.com/gmail/v1/users/me/messages?+#messages" messages
                        JOIN threads ON threads."?id" = messages.threadId
                        WHERE messages."?labelIds" = '$TABLE[id]'
                    )
                    SELECT "Date", "From", "To", "Subject" FROM m
                )
            """, None)
    ]

    sqldb = init_integration_db("gmail", email, init_script, suggestion)

    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
