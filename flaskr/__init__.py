from flaskr.auth import login_required
from logging import DEBUG
import os

from flask import (Flask, render_template)
from flask.helpers import send_from_directory

def create_app(test_config = None):

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY = "dev",
        DATABASE = os.path.join(app.instance_path, 'flaskr.sqlite'),
        UPLOAD_FOLDER = 'flaskr/uploads/', # XXX: why do upload_folder & upload_path have to be different
        UPLOAD_PATH = 'uploads/',
        MAX_CONTENT_LENGTH = 1024 * 1024 * 5, # Max size in bytes; equiv to 5 mb,
        UPLOAD_EXTENSIONS = ['pdf'],
        ENV = "development",
        DEBUG = True
    )

    # -- BASIC SET-UP
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # -- INDEX VIEW
    @app.route('/index')
    def index():
        return render_template('index.html')

    # -- FILE UPLOADS VIEW
    @login_required
    @app.route('/uploads/<user_id>/<file_name>')
    def upload(user_id, file_name):
        print(os.path.join(app.config['UPLOAD_FOLDER'], user_id + "/", file_name))
        print(file_name)
        return send_from_directory(os.path.join(app.config['UPLOAD_PATH'], user_id + "/"), file_name)

    # -- INCLUDE DB + BLUEPRINTS
    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import pdfhandler
    app.register_blueprint(pdfhandler.bp)

    return app