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
    status = db.Column(db.Enum(Status), nullable=False, default=Status.LOST)
    title = db.Column(db.String(100), nullable=False)
    comments = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    date_reported = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('items', lazy=True))
    reporter_name = db.Column(db.String(100), nullable=False)
    reporter_email = db.Column(db.String(150), nullable=False)
    reporter_phone = db.Column(db.String(50), nullable=True)
    photo_filename = db.Column(db.String(200), nullable=True)
    claimant_name = db.Column(db.String(100), nullable=True)
    claimant_email = db.Column(db.String(150), nullable=True)
    claimant_phone = db.Column(db.String(50), nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)
    return_comment = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Item {self.id} {self.title} ({self.status.value})>'
