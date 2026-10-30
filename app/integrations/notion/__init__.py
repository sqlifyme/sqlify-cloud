from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect, abort, session
from app.oauth import oauth
from hyperflask_users import current_user
from ..utils import create_or_update_user, create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["notion"] = {
    "title": "Notion",
    "tagline": "Query your Notion databases using SQL in real-time.",
    "url": "https://notion.so/",
    "logo": "integrations/notion/logo.png",
    "icon": "integrations/notion/icon.png",
    "landing_url": "/notion",
    "setup_url": "/notion/setup"
}

oauth.register('notion',
    api_base_url='https://api.notion.com/v1/',
    authorize_url='https://api.notion.com/v1/oauth/authorize',
    access_token_url='https://api.notion.com/v1/oauth/token',
    authorize_params={
        "owner": "user"
    })

blueprint = Blueprint('notion', __name__, url_prefix='/notion')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="notion")


@blueprint.get('/login')
def login():
    if request.args.get("setup"):
        session["notion_setup"] = True
    redirect_uri = url_for('notion.login_callback', _external=True)
    return oauth.notion.authorize_redirect(redirect_uri)


@blueprint.get('/login/callback')
def login_callback():
    token = oauth.notion.authorize_access_token()
    email = None
    if not current_user.is_authenticated:
        try:
            email = token["owner"]["user"]["person"]["email"]
        except:
            return "Notion login failed. Please try again."
    sqldb = create_or_update_user(email, "notion", token)
    if not session.pop("notion_setup", False) and sqldb:
        return redirect(url_for("client", db=sqldb.slug))
    return redirect(url_for('notion.setup'))


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("notion", lambda: url_for('notion.login', setup=1))
def setup():
    init_script = [
        ('CREATE CREDENTIALS ON "https://api.notion.com/v1" REMOTE %s', (create_auth_url("notion"),)),
        ('CREATE PAGINATION ON "https://api.notion.com/v1" AS start_cursor = json(next_cursor)', None),
        ('CREATE HEADER ON "https://api.notion.com/v1" AS Notion-Version: 2022-06-28', None),
        (f"""CREATE SCHEMA WITH
                TABLES AS (SELECT id, title->0->plain_text AS name FROM "POST https://api.notion.com/v1/search?JSON#results" WHERE "?filter.value" = 'database' AND "?filter.property" = 'object')
                COLUMNS AS (WITH props AS (SELECT unnest(properties) FROM "https://api.notion.com/v1/databases/$TABLE[id]") SELECT value->id AS id, key AS name FROM props)
                ROWS AS (SELECT id, expand(properties) FROM "POST https://api.notion.com/v1/databases/$TABLE[id]/query#results")
            """, None),
    ]

    sqldb = init_integration_db("notion", "Notion", init_script)
    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
