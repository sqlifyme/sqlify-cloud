from hyperflask.factory import app
from hyperflask import url_for, Blueprint, render_template, request, redirect
from hyperflask_users import login_required
from app.models import UserOauthTokens, Database
from ..utils import create_auth_url, integration_login_required, init_integration_db


app.config["INTEGRATIONS"]["openai"] = {
    "title": "OpenAI",
    "tagline": "Use ChatGPT as part of your SQL queries.",
    "url": "https://openai.com",
    "logo": "integrations/openai/logo.png",
    "icon": "integrations/openai/icon.png",
    "landing_url": "/openai",
    "setup_url": "/openai/setup"
}

blueprint = Blueprint('openai', __name__, url_prefix='/openai', template_folder='templates')


@blueprint.get('/')
def index():
    return render_template("integration_builtin.html", integration="openai")


@blueprint.route('/login', methods=['GET', 'POST'])
@login_required
def login():
    if request.method == 'POST':
        apikey = request.form['apikey']
        UserOauthTokens.save_token("openai", apikey)
        sqldb = Database.find_one_for_current_user(integration="openai")
        if not request.args.get("setup") and sqldb:
            return redirect(url_for("client", db=sqldb.slug))
        return redirect(url_for('openai.setup'))
    return render_template("openai/login.html")


@blueprint.route('/setup', methods=['GET', 'POST'])
@integration_login_required("openai", lambda: url_for('openai.login', setup=1))
def setup():
    init_script = [
        ('CREATE CREDENTIALS ON "https://api.openai.com" REMOTE %s', (create_auth_url("openai"),)),
        (f"""CREATE SCHEMA WITH
                TABLES AS (SELECT id AS name FROM "https://api.openai.com/v1/models#data")
                ROWS AS (SELECT choices->0->message->content AS assistant FROM "POST https://api.openai.com/v1/chat/completions?JSON&+" WHERE "?model" = '$TABLE[name]')
            """, None),
    ]

    suggestion = 'SELECT * FROM "gpt-3.5-turbo" WHERE "?messages[]" = \'{"role": "user", "content": "Tell me a joke"}\''
    sqldb = init_integration_db("openai", "ChatGPT", init_script, suggestion)

    return redirect(url_for("client", db=sqldb.slug))


app.register_blueprint(blueprint)
