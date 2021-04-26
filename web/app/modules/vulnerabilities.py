from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound
from app import db
from app.models import Organization, Repository, Branch, Scan
from flask_login import login_required

vulnerabilities_page = Blueprint('vulnerabilities_page', __name__,
    template_folder='templates',
    static_folder='static')

@vulnerabilities_page.route('/vulnerabilities', defaults={'page_num':1})
@vulnerabilities_page.route('/vulnerabilities/<int:page_num>')
@login_required
def vulnerabilities(page_num):
    try:
        vulnerabilities = db.session.query(Scan.id, Scan.count, Scan.time_created, \
            Branch.name, Repository.name, Repository.description, Organization.name, Organization.url, Repository.url).\
                join(Branch, Scan.branch_id == Branch.id).\
                join(Repository, Repository.id == Branch.repository_id).\
                join(Organization, Organization.id == Repository.organization_id).\
                filter(Scan.count>0).\
            order_by(db.desc(Scan.count)).paginate(page_num, 7, False)

        return render_template('vulnerabilities.html', vulnerabilities=vulnerabilities)
    except TemplateNotFound:
        abort(404)
