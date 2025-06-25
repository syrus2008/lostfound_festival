from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Optional, EqualTo
from flask_wtf.file import FileAllowed
from wtforms import MultipleFileField

class HeadphoneLoanForm(FlaskForm):
    first_name = StringField('Prénom', validators=[DataRequired(), Length(max=100)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Téléphone', validators=[DataRequired(), Length(max=50)])
    deposit_type = SelectField('Type de caution', choices=[('id_card', 'Carte d\'identité'), ('cash', 'Caution en argent')], validators=[DataRequired()])
    deposit_details = StringField('Détails de la caution', validators=[Length(max=200)])
    submit = SubmitField('Enregistrer le prêt')

class SimpleCsrfForm(FlaskForm):
    pass

class ItemForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired(), Length(max=100)])
    comments = TextAreaField('Description / Commentaires', validators=[Length(max=500)])
    location = StringField('Lieu (ex. “Entrée Nord”)', validators=[Length(max=100)])
    category = SelectField('Catégorie', coerce=int, validators=[DataRequired()])
    reporter_name = StringField('Nom du déclarant', validators=[DataRequired(), Length(max=100)])
    reporter_email = StringField('Email du déclarant', validators=[Optional(), Email(), Length(max=150)])
    reporter_phone = StringField('Téléphone du déclarant', validators=[Length(max=50)])
    photos = MultipleFileField('Photos de l’objet (jpg/png)', validators=[FileAllowed(['jpg','jpeg','png'])])
    submit = SubmitField('Valider')

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
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Créer un compte administrateur')
    submit = SubmitField('Créer le compte')
