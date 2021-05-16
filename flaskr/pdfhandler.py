import functools

from logging import error, log

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from flask.globals import current_app

from werkzeug.utils import secure_filename

from flaskr.auth import login_required

from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

from os import mkdir, path, listdir, remove

import re

from pdf2image import convert_from_path, convert_from_bytes

import PyPDF2

bp = Blueprint('pdfhandler', __name__, url_prefix='/pdfhandler')

# -- HELPER FUNCTIONS

def allowed_file(filename):
    """Checks if the file name is of an allowed type"""

    # Use rsplit bc can limit splits to 1
    return ('.' in filename) and (filename.rsplit('.', 1)[1].lower() in current_app.config["UPLOAD_EXTENSIONS"])

def validate_pdf(stream):
    """Takes in a file stream and outputs whether it is a valid pdf and what kind of placement the %PDF has in the header

    Parameters
    ----------
    stream : bytes
        pdf files stream

    Returns
    -------
    tuple
        a 2-element tuple where the first element is whether or not it is valid and the second is where the %PDF marker is located
    """

    # Get the first 4 bytes 
    first_four_bytes = stream.read(4)
    stream.seek(0)

    if b"%PDF" == first_four_bytes:
        return (True, "regular")

    # Regex to identify the pdf header if it is not in the first 4 bytes
    extended_pdf_regex = re.compile(b"^.*%PDF")    
    
    # Get the first 1024 bytes
    full_header = stream.read(1024)
    stream.seek(0) # Have to seek back to the beginning each time so file-saving is not 1024 bytes short

    if re.match(extended_pdf_regex, full_header): # Already checked the first 4 chars
        return (True, "extended")
    
    # Return (False, "not")
    return (False, "not")

def remove_except(dir, exception):
    
    """Remove everything from a dir except a given list of exceptions"""
    
    for item in listdir(dir):
        if not item in exception:
            remove(path.join(dir, item))
    return


# -- MAIN ROUTES

@login_required
@bp.route('/upload', methods = ("GET", "POST"))
def upload():
    if request.method == "POST":
        
        # Get all the uploaded files
        uploaded_files = request.files.getlist("file")

        # Check if a file was actually uploaded
        if all(uploaded_file.filename == "" for uploaded_file in uploaded_files):
            flash("No selected file")
            return redirect(request.url)

        # Check if there are already pdfs stored in session
        if not session.get('pdf_names') or type(session.get('pdf_names')) != list:
            session['pdf_names'] = []

        # Generate the path for the user's output folder (uploads/<user_id>/ folder)
        user_upload_folder = path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/",)

        if path.isdir(user_upload_folder):
            # Purge the directory except for the pdfs that were stored in the session
            remove_except(user_upload_folder, session.get('pdf_names'))
        else:
            # Create directory if it does not already exist
            mkdir(user_upload_folder)

        for uploaded_file in uploaded_files:
            pdf_name = uploaded_file.filename

            # Check if the file is valid (using allowed_file and validate_pdf)
            if allowed_file(pdf_name) and validate_pdf(uploaded_file.stream)[0]:
                # Secure file name
                pdf_name = secure_filename(pdf_name)

                # Save file
                uploaded_file.save(path.join(user_upload_folder, pdf_name))

                # Add to a running list of all the pdf file names
                session.get('pdf_names').append(pdf_name)

            # If file is not valid
            else: 
                flash("Upload valid file") # NOTE: may want better error message
                return redirect(request.url)
            
        # if the file save/download is successful redirect to next page
        if session.get('pdf_names'):
            return redirect(url_for('pdfhandler.edit'))
        else:
            flash("Files were not saved. Try again.")
            return redirect(request.url)
    return render_template('pdfhandler/upload.html')

@login_required
@bp.route('/edit', methods = ("GET", "POST"))
def edit():
    if request.method == "POST":
        selected_pages = request.get_json()
        session['selected_pages'] = selected_pages
        return redirect(url_for('pdfhandler.download'))

    # -- CONFIGURABLE
    image_width = 500
    
    if not session.get('pdf_names'):
        flash("Upload a file before you try to edit")
        return redirect(request.url) # NOTE: it may be better to redirect to url_for('pdfhandler.upload')
    
    # -- SAVE ALL THE FILES
    pdf_to_images_map = {}

    for pdf_name in session['pdf_names']:
        # Get url for output folder
        output_folder = path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/")

        # Create images and get paths. XXX: 
        image_paths = convert_from_path(path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", pdf_name), fmt = "jpeg", output_folder = output_folder, size = (image_width, None), paths_only = True)
        
        # Cut off everything except the file stem
        image_names = [path.split(image_path)[1] for image_path in image_paths] # XXX: this may not be robust

        # Put all the images associated with a pdf file in dictionary with form {pdf_file_name : list_of_images}
        pdf_to_images_map[pdf_name] = image_names

    # Store pdf_to_images_map dict in the session
    session['pdf_to_images_map'] = pdf_to_images_map

    return render_template('pdfhandler/edit.html', all_image_names = pdf_to_images_map.values(), user_id = str(session.get('user_id')))

@login_required
@bp.route('/download', methods = ("GET", "POST"))
def download():
    # -- GET PDF NAMES + PG #S
    pdfs_information = {}
    
    regex = re.compile('-(\d).jpg$') # Get the image file stem and the page number. NOTE: This is jpg (jpeg) specific
    for page in session.get('selected_pages'):

        image_file_stem, page_number = re.split(regex, page)[:2]
        
        # Search for the image_file_stem
        pdf_to_images_map = session.get('pdf_to_images_map')
        for pdf_file in pdf_to_images_map:
            if image_file_stem in pdf_to_images_map[pdf_file][0]:
                pdfs_information[page] = [pdf_file, page_number] # Generates an (ordered) dictionary of form {"file name of image corresponsing to page": [pdf_name, page_number]}
                break

    # -- GENERATE PDF
    out_file_name = "out_" + str(session.get('user_id')) + ".pdf"
    out_location = path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", out_file_name)

    pdf_writer = PyPDF2.PdfFileWriter()
    for [file, page] in pdfs_information.values():
        file_location = path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", file) # For some reason, the path works better than passing in a stream
        pdf_reader = PyPDF2.PdfFileReader(file_location) 
        
        page = int(page) - 1

        pdf_writer.addPage(pdf_reader.getPage(page))
        
    with open(out_location, 'wb') as fh:
        pdf_writer.write(fh)

    return render_template('pdfhandler/download.html', file_name = out_file_name, user_id = str(session.get('user_id')))