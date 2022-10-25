from __future__ import annotations
from typing import Any, Container, Dict, List, Literal, Type, TypeVar, Union
from pprint import pformat
from dbacademy.common import deprecated, print_warning
import requests

__all__ = ["ApiContainer", "ApiClient", "DatabricksApiException",
           "HttpStatusCodes", "HttpMethod", "HttpReturnType", "IfNotExists", "IfExists",
           "Item", "ItemId", "ItemOrId"]

HttpStatusCodes = Union[int, Container[int]]
HttpMethod = Literal["GET", "PUT", "POST", "DELETE", "PATCH", "HEAD", "OPTIONS"]
HttpReturnType = TypeVar("HttpReturnType", bound=Union[dict, str, bytes, requests.Response, None])

IfNotExists = Literal["error", "ignore"]
IfExists = Literal["create", "error", "ignore", "overwrite", "update"]

Item = Dict
ItemId = Union[int, str]
ItemOrId = Union[int, str, Dict]


class ApiContainer(object):

    T = TypeVar('T')

    def __call__(self: T) -> T:
        """Returns itself.  Provided for backwards compatibility."""
        return self
    pass

    def help(self):
        for member_name in dir(self):
            if member_name.startswith("__"):
                continue
            member = getattr(self, member_name)
            if isinstance(ApiContainer, member):
                print(f"{member_name}")
            if isinstance(deprecated, member):
                pass
            elif callable(member):
                print(f"{member_name}()")


class ApiClient(ApiContainer):

    url: str = None

    def __init__(self,
                 url: str,
                 *,
                 token: str = None,
                 user: str = None,
                 password: str = None,
                 authorization_header: str = None,
                 client: ApiClient = None,
                 throttle_seconds: int = 0,
                 verbose: bool = False):
        """
        Create a Databricks REST API client.

        Args:
            url: The common base URL to the API endpoints.  e.g. https://workspace.cloud.databricks.com/API/
            token: The API authentication token.  Defaults to None.
            user: The authentication username.  Defaults to None.
            password: The authentication password.  Defaults to None.
            authorization_header: The header to use for authentication.
                By default, it's generated from the token or password.
            client: A parent ApiClient from which to clone settings.
            throttle_seconds: Number of seconds to sleep between requests.
        """
        super().__init__()
        import requests
        from urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter

        # if verbose: print("ApiClient.__init__, url: " + url)
        # if verbose: print("ApiClient.__init__, client: " + str(client))

        if client and "://" not in url:
            url = client.url.lstrip("/") + "/" + url.rstrip("/")

        if authorization_header:
            pass
        elif token is not None:
            authorization_header = 'Bearer ' + token
        elif user is not None and password is not None:
            import base64
            encoded_auth = (user + ":" + password).encode()
            authorization_header = "Basic " + base64.standard_b64encode(encoded_auth).decode()
        elif client is not None:
            authorization_header = client.session.headers["Authorization"]
        else:
            raise ValueError("Must specify one of token, password, or authorization_header")

        if not url.endswith("/"):
            url += "/"

        if throttle_seconds > 0:
            s = "" if throttle_seconds == 1 else "s"
            print_warning("WARNING", f"Requests are being throttled by {throttle_seconds} second{s} per request.")

        self.url = url
        self.user = user
        self.throttle_seconds = throttle_seconds
        self.read_timeout = 300   # seconds
        self.connect_timeout = 5  # seconds
        self._last_request_timestamp = 0
        self.verbose = verbose

        backoff_factor = self.connect_timeout
        retry = Retry(connect=Retry.BACKOFF_MAX / backoff_factor, backoff_factor=backoff_factor)

        self.session = requests.Session()
        self.session.headers = {'Authorization': authorization_header, 'Content-Type': 'text/json'}
        # noinspection HttpUrlsUsage
        self.session.mount('http://', HTTPAdapter(max_retries=retry))
        self.session.mount('https://', HTTPAdapter(max_retries=retry))

    def api_simple(self, _http_method: HttpMethod, _endpoint_path: str, *,
                   _expected: HttpStatusCodes = None, **data) -> Union[str, Dict]:
        """
        DEPRECATED: Use DatabricksApi.api instead.
        """
        return self.api(_http_method, _endpoint_path, data, _expected=_expected)

    def api_raw(self, _http_method: HttpMethod, _endpoint_path: str, _data=None, *,
                _expected: HttpStatusCodes = None) -> requests.Response:
        return self.api(_http_method=_http_method, _endpoint_path=_endpoint_path, _data=_data,
                        _expected=_expected, _return_type=requests.Response)

    def api(self, _http_method: HttpMethod, _endpoint_path: str, _data: dict = None, *,
            _expected: HttpStatusCodes = None, _return_type: Type[HttpReturnType] = dict,
            **data: Any) -> HttpReturnType:
        """
        Invoke the Databricks REST API.

        Args:
            _http_method: 'GET', 'PUT', 'POST', 'DELETE', 'PATCH', 'HEAD', or 'OPTIONS'
            _endpoint_path: The path to append to the URL for the API endpoint, excluding the leading '/'.
                For example: path="2.0/secrets/put"
            _data: Payload to attach to the HTTP request.  GET requests encode as params, all others as json.
            _expected: HTTP response status codes to treat as expected rather than as an error.
            _return_type: Determines what type of result is returned.  It may be any of the following:
               str: Return the body as a text str.
               dict: Parse the body as json and return a dict.
               bytes: Return the body as binary data.
               requests.Response: Return the HTTP response object.
               None: Return None.
            **data: Any kwargs are appended to the _data payload.  Values here take priority over values
               specified in _data.

        Returns:
            The return value varies depending on the requested _return_type.  See above.

        Raises:
            requests.HTTPError: If the API returns an error and on_error='raise'.
        """
        import json
        if _data is None:
            _data = {}
        if data:
            _data = _data.copy()
            _data.update(data)
        self._verify_hostname()
        self._throttle_calls()
        if _endpoint_path.startswith(self.url):
            _endpoint_path = _endpoint_path[len(self.url):]
        elif _endpoint_path.startswith("http"):
            raise ValueError(f"endpoint_path must be relative url, not {_endpoint_path !r}.")
        url = self.url + _endpoint_path.lstrip("/")
        timeout = (self.connect_timeout, self.read_timeout)
        if _http_method in ('GET', 'HEAD', 'OPTIONS'):
            params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in _data.items()}
            response = self.session.request(_http_method, url, params=params, timeout=timeout)
        else:
            # if self.verbose: print(json.dumps(data, indent=4))
            response = self.session.request(_http_method, url, data=json.dumps(_data), timeout=timeout)
        self._raise_for_status(response, _expected)
        # TODO: Should we really return None on errors?  Kept for now for backwards compatibility.
        if not (200 <= response.status_code < 300):
            return None
        if _return_type == requests.Response:
            return response
        elif _return_type == str:
            return response.text
        elif _return_type == bytes:
            return response.content
        elif _return_type is None:
            return None
        elif _return_type == dict:
            try:
                return response.json()
            except ValueError:
                return {
                    "_status": response.text,
                    "_response": response.text
                }

    def _verify_hostname(self):
        """Verify the host for the url-endpoint exists.  Throws socket.gaierror if it does not."""
        from urllib.parse import urlparse
        from socket import gethostbyname, gaierror
        from requests.exceptions import ConnectionError
        url = urlparse(self.url)
        try:
            gethostbyname(url.hostname)
        except gaierror as e:
            raise ConnectionError("DNS lookup for hostname failed") from e

    def _throttle_calls(self):
        if self.throttle_seconds <= 0:
            return
        import time
        now = time.time()
        elapsed = now - self._last_request_timestamp
        sleep_seconds = self.throttle_seconds - elapsed
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        self._last_request_timestamp = time.time()

    @staticmethod
    def _raise_for_status(response: requests.Response, expected: Union[int, Container[int]] = None) -> None:
        """
        If response.status_code is `2xx` or in `expected`, do nothing.
        Raises :class:`DatabricksApiException` for 4xx Client Error, :class:`HTTPError`, for all other status codes.
        """
        if 200 <= response.status_code < 300:
            return
        if expected is None:
            expected = ()
        elif type(expected) == str:
            expected = (int(expected),)
        elif type(expected) == int:
            expected = (expected,)
        elif not isinstance(expected, Container):
            raise ValueError(
                f"The parameter was expected to be of type str, int, tuple, list or set, found {type(expected)}")
        if response.status_code in expected:
            return

        if isinstance(response.reason, bytes):
            try:
                reason = response.reason.decode('utf-8')
            except UnicodeDecodeError:
                reason = response.reason.decode('iso-8859-1')
        else:
            reason = response.reason

        if 100 <= response.status_code < 200:
            error_type = 'Informational'
        elif 300 <= response.status_code < 400:
            error_type = 'Redirection'
        elif 400 <= response.status_code < 500:
            error_type = 'Client Error'
        elif 500 <= response.status_code < 600:
            error_type = 'Server Error'
        else:
            error_type = 'Unknown Error'

        try:
            body = pformat(response.json(), indent=2)
        except ValueError:
            body = response.text

        http_error_msg = f'{response.status_code} {error_type}: {reason} for url: {response.url}'
        http_error_msg += '\n Response from server: \n {}'.format(body)
        e = requests.HTTPError(http_error_msg, response=response)
        if 400 <= response.status_code < 500:
            e = DatabricksApiException(http_exception=e)
        raise e

    def simple_get(self, url: str, expected: Union[int, List[int]] = 200, **data) -> Union[None, str, Dict]:
        """
        :param url:
        :param expected: either a single HTTP status code or a list of status codes
        :param data:
        :return: None when expected includes 404, str when the content
        type is text and a dictionary when the content type is JSON
        """
        return self.api("GET", url, _data=data, _expected=expected)

    def simple_post(self, url: str, expected=200, **data) -> dict:
        return self.api("POST", url, _data=data, _expected=expected)

    def simple_put(self, url: str, expected=200, **data) -> dict:
        return self.api("PUT", url, _data=data, _expected=expected)

    def simple_delete(self, url: str, expected=200, **data) -> dict:
        return self.api("DELETE", url, _data=data, _expected=expected)

    def simple_patch(self, url: str, expected=200, **data) -> dict:
        return self.api("PATCH", url, _data=data, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_patch", action="ignore")
    def execute_patch_json(self, url: str, params: dict, expected=200) -> dict:
        return self.api("PATCH", url, params, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_patch", action="error")
    def execute_patch(self, url: str, params: dict, expected=200):
        return self.api_raw("PATCH", url, params, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_post", action="ignore")
    def execute_post_json(self, url: str, params: dict, expected=200) -> dict:
        return self.api("POST", url, params, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_post", action="error")
    def execute_post(self, url: str, params: dict, expected=200):
        return self.api_raw("POST", url, params, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_put", action="ignore")
    def execute_put_json(self, url: str, params: dict, expected=200) -> dict:
        return self.api("PUT", url, params, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_put", action="error")
    def execute_put(self, url: str, params: dict, expected=200):
        return self.api_raw("PUT", url, params, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_get", action="ignore")
    def execute_get_json(self, url: str, expected=200) -> Union[dict, None]:
        return self.api("GET", url, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_get", action="error")
    def execute_get(self, url: str, expected=200):
        return self.api_raw("GET", url, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_delete", action="ignore")
    def execute_delete_json(self, url: str, expected=(200, 404)) -> dict:
        return self.api("DELETE", url, _expected=expected)

    @deprecated(reason="Use ApiClient.simple_delete", action="error")
    def execute_delete(self, url: str, expected=(200, 404)):
        return self.api_raw("DELETE", url, _expected=expected)


class DatabricksApiException(Exception):
    def __init__(self, message=None, http_code=None, http_exception=None):
        import json
        if http_exception:
            self.__cause__ = http_exception
            self.cause = http_exception
            try:
                self.body = json.loads(http_exception.response.text)
                self.message = self.body.get("message", self.body.get("error", http_exception.response.text))
                self.error_code = self.body.get("error_code", -1)
            except ValueError:
                self.body = http_exception.response.text
                self.message = self.body
                self.error_code = -1
            self.method = http_exception.request.method
            self.endpoint = http_exception.request.path_url
            self.http_code = http_exception.response.status_code
            self.request = http_exception.request
            self.response = http_exception.response
        else:
            self.__cause__ = None
            self.cause = None
            self.body = message
            self.method = None
            self.endpoint = None
            self.http_code = http_code
            self.error_code = -1
            self.request = None
            self.response = None
        if message:
            self.message = message
        self.args = (self.method, self.endpoint, self.http_code, self.error_code, self.message)

    def __repr__(self):
        return (f"DatabricksApiException(message={self.message!r}, "
                f"http_code={self.http_code!r}, "
                f"http_exception={self.__cause__!r})")

    def __str__(self):
        return repr(self)
