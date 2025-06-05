from flask import Blueprint


def create_v1_blueprint():
    v1_blueprint = Blueprint('v1', __name__, url_prefix='/v1.0')
    return v1_blueprint
