from typing import Tuple, List, Dict
import json
import argparse
from datetime import datetime, timedelta
import urllib3
import requests
from tabulate import tabulate


def process_arguments():
    """
    Function for getting all the mandatory command line arguments
    :return:
    """
    parser = argparse.ArgumentParser(
        description="Script that outputs inactive branches based on number of inactive days for the given repository url"
    )
    parser.add_argument("auth_username", type=str, help="Gitea username credentials")
    parser.add_argument("auth_password", type=str, help="Gitea password credentials")
    parser.add_argument("gitea_url", type=str, help="URL of the gitea server")
    parser.add_argument("owner", type=str, help="Owner of the repository")
    parser.add_argument("repository", type=str, help="Name of the repository")
    parser.add_argument("days", type=int, help="Number of days")

    # TODO: add token

    args = parser.parse_args()
    return args


class Gitea:
    """
    Class for working with the Gitea API.
    Features:
    - get all repository branches
    - store all the repository branhes in the Repository model
    """

    def __init__(self, gitea: str, auth: Tuple[str, str], owner: str, repository: str, verify: bool = False):
        self.gitea = gitea
        self._owner = owner
        self._repository = repository
        self.requests = requests.Session()
        self.requests.auth = auth
        self._headers = {"Content-type": "application/json"}

        # Manage SSL certification verification
        self.requests.verify = verify
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get_url(self, endpoint: str):
        url = f"{self.gitea}/api/v1/repos/{endpoint}"
        return url

    def get_branches(self) -> Dict:
        """
        Function that gets all the branches from the repository and returns a Dict of all available branches
        """
        endpoint = f"{self._owner}/{self._repository}/branches"
        request = self.requests.get(self._get_url(endpoint=endpoint), headers=self._headers)

        if request.status_code not in [200, 2001]:
            message = f"Received status code: {request.status_code} ({request.url})"
            raise Exception(message)

        return json.loads(request.text)

    def parse_repository_results(self, results: List[Dict]):
        branches: List[Branch] = []
        for branch_result in results:
            branch: Branch = self.parse_branch_result(branch=branch_result)
            branches.append(branch)

        return branches

    def parse_branch_result(self, branch: Dict):
        name = branch.get("name")
        last_commit: Commit = self.parse_commit_result(branch.get("commit"))

        return Branch(name=name, last_commit=last_commit)

    def parse_commit_result(self, commit: Dict):
        message = commit.get("message")
        url = commit.get("url")
        author = commit.get("author").get("name")
        timestamp = datetime.strptime(commit.get("timestamp")[:-6], "%Y-%m-%dT%H:%M:%S")
        return Commit(url=url, author=author, message=message, timestamp=timestamp)


class Commit:
    """
    Commit model
    """

    def __init__(self, url: str, author: str, message: str, timestamp: datetime):
        self._url = url
        self._author = author

        # Get only the first 90 char of the message
        self._message = message[:90]

        self._timestamp = timestamp

    def get_timestamp(self) -> datetime:
        return self._timestamp

    def get_dict(self):
        return {
            "author": self._author,
            "message": self._message,
            "timestamp": self._timestamp.strftime("%d-%m-%Y %H:%m"),
            "url": self._url,
        }


class Branch:
    """
    Branch model
    """

    def __init__(self, name: str, last_commit: Commit):
        self._name = name
        self._last_commit = last_commit

    def get_last_commit(self) -> Commit:
        return self._last_commit

    def get_name(self) -> str:
        return self._name

    def get_dict(self):
        today = datetime.today()
        time_since_last_commit = today - self._last_commit.get_timestamp()
        last_commit_dict = self._last_commit.get_dict()
        return {"name": self._name, "days_since_last_commit": time_since_last_commit.days, **last_commit_dict}

    def is_active(self, time_inactive: timedelta) -> bool:
        """
        Function that returns bool if branch has been last time_inactive
        :param time_inactive:
        :return: bool
        """
        today = datetime.today()
        return today - self._last_commit.get_timestamp() < time_inactive


class Repository:
    """
    Repository model
    """

    def __init__(self, name: str, branches: List[Branch]):
        self._name = name
        self._branches = branches

    def get_inactive_branches(self, time_inactive: timedelta) -> List[Branch]:
        return [branch for branch in self._branches if not branch.is_active(time_inactive)]

    def display_tabulate(self, sort_by_datetime: bool = True):
        if sort_by_datetime:
            sorted_branches = sorted(self._branches, key=lambda branch: branch.get_last_commit().get_timestamp())
        else:
            sorted_branches = self._branches

        data = [[*branch.get_dict().values()] for branch in sorted_branches]
        print(tabulate(data, headers=[*sorted_branches[0].get_dict().keys()]))


def main():
    try:
        args = process_arguments()
        auth_username = args.auth_username
        auth_password = args.auth_password

        gitea_url = args.gitea_url
        owner = args.owner
        repository = args.repository
        inactive_days = args.days

        gitea = Gitea(
            gitea=gitea_url, auth=(auth_username, auth_password), owner=owner, repository=repository, verify=False
        )
        results = gitea.get_branches()
        branches: List[Branch] = gitea.parse_repository_results(results=results)

        repo = Repository(name="FWSW_Platform", branches=branches)
        inactive_repo = Repository(
            name="FWSW_Platform", branches=repo.get_inactive_branches(time_inactive=timedelta(days=inactive_days))
        )
        inactive_repo.display_tabulate(sort_by_datetime=True)

    except Exception as exc:
        print("Exception", exc)


if __name__ == "__main__":
    main()
