from flask import Blueprint, render_template, abort, request, jsonify
from flask_expects_json import expects_json
from flask_login import current_user
from app.models import Organization, Repository, Branch, ScannerSettings
from app import db
from app.scanner import run_one_branch_scan
from app.validator import scan_branch_schema
from sqlalchemy.orm.session import Session
from flask_login import login_required

repository_page = Blueprint('repository_page', __name__,
    template_folder='templates',
    static_folder='static')

@repository_page.route('/repository', methods=['GET','POST'], defaults={"page": 1})
@repository_page.route('/repository/<int:page>', methods=['GET','POST'])
@login_required
def repository(page):
    pages = 10
    repository = db.session.query(Branch.id, Branch.name, Repository.id, \
        Repository.name, Organization.id, Organization.name, Repository.url).\
            join(Repository, Repository.id == Branch.repository_id).\
            join(Organization, Organization.id == Repository.organization_id).\
        order_by(db.asc(Organization.name)).paginate(page, pages, False)

    return render_template('repository.html', repository_view=repository)

@repository_page.route('/repository_filter/', methods=['GET'], defaults={'page_num':1})
@repository_page.route('/repository_filter/<int:page_num>', methods=['GET'])
@login_required
def repository_filter(page_num):
    pages = 10
    filter_criteria = request.args.get('query')
    if filter_criteria != "":
        repo_filter = f"{filter_criteria}%"
        search_result = db.session.query(Branch.id, Branch.name, Repository.id, \
        Repository.name, Organization.id, Organization.name, Repository.url).\
            join(Repository, Repository.id == Branch.repository_id).\
            join(Organization, Organization.id == Repository.organization_id).\
            filter(Repository.name.like(repo_filter)).\
        order_by(db.asc(Organization.name))
    else:
        search_result =  db.session.query(Branch.id, Branch.name, Repository.id, \
            Repository.name, Organization.id, Organization.name, Repository.url).\
                join(Repository, Repository.id == Branch.repository_id).\
                join(Organization, Organization.id == Repository.organization_id).\
            order_by(db.asc(Organization.name))

    if search_result != None:
        paginated = search_result.paginate(page_num, pages, False)
        repository_list = []
        for i in paginated.iter_pages(left_edge=3, right_edge=3, left_current=3, right_current=3):
            repository_list.append(i)
        return jsonify({'json_list': [i for i in paginated.items], 'pages_lst': repository_list})                

@repository_page.route('/scan_branch', methods=['POST'])
@expects_json(scan_branch_schema)
@login_required
def scan_branch():
    if not (current_user.is_admin() or current_user.is_operator()):
        abort(403)
    try:
        scannerSettings = ScannerSettings.query.first()
        branch_id = request.json.get('branch_id')
        branch = Branch.query.get(branch_id)
        if not branch:
            raise ValueError(f"Branch id: {branch} doesn't exist.") 
        session = Session.object_session(branch)
        result = run_one_branch_scan(session, branch, scannerSettings)
        print(result)
        
        alert='success'
        if 'status' in result:
            if result.get('status') > 0:
                alert='warning'
            
        result.update(alert=alert)
        return jsonify(result), 201
        
    except Exception as e:
        res = jsonify(dict(message=str(e), alert='danger'))
        return res, 409
