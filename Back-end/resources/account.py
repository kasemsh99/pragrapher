import os
from flask_restful import Resource
from flask import request, redirect, make_response, url_for, jsonify, render_template
import jwt
from sqlalchemy.orm.base import NOT_EXTENSION
from config import jwt_secret_key
from tools.db_tool import engine
from tools.image_tool import get_extension
from tools.token_tool import authorize

from db_models.users import  change_user_image, edit_bio, get_one_user, add_user, change_pass, edit_fname
from tools.string_tools import gettext



class myprofile(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def get(self, current_user):
        """:return current user info"""
        req_data = request.json
        res = make_response(jsonify(current_user.json))
        return res

    @authorize
    def post(self, current_user):
        """insert or change current user fname"""
        req_data = request.json
        edit_fname(current_user, req_data['fname'], self.engine)
        return redirect(url_for("myprofile"))

class bio(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def post(self, current_user):
        """insert or change current user bio"""
        req_data = request.json
        edit_bio(current_user, req_data['bio'], self.engine)
        return redirect(url_for("myprofile"))

class profile_picture(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def post(self, current_user):
        """insert or change current user profile picture"""
        files = request.files
        file = files.get('file')
        if 'file' not in request.files:
            return jsonify(message=gettext("upload_no_file")), 400
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            return jsonify(message=gettext("upload_no_filename")), 400
        if file:
            try:
                os.makedirs(os.getcwd() +gettext('UPLOAD_FOLDER') + '/pp/', exist_ok=True)
            except:
                pass
            url = gettext('UPLOAD_FOLDER') + 'pp/' + str(current_user.id) + get_extension(file.filename)
            try:
                os.remove(url)
            except:
                pass
            file.save(os.getcwd() +url)
            change_user_image(current_user, url, self.engine)
            return jsonify(message=gettext("upload_success"))


class password(Resource):
    def __init__(self, **kwargs):
        self.engine = kwargs['engine']
    @authorize
    def post(self, current_user):
        """change current_user password"""
        req_data = request.json
        res = change_pass(current_user, req_data['old_password'], req_data['new_password'], self.engine)
        if res:
            return redirect(url_for("logout"))
        else:
            return jsonify(message=gettext("wrong_pass"))
