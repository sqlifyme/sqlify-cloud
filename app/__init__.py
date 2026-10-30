from hyperflask import Hyperflask, factory
from hyperflask_users import Users
from flask_stripe_checkout import StripeCheckout


def create_app():
    app = factory.app = Hyperflask("app", static_folder="../public", static_url_path="/static", config={
        "SITE_TITLE": "SQLify",
        "ASSETS_TAILWIND": "main.css",
        "SQLORM_URI": "sqlite://database/app.db?pragma[foreign_keys]=ON",
        "USERS_SIGNUP_DEFAULT_REDIRECT_URL": "/client",
        "STRIPE_CHECKOUT_SUCCESS_REDIRECT": "/client",
        "INTEGRATIONS": {},
        "OAUTH_TOKENS_INTEGRATION_ALIAS": {},
    })
    factory.db = app.db
    Users(app)
    StripeCheckout(app)
    from . import models, routes, billing, integrations
    return app
