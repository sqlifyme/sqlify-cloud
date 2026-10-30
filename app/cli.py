from hyperflask.factory import app
import click
from .models import User
from .billing import set_user_plan


@app.cli.command()
@click.argument("email")
def upgrade_to_premium(email):
    with app.db:
        user = User.find_one(email=email)
        if not user:
            print("User not found")
            return
        set_user_plan(user, "premium")
