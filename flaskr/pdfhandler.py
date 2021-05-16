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

import os

import re

from pdf2image import convert_from_path, convert_from_bytes

import PyPDF2

bp = Blueprint('pdfhandler', __name__, url_prefix='/pdfhandler')

# -- HELPER FUNCTIONS

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config["UPLOAD_EXTENSIONS"]

def validate_pdf(stream):
    extended_pdf_regex = re.compile(b"^.*%PDF")
    first_four_bytes = stream.read(4)
    stream.seek(0)
    full_header = stream.read(1024)
    stream.seek(0) # Have to seek back to the beginning each time so file-saving is not 1024 bytes short

    if b"%PDF" == first_four_bytes:
        return (True, "regular")
    elif re.match(extended_pdf_regex, full_header): # Already checked the first 4 chars
        return (True, "extended")
    else:
        return (False, "not")

# -- MAIN ROUTES

@bp.route('/upload', methods = ("GET", "POST"))
@login_required
def upload():
    if request.method == "POST":

        # Get all the uplaoded files
        uploaded_files = request.files.getlist("file")

        # Check if a file was actually uploaded
        if all(uploaded_file.filename == "" for uploaded_file in uploaded_files):
            flash("No selected file")
            return redirect(request.url)
        
        file_names = []
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.filename

            if allowed_file(file_name) and validate_pdf(uploaded_file.stream)[0] and uploaded_file: # Validate
                file_name = secure_filename(file_name)

                # XXX: This file needs to be deleted

                # Save file
                try:
                    uploaded_file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", file_name))
                except FileNotFoundError:
                    # Create directory if doesn't exist
                    os.mkdir(os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/"))
                    uploaded_file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", file_name))

                file_names.append(file_name)

            else: # If file is not valid
                flash(f"Upload valid file") # NOTE: may want better error message
                return redirect(request.url)
            
        # if the file save/download is successful red direct to next page
        if file_names: # Check if there is anything in file_names (ie, if any files were successfully saved)
            session['file_names'] = file_names
            return redirect(url_for('pdfhandler.edit')) # XXX: is this correct? XXX: this may be insecure (url may provide access to other ppls files)
            # XXX: need to make this temporary: use tempfile?
    
    return render_template('pdfhandler/upload.html')

@login_required
@bp.route('/edit', methods = ("GET", "POST"))
def edit():
    if request.method == "POST":
        selected_pages = request.get_json()
        session['selected_pages'] = selected_pages
        print('hello')
        return redirect(url_for('pdfhandler.download'))
    
    # NOTE: everything above this point needs to return something so the area below doesn't fire
    # -- CONFIGURABLE
    image_width = 500
    
    if not session.get('file_names'):
        flash("Upload a file before you try to edit")
        return redirect(request.url) # NOTE: it may be better to redirect to url_for('pdfhandler.upload')
    
    # -- SAVE ALL THE FILES

    # XXX: add code to ignore and/or delete previously created data

    pdf_to_images_map = {}

    for file_name in session['file_names']:
        # Get url for output folder
        output_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/")

        # Create images and get paths. XXX: 
        image_paths = convert_from_path(os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", file_name), fmt = "jpeg", output_folder = output_folder, size = (image_width, None), paths_only = True) # Set size to something relatively small (e.g., 200xNone?, where 200)
        
        # Cut off everything except the file stem
        image_names = [os.path.split(image_path)[1] for image_path in image_paths] # XXX: this may not be robust

        # Put all the images associated with a pdf file in dictionary with form {pdf_file_name : list_of_images}
        pdf_to_images_map[file_name] = image_names

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
    out_location = os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", out_file_name)

    pdf_writer = PyPDF2.PdfFileWriter()
    for [file, page] in pdfs_information.values():
        file_location = os.path.join(current_app.config["UPLOAD_FOLDER"], str(session.get('user_id')) + "/", file) # For some reason, the path works better than passing in a stream
        pdf_reader = PyPDF2.PdfFileReader(file_location) 
        
        # Grab some infomration about the file:
        # info = pdf_reader.getDocumentInfo()
        # num_pages = pdf_reader.getNumPages()
        page = int(page) - 1

        pdf_writer.addPage(pdf_reader.getPage(page))
        
    with open(out_location, 'wb') as fh:
        pdf_writer.write(fh)

    return render_template('pdfhandler/download.html', file_name = out_file_name, user_id = str(session.get('user_id')))