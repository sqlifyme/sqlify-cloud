from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from hyperflask_users import login_required
import requests
import time
from urllib.parse import urlencode
from ..utils import activate_user_integration, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["stripe"] = {
    "title": "Stripe",
    "tagline": "Query your Stripe data using SQL in real-time.",
    "url": "https://stripe.com/",
    "logo": "integrations/stripe/logo.png",
    "icon": "integrations/stripe/icon.webp",
    "landing_url": "/stripe",
    "setup_url": "/stripe/setup"
}

oauth.register('stripe',
    api_base_url='https://api.stripe.com/v1/',
    #authorize_url='https://marketplace.stripe.com/oauth/v2/authorize',
    access_token_url='https://api.stripe.com/v1/oauth/token')


blueprint = Blueprint('stripe', __name__, url_prefix='/stripe')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="stripe")


@blueprint.get('/login')
@login_required
def login():
    if request.args.get("setup"):
        session["stripe_setup"] = True
    redirect_uri = url_for('stripe.login_callback', _external=True)
    authorize_url = f"{oauth.stripe.authorize_url}?" + urlencode({"client_id": oauth.stripe.client_id, "redirect_uri": redirect_uri})
    return redirect(authorize_url)


@blueprint.get('/login/callback')
@login_required
def login_callback():
    r = requests.post(oauth.stripe.access_token_url, auth=(app.config["STRIPE_API_KEY"], ''), data={"code": request.values['code'], "grant_type": "authorization_code"})
    r.raise_for_status()
    token = r.json()
    token["expires_at"] = time.time() + 3600
    sqldb = activate_user_integration("stripe", token)
    if not session.pop("stripe_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('stripe.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("stripe", lambda: url_for('stripe.login', setup=1))
def setup():
    init_script = [
        ('CREATE CREDENTIALS ON "https://api.stripe.com/v1" REMOTE %s', (create_auth_url("stripe"),)),
        #('CREATE PAGINATION ON "https://app.stripe.com/api/1.0" AS starting_after = json(data[-1:].id)', None),
        ('CREATE VIEW Customers AS SELECT * FROM "https://api.stripe.com/v1/customers#data"', None),
        ('CREATE VIEW Charges AS SELECT * FROM "https://api.stripe.com/v1/charges#data"', None),
        ('CREATE VIEW Disputes AS SELECT * FROM "https://api.stripe.com/v1/disputes#data"', None),
        ('CREATE VIEW Invoices AS SELECT * FROM "https://api.stripe.com/v1/invoices#data"', None),
        ('CREATE VIEW Products AS SELECT * FROM "https://api.stripe.com/v1/products#data"', None),
        ('CREATE VIEW Subscriptions AS SELECT * FROM "https://api.stripe.com/v1/subscriptions#data"', None)
    ]

    sqldb = init_integration_db("stripe", "Stripe", init_script, "SELECT * FROM Customers")
    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
