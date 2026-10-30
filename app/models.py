from hyperflask.factory import db
from hyperflask import slugify, current_app
from hyperflask_users import UserMixin, UserRelatedMixin, current_user
from contextlib import contextmanager
import uuid
import datetime
import brevo_python
from .sqlify import connect


class User(UserMixin, db.Model):
    __table__ = 'users'

    stripe_customer_id: str
    plan: str = db.Column(default='free')
    tutorial_completed: bool = db.Column(default=False)
    first_integration_completed: bool = db.Column(default=False)
    period_query_count: int = db.Column(default=0)
    period_end: datetime.datetime = db.Column(default=lambda: datetime.datetime.utcnow() + datetime.timedelta(days=30))
    max_queries: int = db.Column(default=50)
    max_databases: int = db.Column(default=-1)
    theme: str = db.Column(default='auto')
    db_role: str
    db_password: str

    oauth_tokens = db.Relationship('UserOauthTokens', 'user_id')
    databases = db.Relationship('Database', 'user_id')

    @db.fetchscalar
    def count_databases(self):
        "SELECT COUNT(*) FROM database WHERE user_id = %(self.id)s"

    def incr_query_count(self):
        "UPDATE SET period_query_count = period_query_count + 1 WHERE id = %(self.id)s RETURNING period_query_count"

    @property
    def is_paying(self):
        return self.plan != 'free'

    @property
    def can_create_database(self):
        return self.max_databases == -1 or self.count_databases() < self.max_databases

    @property
    def can_perform_queries(self):
        return self.max_queries == -1 or self.period_query_count < self.max_queries

    def create_db_role(self):
        self.db_role = str(uuid.uuid4()).split('-')[0]
        with connect() as cur:
            cur.execute(f"CREATE ROLE %s", (self.db_role,))
        self.save()

    def create_db_password(self):
        if not self.db_password:
            self.db_password = str(uuid.uuid4()).split('-')[0]
        with connect() as cur:
            cur.execute(f"ALTER ROLE %s PASSWORD %s", (self.db_role, self.db_password))
        self.save()

    def desactivate_db_password(self):
        if not self.db_password:
            return
        with connect() as cur:
            cur.execute(f"ALTER ROLE %s PASSWORD NULL", (self.db_role,))

    def update_brevo(self):
        if not current_app.config.get('BREVO_LIST_ID'):
            return
        try:
            config = brevo_python.Configuration()
            config.api_key['api-key'] = current_app.config['BREVO_API_KEY']
            api = brevo_python.ContactsApi(brevo_python.ApiClient(config))
            api.create_contact(brevo_python.CreateContact(
                update_enabled=True,
                email_blacklisted=False,
                email=self.email,
                list_ids=[current_app.config['BREVO_LIST_ID']],
                attributes=dict(self.brevo_props)
            ))
        except Exception as e:
            current_app.logger.error(e)

    @property
    def brevo_props(self):
        return [
            ("ORG_PLAN", self.plan),
            ("ONBOARDED", bool(self.tutorial_completed)),
        ]

    def delete_brevo(self):
        if not current_app.config.get('BREVO_LIST_ID'):
            return
        try:
            config = brevo_python.Configuration()
            config.api_key['api-key'] = current_app.config['BREVO_API_KEY']
            api = brevo_python.ContactsApi(brevo_python.ApiClient(config))
            api.delete_contact(self.email)
        except Exception as e:
            current_app.logger.error(e)


class UserOauthTokens(UserRelatedMixin, db.Model):
    __table__ = 'user_oauth_tokens'

    access_token: str = db.Column(type=db.Encrypted())
    expires_at: int
    refresh_token: str = db.Column(type=db.Encrypted())
    refresh_expires_in: int
    token_type: str
    scope: str
    integration: str

    def to_token(self):
        o = dict(
            access_token=self.access_token,
            token_type=self.token_type,
            refresh_token=self.refresh_token,
        )
        if self.expires_at:
            o['expires_at'] = self.expires_at
        if self.refresh_expires_in:
            o['refresh_expires_in'] = self.refresh_expires_in
        if self.scope:
            o['scope'] = self.scope
        return o

    @classmethod
    def save_from_oauth(cls, name, token):
        with db:
            saved_token = cls.find_one_for_current_user(integration=name)
            if not saved_token:
                saved_token = cls(user_id=current_user.id, integration=name)
            saved_token.access_token = token['access_token']
            saved_token.expires_at = token.get('expires_at')
            saved_token.refresh_token = token.get('refresh_token')
            saved_token.refresh_expires_in = token.get('refresh_expires_in')
            saved_token.token_type = token.get('token_type')
            saved_token.scope = token.get('scope')
            saved_token.save()
            return saved_token

    @classmethod
    def save_token(cls, name, token):
        with db:
            saved_token = cls.find_one_for_current_user(integration=name)
            if not saved_token:
                saved_token = cls(user_id=current_user.id, integration=name)
            saved_token.access_token = token
            saved_token.save()
            return saved_token

    @classmethod
    def fetch_token_for_oauth(cls, name):
        name = current_app.config["OAUTH_TOKENS_INTEGRATION_ALIAS"].get(name, name)
        return cls.find_one_for_current_user(integration=name).to_token()

    @classmethod
    def update_token_from_oauth(cls, name, token, refresh_token=None, access_token=None):
        name = current_app.config["OAUTH_TOKENS_INTEGRATION_ALIAS"].get(name, name)
        with db:
            item = cls.find_one_for_current_user(integration=name)
            item.access_token = token['access_token']
            item.expires_at = token['expires_at']
            item.refresh_token = token.get('refresh_token')
            item.refresh_expires_in = token.get('refresh_expires_in')
            item.scope = token.get('scope')
            item.save()


class Database(UserRelatedMixin, db.Model):
    __table__ = 'databases'

    name: str
    slug: str
    integration: str
    suggestion: str
    init_script: str

    @classmethod
    def create(cls, user, name, **kwargs):
        slug = "%s-%s" % (str(uuid.uuid4()).split('-')[0], slugify(name))
        with connect() as cur:
            cur.execute("CREATE DATABASE %s", (slug,))
            cur.execute("GRANT ADMIN ON %s TO %s AS %s", (slug, user.db_role, name))
        return super().create(user_id=user.id, name=name, slug=slug, **kwargs)

    @classmethod
    def find_for_current_user_or_404(cls, slug=None):
        if slug:
            return super().find_one_for_current_user_or_404(slug=slug)
        return super().find_all_for_current_user(order_by="id").first()

    @contextmanager
    def connect(self):
        with connect(self.slug) as cur:
            yield cur

    def drop_database(self):
        with connect() as cur:
            cur.execute("DROP DATABASE %s", (self.slug,))


class NotebookQuery(db.Model):
    __table__ = 'notebook_queries'

    database_id: int
    stmt: str
    created_at: datetime.datetime = db.Column(default=datetime.datetime.utcnow)
