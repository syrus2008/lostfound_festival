import os
import imghdr
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO
import magic
import logging

logger = logging.getLogger(__name__)

def is_allowed_file(filename, allowed_extensions=None):
    """
    Vérifie si le fichier a une extension autorisée.
    """
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions

def validate_image(stream):
    """
    Valide qu'un fichier est bien une image.
    """
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    
    if not format:
        return None
    
    return '.' + (format if format != 'jpeg' else 'jpg')

def sanitize_filename(filename):
    """
    Nettoie le nom de fichier pour éviter les problèmes de sécurité.
    """
    # Supprime les chemins de répertoire
    filename = os.path.basename(filename)
    # Nettoie le nom de fichier
    filename = secure_filename(filename)
    # Limite la longueur du nom de fichier
    max_length = 100
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename

def check_file_type(file_stream, allowed_mime_types=None):
    """
    Vérifie le type MIME réel du fichier.
    """
    if allowed_mime_types is None:
        allowed_mime_types = {
            'image/jpeg', 'image/png', 'image/gif',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
    
    # Lire les premiers octets pour l'analyse
    header = file_stream.read(1024)
    file_stream.seek(0)
    
    # Utiliser python-magic pour détecter le type MIME
    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(header)
    
    return file_type in allowed_mime_types, file_type

def process_image(file_stream, max_size=(1200, 1200), quality=85):
    """
    Traite une image pour la redimensionner et la compresser.
    """
    try:
        img = Image.open(file_stream)
        
        # Convertir en RGB si nécessaire (pour les PNG avec transparence)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Redimensionner l'image en conservant les proportions
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Sauvegarder dans un BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return output
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'image: {str(e)}")
        return None

def secure_file_upload(file, upload_folder, allowed_extensions=None, max_size=30 * 1024 * 1024):
    """
    Gère un téléchargement de fichier de manière sécurisée.
    """
    try:
        # Vérifie si un fichier a été soumis
        if not file or file.filename == '':
            return None, "Aucun fichier sélectionné"
        
        # Vérifie l'extension du fichier
        if not is_allowed_file(file.filename, allowed_extensions):
            return None, "Type de fichier non autorisé"
        
        # Vérifie la taille du fichier
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > max_size:
            return None, f"Fichier trop volumineux (max {max_size/1024/1024} Mo)"
        
        # Vérifie le type MIME réel du fichier
        is_valid, file_type = check_file_type(file.stream)
        if not is_valid:
            return None, f"Type de fichier non autorisé: {file_type}"
        
        # Nettoie le nom du fichier
        filename = sanitize_filename(file.filename)
        
        # Crée le dossier de destination s'il n'existe pas
        os.makedirs(upload_folder, exist_ok=True)
        
        # Chemin complet du fichier
        filepath = os.path.join(upload_folder, filename)
        
        # Traitement des images
        if file_type.startswith('image/'):
            processed_image = process_image(file.stream)
            if processed_image:
                with open(filepath, 'wb') as f:
                    f.write(processed_image.read())
                return filename, None
            else:
                return None, "Erreur lors du traitement de l'image"
        else:
            # Pour les autres types de fichiers, les sauvegarder tels quels
            file.save(filepath)
            return filename, None
    
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier: {str(e)}")
        return None, f"Erreur lors du téléchargement du fichier: {str(e)}"
