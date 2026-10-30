from flask_stripe_checkout.subscription import subscription_checkout, redirect_to_customer_portal, upgrade_subscription

if current_user.stripe_customer_id:
    return_url = url_for("client", _external=True)
    if request.values.get("plan"):
        page.respond(upgrade_subscription(current_user.stripe_customer_id,
                                          current_app.config["PLANS"][request.values.get("plan")]["price"],
                                          current_user.id, return_url,
                                          proration_behavior="always_invoice"))
    else:
        page.respond(redirect_to_customer_portal(current_user.stripe_customer_id, return_url))
else:
    plan = request.values.get('plan', 'premium')
    if plan not in current_app.config["PLANS"]:
        page.abort(404)
    page.respond(subscription_checkout(current_app.config["PLANS"][plan]["price"], current_user.id,
                                       customer_email=current_user.email,
                                       allow_promotion_codes=True))
