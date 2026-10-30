from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, session
from app.oauth import oauth
from hyperflask_users import login_required
from urllib.parse import urlencode, quote, urlparse, parse_qs
from ..utils import activate_user_integration, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["hubspot"] = {
    "title": "Hubspot",
    "tagline": "Query Hubspot CRM using SQL in real-time.",
    "url": "https://hubspot.com/",
    "logo": "integrations/hubspot/logo.png",
    "icon": "integrations/hubspot/icon.png",
    "landing_url": "/hubspot",
    "setup_url": "/hubspot/setup"
}

oauth.register('hubspot',
    api_base_url='https://api.hubapi.com',
    authorize_url='https://app.hubspot.com/oauth/authorize',
    access_token_url='https://api.hubapi.com/oauth/v1/token',
    scope="crm.objects.contacts.read oauth")


blueprint = Blueprint('hubspot', __name__, url_prefix='/hubspot')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="hubspot")


@blueprint.get('/login')
@login_required
def login():
    if request.args.get("setup"):
        session["hubspot_setup"] = True
    redirect_uri = url_for('hubspot.login_callback', _external=True)
    rv = oauth.hubspot.create_authorization_url(redirect_uri)
    authorize_url = urlparse(rv["url"])
    authorize_url = authorize_url._replace(query=urlencode(parse_qs(authorize_url.query), doseq=True, quote_via=quote))
    rv["url"] = authorize_url.geturl()
    oauth.hubspot.save_authorize_data(redirect_uri=redirect_uri, **rv)
    print(rv["url"])
    return redirect(rv["url"])


@blueprint.get('/login/callback')
@login_required
def login_callback():
    token = oauth.hubspot.authorize_access_token()
    print(token)
    sqldb = activate_user_integration("hubspot", token)
    if not session.pop("hubspot_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('hubspot.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("hubspot", lambda: url_for('hubspot.login', setup=1))
def setup():
    init_script = [
        ('CREATE CREDENTIALS ON "https://api.hubapi.com" REMOTE %s', (create_auth_url("hubspot"),)),
        ('CREATE PAGINATION ON "https://api.hubapi.com" AS after = json(paging.next.after)', None),
        ('CREATE VIEW Contacts AS SELECT id, expand(properties) FROM "https://api.hubapi.com/crm/v3/objects/contacts#results"', None),
    ]

    sqldb = init_integration_db("hubspot", "Hubspot", init_script, "SELECT * FROM Contacts")

    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
