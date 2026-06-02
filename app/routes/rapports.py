from flask import Blueprint, render_template
from flask_login import login_required

rapports_bp = Blueprint('rapports', __name__, url_prefix='/rapports')

@rapports_bp.route('/')
@login_required
def index():
    return render_template('rapports/index.html')
