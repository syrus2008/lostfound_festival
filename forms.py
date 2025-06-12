from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FileField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional
from flask_wtf.file import FileAllowed
from wtforms import MultipleFileField

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
