from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from hyperflask_users import login_required
from ..utils import activate_user_integration, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["slack"] = {
    "title": "Slack",
    "tagline": "Query your Slack channels using SQL in real-time.",
    "url": "https://slack.com/",
    "logo": "integrations/slack/logo.png",
    "icon": "integrations/slack/icon.png",
    "landing_url": "/slack",
    "setup_url": "/slack/setup"
}

oauth.register('slack',
    api_base_url='https://slack.com/api/',
    authorize_url='https://slack.com/oauth/v2/authorize',
    access_token_url='https://slack.com/api/oauth.v2.access',
    client_kwargs={
        'scope': "team:read,channels:read,channels:history,channels:join",
    })


blueprint = Blueprint('slack', __name__, url_prefix='/slack')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="slack")


@blueprint.get('/login')
@login_required
def login():
    if request.args.get("setup"):
        session["slack_setup"] = True
    redirect_uri = url_for('slack.login_callback', _external=True)
    return oauth.slack.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
@login_required
def login_callback():
    token = oauth.slack.authorize_access_token()
    token["token_type"] = "Bearer"
    sqldb = activate_user_integration("slack", token)
    if not session.pop("slack_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('slack.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("slack", lambda: url_for('slack.login', setup=1))
def setup():
    resp = oauth.slack.get(f'team.info')
    resp.raise_for_status()
    team_name = resp.json()['team']['name']

    resp = oauth.slack.get('conversations.list')
    resp.raise_for_status()
    channels = resp.json()['channels']
    suggestion = None
    for channel in channels:
        if not suggestion:
            suggestion = f'SELECT * FROM "{channel["name"]}"'
        oauth.slack.post("conversations.join", params={"channel": channel["id"]})

    init_script = [
        ('CREATE CREDENTIALS ON "https://slack.com/api" REMOTE %s', (create_auth_url("slack"),)),
        ('CREATE PAGINATION ON "https://slack.com/api/" AS cursor = json(response_metadata.next_cursor)', None),
        (f"""CREATE SCHEMA WITH
                TABLES AS (SELECT id, name FROM "https://slack.com/api/conversations.list#channels")
                ROWS AS (SELECT * FROM "https://slack.com/api/conversations.history#messages" WHERE "?channel" = '$TABLE[id]')
            """, None),
    ]

    sqldb = init_integration_db("slack", team_name, init_script, suggestion)

    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
