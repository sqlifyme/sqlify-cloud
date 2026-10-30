from hyperflask.factory import app
from .models import UserOauthTokens
from authlib.integrations.flask_client import OAuth


oauth = OAuth(app, fetch_token=UserOauthTokens.fetch_token_for_oauth, update_token=UserOauthTokens.update_token_from_oauth)
