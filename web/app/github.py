from pygithub3 import Github
from config import Settings
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .models import Branch, Organization, Language, Repository, \
    Github as GitTimeStamp, ScannerSettings

engine = create_engine(Settings.config.get('db').get('database_uri'))
SessionX = sessionmaker(bind=engine, autocommit=False)

stopper = False

def get_or_create(session, model, commit=True, new_values={}, filter_by={}):
    if bool(filter_by):
        instance = session.query(model).filter_by(**filter_by).one_or_none()
    else:
        instance = session.query(model).filter_by(**new_values).one_or_none()
    if instance:
        return instance, False
    else:
        new_values |= {}
        instance = model(**new_values)
        try:
            session.add(instance)
            if commit:
                session.commit()
        except Exception: 
            session.rollback()
            instance = session.query(model).filter_by(**new_values).one()
            return instance, False
        else:
            return instance, True

class GitApi(object):
    scannerSettings = ScannerSettings.query.first()
    gh = Github(login_or_token = scannerSettings.token, 
                base_url=scannerSettings.github_api_url)
    updated_for_last_days = scannerSettings.github_last_updated_days
    
    @classmethod
    def gather_orgs(cls):
        orgs = cls.gh.get_organizations()
        return orgs

    @classmethod
    def gather_repos(cls, org):
        repos = org.get_repos()
        return repos

    @classmethod
    def gather_branches(cls, repo):
        branches = repo.get_branches()
        return branches

    @classmethod
    def gather_languages(cls, repo):
        lines = repo.get_languages()
        return lines


def run_scanner_org(org):
    if stopper:
        raise ValueError('Scanning cancelled')
    
    now = datetime.utcnow()
    session = SessionX()
    result = {}
    global org_counter

    try:
        (org_db, created) = get_or_create(session, Organization,
            new_values={'name':org.login, 'url':org.html_url})
        result.update({'message': f"Scanned: {org_db.name}"})

        repos = GitApi.gather_repos(org)
        for repo in repos:
            last_updated = repo._updated_at.value or now
            delta_days = (lambda x: x.days)(now - last_updated)
            if delta_days > GitApi.updated_for_last_days:
                continue
            #TODO UPDATE due to date
            (repo_db, created) = get_or_create(session, Repository,
                new_values={'name':repo.name, 'url':repo.html_url, 'private':repo.private,
                    'description':repo.description, 'organization':org_db, 
                    'last_updated':last_updated},
                filter_by={'name': repo.name, 'organization':org_db})
            print(repo.name)

            #TODO update due to lines
            languages = GitApi.gather_languages(repo)
            for language, lines in languages.items():
                (language_db, created) = get_or_create(session, Language,
                    new_values={'name':language, 'lines':lines, 'repository':repo_db},
                    filter_by={'name': language, 'repository': repo_db})

            branches = GitApi.gather_branches(repo)
            for branch in branches:
                is_default = repo.default_branch == branch.name
                (branch_db, created) = get_or_create(session, Branch,
                        new_values={'name':branch.name, 'repository':repo_db, 
                        'default_branch':is_default})
    except Exception:
        pass
    finally:
        session.close()
        return result

def save_github_timestamp(timestamp):
    session = SessionX()
    try:
        (timestamp_db, created) = get_or_create(session, GitTimeStamp,
            new_values={'time_created':timestamp},
            filter_by={'time_created': timestamp})
        return dict(message="Github Scan Timestamp created", alert='success')
    except Exception:
        raise ValueError("Couldn't save timestamp")
    finally:
        session.close()
