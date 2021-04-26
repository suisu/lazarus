from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from string import Template
from config import Settings
from truffleHog import truffleHog
import json
from .models import Branch, Vuln, Scan
from .dbhelper import create_or_update as cru
from app.models import ScannerSettings


json_file_template = Template('$organization $repository $branch.json')

engine = create_engine(Settings.config.get('db').get('database_uri')) #('postgres+psycopg2://localhost:5432/lazarus')
SessionX = sessionmaker(bind=engine, autocommit=False)

##
stopper = False
import threading
threadLock = threading.Lock()
branch_counter = 0

def truffle_scan(session, branch, scannerSettings):
    repository = branch.repository
    organization = repository.organization

    git_repo_template = Template('https://$token@$github_domain/$organization/$repository.git')
    git_url = git_repo_template.substitute(
        token=scannerSettings.token,
        github_domain = scannerSettings.scan_github_domain,
        organization=organization.name,
        repository=repository.name
    )
    entropy = scannerSettings.scan_entropy
    max_depth = scannerSettings.scan_max_depth

    output = truffleHog.find_strings(git_url=git_url,
                    branch=branch.name, 
                    do_regex=True, 
                    do_entropy=entropy,
                    printJson=True,
                    max_depth=max_depth)
    issues = []
    for issue in output.get('foundIssues'):
        with open(issue) as json_file:
            data = json.load(json_file)
            issues.append(data)

    truffleHog.clean_up(output)

    (scan, _) = cru(session, 
                Scan, 
                new_values={"count":len(issues), "branch": branch},
                filter_by={"branch": branch}
    )
    for issue in issues:
        try:
            t = datetime.strptime(issue.get('date'),'%Y-%m-%d %H:%M:%S')
            #issuesFound = set(issue.get('stringsFound'))
            (vuln, _) = cru(session,
                        Vuln,
                        filter_by={"reason":issue.get('reason'),
                            "commithash":issue.get('commitHash'),
                            "commit":issue.get('commit'),
                            "date":t,
                            "path":issue.get('path'), 
                            "branch":branch,
                            "scan":scan},
                        new_values={"reason":issue.get('reason'),
                            "stringsfound":issue.get('stringsFound'),
                            "commithash":issue.get('commitHash'),
                            "commit":issue.get('commit'),
                            "printdiff":issue.get('printDiff'),
                            "date":t,
                            "path":issue.get('path'), 
                            "branch":branch,
                            "scan":scan}
                        )
        except Exception as e:
            print("Error occurred: {}".format(str(e)))
            continue
    return len(issues)

def run_one_branch_scan(session, branch, scanSettings=None):
    if scanSettings is None:
        scanSettings = ScannerSettings.query.first()
    result = truffle_scan(session, branch, scanSettings)
    
    print(f'Branch scanned: {branch.name}, vulnerabilities: {result}')
    resStr = f'Scanned: Org({branch.repository.organization.name}), \
        Repo:({branch.repository.name}), Branch:({branch.name}), \
            <strong>Vulns: ({result})</strong>'
    result = dict(message = resStr, status = result)
    return result

def run_scanner(branch_id, scanSettings):
    if stopper:
        raise ValueError("Scanning cancelled")
    
    session = SessionX()
    result = None
    status = 0
    global branch_counter
    try:
        branch = session.query(Branch).get(branch_id)
        vuln = session.query(Scan).filter_by(branch_id=branch.id).one_or_none()
        if vuln:
            time_created = vuln.time_created.replace(tzinfo=None)
            delta_days = (lambda x: x.days)(datetime.utcnow() - time_created)
            last_days = scanSettings.scan_newer_days
            if delta_days > last_days:
                # not scanned
                print(f'Branch not scanned: {branch.name}, reason: scan performed {delta_days} ago')
                resStr = f'Not Scanned: Org({branch.repository.organization.name}), \
                    Repo:({branch.repository.name}), Branch:({branch.name}), \
                        <strong>Reason: (scan performed {delta_days})</strong>'
                status = 0
            else:
                # everything else scan again or newly
                result = truffle_scan(session, branch, scanSettings)
        else:
            result = truffle_scan(session, branch, scanSettings)

        print(f'Branch scanned: {branch.name}, vulnerabilities: {result}')
        resStr = f'Scanned: Org({branch.repository.organization.name}), \
            Repo:({branch.repository.name}), Branch:({branch.name}), \
                <strong>Vulns: ({result})</strong>'
        status = result
                    
    except Exception as e:
        resStr = f'Error occured: {str(e)}'
    finally:
        session.close()
        with threadLock:
            branch_counter += 1
        result = dict(message=resStr, status=status, counter=branch_counter)
        return result
