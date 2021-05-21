import os

from git import Repo
from git.exc import InvalidGitRepositoryError

from github import Github
from github.GithubException import UnknownObjectException

from .common import \
    TAG_EXPERIMENTAL, \
    die, \
    get_experimental, \
    load_dabl_meta, \
    package_dit_filename, \
    with_catalog

from .log import LOG, is_verbose

REQUIRED_SCOPES=set([
    'repo',
    'write:packages',
    'delete:packages'
])

def connect_to_github() -> 'Github':

    github_token = os.environ.get('GITHUB_TOKEN')

    if github_token is None:
        die('Missing GitHub token in environment variable GITHUB_TOKEN')

    github = Github(github_token)

    user_scopes = set()
    try:
        user = github.get_user()

        username = user.name

        user_scopes = set() if github.oauth_scopes is None else set(github.oauth_scopes)

        LOG.info('Connected as user: %r (scopes: %r)', username, user_scopes)

    except:
        if is_verbose():
            LOG.exception('Error authenticating to GitHub.')

        die('Invalid credentials in GITHUB_TOKEN')


    if not REQUIRED_SCOPES.issubset(user_scopes):
        die(f'Github token missing required permissions (oauth scopes):'
            f'{REQUIRED_SCOPES.difference(user_scopes)}')


    return github

def subcommand_main(force: bool, dry_run: bool):

    dabl_meta = load_dabl_meta()

    dit_filename = package_dit_filename(dabl_meta)

    if not os.path.exists(dit_filename):
        die(f'Release artifact not found (run \'ddit build\' to build): {dit_filename}')

    github = connect_to_github()

    try:
        repo = Repo('.')
    except InvalidGitRepositoryError:
        die('Invalid git repository.')

    try:
        origin = repo.remote()
        LOG.info('Remote URL: %r', origin.url)

        repo_name = origin.url.split('.git')[0].split(':')[1]

        LOG.info('Repo name: %r', repo_name)

    except ValueError:
        die(f'No remote with name \'origin\'.')

    try:
        github_repo = github.get_repo(repo_name)
    except UnknownObjectException:
        die(f'Remote not found on GitHub: {origin.url}')

    if repo.is_dirty():
        die('Uncommitted changes in repository')

    catalog = with_catalog(dabl_meta)
    tag_name = f'{catalog.name}-v{catalog.version}'

    LOG.info(f'Releasing version {catalog.version} as {tag_name}.')

    prerelease = get_experimental(catalog)

    if prerelease:
        LOG.info(f'Found the "{TAG_EXPERIMENTAL}" tag. Creating a prerelease.')

    if dry_run:
        LOG.info('Dry run. Tags and releases not created.')
        return

    try:
        repo.create_tag(tag_name, force=force)
    except:
        die(f'Error creating tag: {tag_name}')

    try:
        origin.push(tag_name, force=force)
    except:
        die(f'Error pushing to remote.')

    github_release = None
    for release in github_repo.get_releases():
        if release.tag_name == tag_name:
            github_release = release

    if github_release:
        if force:
            LOG.warn(f'Deleting existing release for tag: {tag_name}')
            github_release.delete_release()
        else:
            die(f'Existing release found for tag: {tag_name}')

    LOG.info('Creating new release for tag: %r', tag_name)
    github_release = github_repo.create_git_release(
        tag_name, tag_name, f'DIT file release (ddit) - {tag_name}', prerelease=prerelease)

    LOG.info('Uploading release asset: %r', dit_filename)
    github_release.upload_asset(dit_filename, dit_filename)


def setup(sp):
    sp.add_argument('--dry-run',
                    help='Do not create tags or releases.',
                    dest='dry_run', action='store_true', default=False)

    sp.add_argument('--force',
                    help='Forcibly overwrite target release and tag if they exist',
                    dest='force', action='store_true', default=False)

    return subcommand_main
