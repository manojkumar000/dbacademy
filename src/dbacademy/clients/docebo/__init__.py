__all__ = ["DoceboRestClient"]

from dbacademy.clients.rest.common import ApiClient


class DoceboRestClient(ApiClient):
    """Docebo REST API client."""

    @staticmethod
    def from_environ(*, endpoint: str = None, username: str = None, password: str = None, consumer_key: str = None, consumer_secret: str = None) -> "DoceboRestClient":
        import os

        return DoceboRestClient(endpoint=endpoint or os.environ.get("DOCEBO_ENDPOINT"),
                                username=username or os.environ.get("DOCEBO_USERNAME"),
                                password=password or os.environ.get("DOCEBO_PASSWORD"),
                                consumer_key=consumer_key or os.environ.get("DOCEBO_CONSUMER_KEY"),
                                consumer_secret=consumer_secret or os.environ.get("DOCEBO_CONSUMER_SECRET"))

    @staticmethod
    def from_workspace(scope: str, *, endpoint: str = None, username: str = None, password: str = None, consumer_key: str = None, consumer_secret: str = None) -> "DoceboRestClient":
        from dbacademy import dbgems

        return DoceboRestClient(endpoint=endpoint or dbgems.dbutils.secrets.get(scope, "endpoint"),
                                username=username or dbgems.dbutils.secrets.get(scope, "username"),
                                password=password or dbgems.dbutils.secrets.get(scope, "password"),
                                consumer_key=consumer_key or dbgems.dbutils.secrets.get(scope, "consumer_key"),
                                consumer_secret=consumer_secret or dbgems.dbutils.secrets.get(scope, "consumer_secret"))

    def __init__(self,
                 endpoint: str = None,
                 throttle_seconds: int = 0,
                 *,
                 username: str,
                 password: str,
                 consumer_key: str,
                 consumer_secret: str):

        assert endpoint is not None, "The parameter \"endpoint\" must be specified"
        assert username is not None, "The parameter \"username\" must be specified"
        assert consumer_key is not None, "The parameter \"consumer_key\" must be specified"
        assert consumer_secret is not None, "The parameter \"consumer_secret\" must be specified"

        access_token = DoceboRestClient.authenticate(endpoint=endpoint,
                                                     consumer_key=consumer_key,
                                                     consumer_secret=consumer_secret,
                                                     username=username,
                                                     password=password)
        super().__init__(url=endpoint,
                         authorization_header=F"Bearer {access_token}",
                         throttle_seconds=throttle_seconds)

        from dbacademy.clients.docebo.manage import ManageClient
        self.manage = ManageClient(self)

        from dbacademy.clients.docebo.courses import CoursesClient
        self.courses = CoursesClient(self)

        from dbacademy.clients.docebo.events import EventsClient
        self.events = EventsClient(self)

        from dbacademy.clients.docebo.sessions import SessionsClient
        self.sessions = SessionsClient(self)

    @staticmethod
    def authenticate(*, endpoint: str, consumer_key: str, consumer_secret: str, username: str, password: str) -> str:
        import requests

        # Format the Payload
        payload = {
            'grant_type': 'password',
            'client_id': consumer_key,
            'client_secret': consumer_secret,
            'username': username,
            'password': password
        }

        # Request an OAuth Token
        url = f"{endpoint}/oauth2/token"
        response = requests.post(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 200, f"Expected the HTTP status code 200, found {response.status_code}: {response.text}"

        return response.json().get("access_token")
