from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Optional, EqualTo
from flask_wtf.file import FileAllowed
from wtforms import MultipleFileField

from wtforms import RadioField, DecimalField, IntegerField

from flask_wtf.file import FileField, FileAllowed, FileRequired

class HeadphoneLoanForm(FlaskForm):
    first_name = StringField('Prénom', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Téléphone', validators=[DataRequired(), Length(max=50)])
    deposit_type = RadioField('Type de caution', choices=[('id_card', "Carte d'identité"), ('cash', 'Caution en argent')], validators=[DataRequired()])
    deposit_amount = DecimalField('Montant de la caution (€)', places=2, validators=[Optional()])
    quantity = IntegerField('Nombre de casques prêtés', default=1, validators=[DataRequired()])
    deposit_details = StringField('Détails de la caution', validators=[Length(max=200)])
    id_card_photo = FileField("Photo de la carte d'identité", validators=[FileAllowed(['jpg', 'jpeg', 'png'], "Images uniquement")])
    submit = SubmitField('Enregistrer le prêt')

class SimpleCsrfForm(FlaskForm):
    pass

class ItemForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired(), Length(max=100)])
    comments = TextAreaField('Description / Commentaires', validators=[Length(max=500)])
    location = StringField('Lieu (ex. "Entrée Nord")', validators=[Length(max=100)])
    category = SelectField('Catégorie', coerce=lambda x: int(x) if x else None, validators=[DataRequired(message='Veuillez sélectionner une catégorie')], choices=[])
    new_category = StringField('Nouvelle catégorie', validators=[
        Optional(),
        Length(max=50, message='Le nom de la catégorie ne doit pas dépasser 50 caractères')
    ])
    reporter_name = StringField('Nom du déclarant', validators=[DataRequired(), Length(max=100)])
    reporter_email = StringField('Email du déclarant', validators=[Optional(), Email(), Length(max=150)])
    reporter_phone = StringField('Téléphone du déclarant', validators=[Length(max=50)])
    photos = MultipleFileField('Photos de l\'objet (jpg/png)', validators=[FileAllowed(['jpg','jpeg','png'])])
    submit = SubmitField('Valider')
    
    def __init__(self, *args, **kwargs):
        super(ItemForm, self).__init__(*args, **kwargs)
        # Charger les catégories existantes
        from models import Category
        categories = Category.query.order_by('name').all()
        self.category.choices = [('', 'Sélectionnez une catégorie')] + [(str(c.id), c.name) for c in categories]

class ClaimForm(FlaskForm):
    claimant_name = StringField('Votre nom', validators=[DataRequired(), Length(max=100)])
    claimant_email = StringField('Votre email', validators=[DataRequired(), Email(), Length(max=150)])
    claimant_phone = StringField('Votre téléphone', validators=[Length(max=50)])
    photos = MultipleFileField('Photos de restitution (jpg/png)', validators=[FileAllowed(['jpg','jpeg','png'])])
    submit = SubmitField('Réclamer')

class ConfirmReturnForm(FlaskForm):
    return_comment = TextAreaField('Commentaire de restitution', validators=[Length(max=500)])
    submit = SubmitField('Confirmer restitution')

class MatchForm(FlaskForm):
    match_with = SelectField(
        "Objet correspondant",
        coerce=int,
        validators=[DataRequired()]
    )
    submit_match = SubmitField("Confirmer correspondance")

class DeleteForm(FlaskForm):
    delete_password = StringField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Supprimer définitivement')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Connexion')

class RegisterForm(FlaskForm):
    first_name = StringField('Prénom', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    from wtforms.validators import Regexp
    password = PasswordField('Mot de passe', validators=[
        DataRequired(),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères.'),
        Regexp(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d)(?=.*[!@#$%^&*()_+\-=\\[\\]{};':\",.<>/?]).+$", message="Le mot de passe doit contenir une majuscule, une minuscule, un chiffre et un caractère spécial.")
    ])
    password2 = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Créer un compte administrateur')
    submit = SubmitField('Créer le compte')
