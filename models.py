import enum
from datetime import datetime
from app import db

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

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(Status), nullable=False, default=Status.LOST, index=True)
    title = db.Column(db.String(100), nullable=False)
    comments = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    date_reported = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    category = db.relationship('Category', backref=db.backref('items', lazy=True))
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_email = db.Column(db.String(150), nullable=False)
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
