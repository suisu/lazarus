from flask import Blueprint, render_template, abort, json
from jinja2 import TemplateNotFound
from app.models import Organization, Repository, Branch, Vuln, ScannerSettings
from app import db
from flask_login import login_required

dashboard_page = Blueprint('dashboard_page', __name__,
    template_folder='templates',
    static_folder='static')


@dashboard_page.route('/dashboard')
@login_required
def dashboard():
    try:
        
        subquery = db.session.query(Vuln.branch_id.label('br_id'), db.func.count(Vuln.id)\
            .label('vuln_cnt')).group_by(Vuln.branch_id).subquery()
        query = db.session.query(Organization.id, Organization.name, Repository.name, Branch.name, subquery.c.vuln_cnt)\
            .join(subquery, (Branch.id == subquery.c.br_id) & (subquery.c.vuln_cnt > 0)).join(Repository).join(Organization).all()
        
        orgs = set(map(lambda x: x[1], query))
        
        # circle chart
        organization_filter = list(map(lambda y: {"name":y, "children":list(map(lambda x: {"name": x[2], "value": x[4]}, \
            list(filter(lambda x: x[1]==y, query))))}, orgs))

        #filled_organization_filter = list(filter(lambda x: len(x["children"])>0, organization_filter))
        data = {"name": "Organization", "children": organization_filter}
        
        # pie chart
        transformed_repository = list(map(lambda x: {"label": x[2], "value": x[4]}, query))

        # reasaonpie chart
        reasons = db.session.query(Vuln.reason, db.func.count(Vuln.reason)).\
            group_by(Vuln.reason).all()
        reas = list(map(lambda x: {"label": x[0], "value": x[1]}, reasons))

        return render_template('dashboard.html', \
                data=json.dumps(data), \
                chart_data=json.dumps(transformed_repository), \
                reasons_chart_data=json.dumps(reas)) 
    except TemplateNotFound:
        abort(404)
