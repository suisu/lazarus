from flask import Blueprint, render_template, abort, flash, redirect, url_for
from app.models import Branch, ScannerSettings
from app import socketio
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import github as gh
from app import scanner as scanner
from requests.exceptions import Timeout
from datetime import datetime
from flask_login import login_required, current_user
from app.modules.admin import admin_page

scanner_page = Blueprint('scanner_page', __name__,
    template_folder='templates',
    static_folder='static')

@scanner_page.route('/scan', methods=['GET'])
@login_required
def scan():
    if not (current_user.is_admin() or current_user.is_operator()):
        abort(403)
    
    scannerSettings = ScannerSettings.query.one_or_none()
    if scannerSettings is None:
        flash("Before Scanning, please enter Scanning Settings.", category="info")
        return redirect(url_for('admin_page.settings'))
    return render_template('scanner.html')

def getscan():
    print("scanning for vulnerabilities")
    try:
        scannerSettings = ScannerSettings.query.first()
        session = scanner.SessionX()
        branches = session.query(Branch.id).filter(Branch.default_branch.is_(True)).all()
        session.close()
        branches_count = len(branches)
        scanner.branch_counter = 0
        pool = ThreadPoolExecutor(scannerSettings.scan_threads)
        futures = []
        alert = 'info'
        for branch in branches:
            futures.append(pool.submit(scanner.run_scanner, branch, scannerSettings))
        for out in as_completed(futures):
            print(scanner.branch_counter)
            result = out.result()
            print(result)
            percentage(result, result.get('counter'), branches_count)
            if 'status' in result:
                if result.get('status') > 0:
                    alert = 'warning'
            result.update({'alert': alert})
            socketio.emit('scan_results', result, broadcast=True)
    except Timeout as e:
        print(e)
        result = {"message": "Connection error: You are not connected to VPN!",
            'alert': 'danger', 'percentage': '100'}
        socketio.emit('scan_results', result)
    except Exception as e:
        print(e)
        result = {"message": f"{e}", 'alert': 'danger', 'percentage': '100'}
        socketio.emit('scan_results', result)

def percentage(hashresult, counter, total):
    percentage = round(counter / total * 100)
    hashresult.update({"percentage": str(percentage)})

def getgithub():
    print("scanning for github")
    orgs_total_count = 0
    try:
        scannerSettings = ScannerSettings.query.first()
        orgs = gh.GitApi.gather_orgs()
        orgs_total_count=len(list(orgs))
        result = {"message": f"{orgs_total_count} will be scanned", "alert": "info" }
        percentage(result, 0, orgs_total_count)
        socketio.emit('github_results', result)
        
        gh.org_counter = 0
        pool = ThreadPoolExecutor(scannerSettings.scan_threads)
        futures_org = []
        for org in orgs:
            futures_org.append(pool.submit(gh.run_scanner_org, org))
        for idx, out in enumerate(as_completed(futures_org), 1):
            result = out.result()
            percentage(result, idx, orgs_total_count)
            result.update({'alert': 'info'})
            socketio.emit('github_results', result)

        result = gh.save_github_timestamp(timestamp=(lambda y: y)((lambda x: x.replace(microsecond=0))(datetime.utcnow())))
        result.update({'percentage': '100'})
        socketio.emit('github_results', result)
    except Timeout as e:
        print(e)
        result = {"message": "Connection error: You are not connected to VPN!",
            'alert': 'danger', 'percentage': '100'}
        socketio.emit('github_results', result)
    except Exception as e:
        print(e)
        result = {"message": f"{e}", 'alert': 'danger', 'percentage': '100'}
        socketio.emit('github_results', result)

@socketio.on('scan')
@login_required
def handleScan(msg):
    if not (current_user.is_admin() or current_user.is_operator()):
        abort(403)

    if (msg=='start'):
        scanner.stopper = False
        socketio.start_background_task(getscan)
    if (msg=='stop'):
        scanner.stopper = True

@socketio.on('github')
@login_required
def handleGithub(msg):
    if not (current_user.is_admin() or current_user.is_operator()):
        abort(403)

    if (msg=='start'):
        gh.stopper = False
        socketio.start_background_task(getgithub)
    if (msg=='stop'):
        gh.stopper = True

@socketio.on('disconnect')
@login_required
def disconnect():
    print('Client disconnected')

