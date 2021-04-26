import collections
from flask import Blueprint, render_template, abort, flash, redirect, request, jsonify
from jinja2 import TemplateNotFound
from flask_expects_json import expects_json
from app.models import Vuln, Scan, Branch
from app import db
from app.validator import details_false_positive, details_printPDF
from config import Settings
from flask_login import login_required

details_page = Blueprint('details_page', __name__,
    template_folder='templates',
    static_folder='static')

@details_page.route('/details/<int:id>', defaults={'page_num':1})
@details_page.route('/details/<int:id>/<int:page_num>')
@login_required
def details(id, page_num):
    try:
        scannerSettings = ScannerSettings.query.first()
        githubdomain = f"https://{scannerSettings.scan_github_domain}
        scan = Scan.query.get(id)
        
        details = Vuln.query.filter_by(scan_id=id).\
            order_by(db.asc(Vuln.id)).\
            paginate(page_num, 5, False)

        if not details:
            flash("No scan result found.", "error")
            return redirect(request.referrer)

        languages = get_languages(scan)
        reasons = get_reasons(scan)
        
        return render_template('details.html', details=details, languages=languages, scan=scan, reasons=reasons, githudomain=githubdomain)
    except TemplateNotFound:
        abort(404)

def get_languages(scan):
    languages = scan.branch.repository.languages.all()
    langs = list(map(lambda x: {"label": x.name, "value": x.lines }, languages))
    return langs

def get_reasons(scan):
    reasons = db.session.query(Vuln.reason, db.func.count(Vuln.reason)).\
        filter_by(scan_id=scan.id).group_by(Vuln.reason).all()
    reas = list(map(lambda x: {"label": x[0], "value": x[1]}, reasons))
    return reas

@details_page.route('/false-positive', methods=['POST'])
@expects_json(details_false_positive)
@login_required
def false_positive():
    try:
        vuln_id = request.json.get('vuln_id')
        checked = request.json.get('checked')
        vuln = Vuln.query.get(vuln_id)
        if not vuln:
            raise ValueError(f"Vulnerability id: {vuln_id} doesn't exist.")
        vuln.false_positive = checked
        db.session.commit()
        # assing vuln_positive to all branches in repository
        repo = vuln.branch.repository
        branches = db.session.query(Branch.id).filter_by(repository_id=repo.id).all()
        br = [item for item, in branches]
        vulns = Vuln.query.filter(Vuln.branch_id.in_(br)).all()
        for item in vulns:
            if collections.Counter(item.stringsfound) == collections.Counter(vuln.stringsfound):
                item.false_positive = checked
        db.session.commit()

        result = dict(message=f"Vulnerability id: {vuln_id} updated.", alert='success')
        return jsonify(result), 201

    except Exception as e:
        res = jsonify(dict(message=str(e), alert='danger'))
        return res, 409

@details_page.route('/print-pdf', methods=['POST'])
@expects_json(details_printPDF)
@login_required
def printPDF():
    try:
        scan_id = request.json.get('scan_id')
        if not scan_id:
            raise ValueError("Scan ID is not specified")

        details = Vuln.query.filter_by(scan_id=scan_id).\
            order_by(db.asc(Vuln.false_positive)).all()

        githuburl = Settings.config.get('vulnerability_scan').get('git_url')
        result = list(map(lambda x: {
            'stringsfound': x.stringsfound,
            'printdiff': x.printdiff,
            'reason': x.reason,
            'commit': x.commit,
            'commithash': x.commithash,
            'path': x.path,
            'false_positive': x.false_positive,
            'date': x.date.strftime('%d.%m.%Y %H:%M'),
            'pathurl': f'https://{githuburl}/{x.branch.repository.organization.name}/{x.branch.repository.name}/blob/{x.branch.name}/{x.path}'
        }, details))

        return jsonify(result=result)

    except Exception as e:
        res = jsonify(dict(message=str(e), alert='danger'))
        return res, 409