from hyperflask.factory import app
from hyperflask import jsonify, request, abort, make_response, send_from_directory
from hyperflask.utils.tokens import load_token
from hyperflask_users import user_signed_up, login, current_user
from authlib.oauth2.auth import OAuth2Token
from . import sqlify
from .models import User, UserOauthTokens, Database, NotebookQuery
from .oauth import oauth


@user_signed_up.connect
def on_user_signed_up(app, user):
    with app.db:
        user.create_db_role()
    if not user.signup_using:
        with app.db:
            Database.create(user, "First Database")
    user.update_brevo()


@app.route('/db-auth', methods=['POST'])
@app.route('/sqletl-db-auth', methods=['POST']) # legacy
def db_auth():
    secret, user_id, integration = load_token(request.args["token"])
    if secret != app.config["SQLIFY_AUTH_SECRET"]:
        abort(404)
    user = User.get(user_id)
    if integration in oauth._registry:
        login(user)
        client = oauth.create_client(integration)
        integration = app.config["OAUTH_TOKENS_INTEGRATION_ALIAS"].get(integration, integration)
        token = UserOauthTokens.find_one_for_current_user(integration=integration)
        with client._get_oauth_client(**client.load_server_metadata()) as session:
            session.ensure_active_token(OAuth2Token.from_dict(token.to_token()))
        token.refresh()
    else:
        token = UserOauthTokens.find_one(user_id=user_id, integration=integration)
    return jsonify({
        "type": "token",
        "value": token.access_token
    })


@app.route('/csv-export/<db>/<qid>.csv')
def csv_export(db, qid):
    sqldb = Database.find_for_current_user_or_404(db)
    query = NotebookQuery.find_one_or_404(id=qid, database_id=sqldb.id)
    results, columns = sqlify.query(query.stmt, sqldb.slug, current_user.db_role)
    resp = make_response(sqlify.iter_results_as_csv(results, columns if request.args.get('header', '1') == '1' else None))
    resp.mimetype = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=data.csv'
    return resp


@app.route('/docs/')
@app.route('/docs/<path:path>')
def docs(path="index.html"):
    if not path.startswith("assets/"):
        if path.endswith("/"):
            path += "index.html"
        elif not path.endswith(".html"):
            path += ".html"
    return send_from_directory('docs', path)
