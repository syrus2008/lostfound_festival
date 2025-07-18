import enum
from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum

class DepositType(enum.Enum):
    ID_CARD = 'id_card'
    CASH = 'cash'

class LoanStatus(enum.Enum):
    ACTIVE = 'active'
    PENDING_DELETION = 'pending_deletion'
    DELETED = 'deleted'

class HeadphoneLoan(db.Model):
    __tablename__ = 'headphone_loans'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    deposit_type = db.Column(db.Enum(DepositType), nullable=False)
    deposit_details = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    deposit_amount = db.Column(db.Numeric(10, 2), nullable=True)
    loan_date = db.Column(db.DateTime, nullable=False, default=db.func.now())
    return_date = db.Column(db.DateTime, nullable=True)
    signature = db.Column(db.Text, nullable=True)  # Image base64 de la signature
    id_card_photo = db.Column(db.Text, nullable=True)  # Image base64 de la CI
    status = db.Column(db.Enum(LoanStatus), nullable=False, default=LoanStatus.ACTIVE, index=True)
    previous_status = db.Column(db.Enum(LoanStatus), nullable=True)

    def __repr__(self):
        return f'<HeadphoneLoan {self.first_name} {self.last_name} ({self.status.value})>'

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f'<Category {self.name}>'

class Status(enum.Enum):
    LOST = 'lost'
    FOUND = 'found'
    RETURNED = 'returned'
    PENDING_DELETION = 'pending_deletion'  # En attente de suppression

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(Status), nullable=False, default=Status.LOST, index=True)
    previous_status = db.Column(db.Enum(Status), nullable=True)  # Statut original avant demande suppression
    title = db.Column(db.String(100), nullable=False)
    comments = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    date_reported = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    category = db.relationship('Category', backref=db.backref('items', lazy=True))
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_email = db.Column(db.String(150), nullable=True)
    reporter_phone = db.Column(db.String(50), nullable=True)
    photo_filename = db.Column(db.String(200), nullable=True)  # Pour compatibilité
    claimant_name = db.Column(db.String(100), nullable=True)
    claimant_email = db.Column(db.String(150), nullable=True)
    claimant_phone = db.Column(db.String(50), nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)
    return_comment = db.Column(db.Text, nullable=True)
    photos = db.relationship('ItemPhoto', backref='item', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Item {self.id} {self.title} ({self.status.value})>'


class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    lost_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    found_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    date_validated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lost = db.relationship('Item', foreign_keys=[lost_id])
    found = db.relationship('Item', foreign_keys=[found_id])

    def __repr__(self):
        return f'<Match Lost:{self.lost_id} Found:{self.found_id}>'

class ItemPhoto(db.Model):
    __tablename__ = 'item_photos'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    actions = db.relationship('ActionLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ActionLog(db.Model):
    __tablename__ = 'action_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
