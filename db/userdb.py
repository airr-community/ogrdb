# ORM definitions for user management

from app import db
from flask_security import UserMixin, RoleMixin

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(250))

    def __repr__(self):
        return('%s' % (self.name))

roles_submissions = db.Table('roles_submissions',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('submission_id', db.Integer(), db.ForeignKey('submission.id')))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    name = db.Column(db.String(255))
    address = db.Column(db.String(250))
    accepted_terms = db.Column(db.Boolean)
    reduce_emails = db.Column(db.Boolean)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    delegated_submissions = db.relationship('Submission', secondary=roles_submissions, backref=db.backref('delegates', lazy='dynamic'))


    def __repr__(self):
        return('%s' % (self.email))
