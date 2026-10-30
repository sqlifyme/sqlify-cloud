from hyperflask import current_app
from flask_stripe_checkout import webhook
from .models import db, User
import datetime


def set_user_plan(user, plan, reset_period=False):
    if plan not in current_app.config["PLANS"]:
        raise ValueError(f"Invalid plan: {plan}")
    with db:
        user.max_queries = current_app.config["PLANS"][plan]["max_queries"]
        user.max_databases = current_app.config["PLANS"][plan]["max_databases"]
        user.plan = plan
        if reset_period:
            user.period_query_count = 0
            user.period_end = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        if current_app.config["PLANS"][plan]["connstr"]:
            user.create_db_password()
        else:
            user.desactivate_db_password()
        user.save()
    user.update_brevo()


@webhook.checkout_session_success()
def checkout_session_success(sender, session):
    with db:
        user = User.get(session["client_reference_id"])
        user.stripe_customer_id = session["customer"]["id"]
        plan = get_plan_from_subscription(session["subscription"])
        set_user_plan(user, plan, reset_period=True)


@webhook("customer.subscription.updated")
def subscription_updated(event):
    with db:
        plan = get_plan_from_subscription(event["data"]["object"])
        user = User.find_one(stripe_customer_id=event["data"]["object"]["customer"])
        if user and user.plan != plan:
            set_user_plan(user, plan, reset_period=True)


@webhook("customer.subscription.deleted")
def subscription_deleted(event):
    with db:
        user = User.find_one(stripe_customer_id=event["data"]["object"]["customer"])
        if user:
            set_user_plan(user, "free", reset_period=True)


@webhook("customer.deleted")
def customer_deleted(event):
    with db:
        user = User.find_one(stripe_customer_id=event["data"]["object"]["customer"])
        if user:
            user.stripe_customer_id = None
            set_user_plan(user, "free", reset_period=True)


def get_plan_from_subscription(sub):
    price_id = sub["items"]["data"][0]["price"]["id"]
    for plan, data in current_app.config["PLANS"].items():
        if data["price"] == price_id:
            return plan
    raise ValueError(f"Unknown price id: {price_id}")
