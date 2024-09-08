import datetime
import enum
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import TypedDict

import httpx
from fake_useragent import FakeUserAgent
from lxml import html

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@enum.unique
class APIOperation(str, enum.Enum):
    """An enumeration of the different API operations and their corresponding names in the API details."""

    LIST_FOLLOWERS = "Followers"
    REMOVE_FOLLOWER = "RemoveFollower"

class APIDetails(TypedDict):
    """A dictionary type for storing the details of an API endpoint."""

    queryId: str
    operationName: str
    operationType: str
    metadata: dict


api_details_lookup: dict[APIOperation, APIDetails] = {}


def get_app_data_folder(app_name: str) -> Path:
    """Get the path to the application data folder for the given application name.

    Args:
        app_name (str): The name of the application.

    """
    if os.name == 'nt':  # Windows
        base_dir = Path(os.getenv('APPDATA'))
    else:  # macOS and Linux
        base_dir = Path(os.getenv('HOME')) / '.local' / 'share'
    
    app_data_folder = base_dir / app_name
    
    # Create the directory if it doesn't exist
    app_data_folder.mkdir(parents=True, exist_ok=True)
    
    return app_data_folder

APP_NAME = "x-remove.com"
app_data_folder = get_app_data_folder(APP_NAME)
x_api_details_file: Path | None = None


def js_object_to_python_dict(js_object_str):
    """Converts a JavaScript object string to a Python dictionary.

    Args:
        js_object_str (str): A string containing a JavaScript object.

    Returns:
        dict: The Python dictionary equivalent of the JavaScript object.

    Example:

    ```js
    {a: 1, b: {c: "2", d: 3}, e: [4, 5, 6]}
    ```

    The above JavaScript object string will be converted to the following Python dictionary:

    ```python
    {"a": 1, "b": {"c": "2", "d": 3}, "e": [4, 5, 6]}
    ```
    """
    # Replace unquoted keys with quoted keys
    json_object_str = re.sub(r'(\w+):', r'"\1":', js_object_str)
    
    # Parse the cleaned string into a Python dictionary
    try:
        python_dict = json.loads(json_object_str)
    except json.JSONDecodeError as e:
        e.add_note(
            f"Original JavaScript object string: {js_object_str}"
        )
        raise e    
    return python_dict

def extract_api_details_from_obfuscated_javascript(js_code: str) -> dict[int, dict]:
    """Extracts API details from obfuscated JavaScript code. The input is a string
    containing the JavaScript code. The function returns a dictionary where the keys
    are the IDs of the API endpoints and the values are dictionaries containing the
    details of the API endpoints.

    Args:
        js_code (str): A string containing the JavaScript code.

    Returns:
        dict[int, dict]: A dictionary where the keys are the IDs of the API endpoints
        and the values are dictionaries containing the details of the API endpoints.

    Example:

    ```js
    {
        123: e => { e.exports = {a: 1, b: {c: "2", d: 3}, e: [4, 5, 6]}}
    }
    ```

    The above JavaScript code will be converted to the following Python dictionary:

    ```python
    {
        123: {"a": 1, "b": {"c": "2", "d": 3}, "e": [4, 5, 6]}
    }
    ```
    """
    pattern = re.compile(r'(\d+):\s*e\s*=>\s*{\s*e\.exports\s*=\s*({)')
    matches = pattern.finditer(js_code)

    result = {}
    for match in matches:
        id_ = int(match.group(1))
        start_index = match.end(2)
        end_index = find_matching_bracket(js_code, start_index)
        js_object_str = "{" + js_code[start_index:end_index + 1] + "}"
        result[id_] = js_object_to_python_dict(js_object_str)

    return result

def find_matching_bracket(code, start_index):
    """Finds the matching closing bracket in the code starting from the given index.

    Args:
        code (str): The code to search in.
        start_index (int): The index to start searching from.

    Returns:
        int: The index of the matching closing bracket.
    """
    stack = []
    for i in range(start_index, len(code)):
        if code[i] == '{':
            stack.append('{')
        elif code[i] == '}':
            stack.pop()
            if not stack:
                return i
    raise ValueError("No matching closing bracket found")


def get_x_dot_com_main_page_initial_redirect_url(client: httpx.Client) -> str:
    """Get the initial redirect URL from the main page of x.com. It parses the redirect
    from a script tag in the response HTML.

    Args:
        client (httpx.Client): The HTTP client to use for making requests. Will add cookies
        and headers as needed.

    Returns:
        str: The initial redirect URL.
    """

    r = client.get("https://x.com/")
    r.raise_for_status()

    tree = html.fromstring(r.text)
    script_tags = tree.xpath('//script[contains(text(), "document.location")]')
    if not script_tags:
        raise ValueError("Failed to find redirect script in response")
    script_content = script_tags[0].text_content()
    match = re.search(r'document\.location\s*=\s*"(.*?)"', script_content)
    if not match:
        raise ValueError("Failed to find redirect URL in response")
    return match.group(1)


def get_x_dot_com_redirect_post_data(client: httpx.Client, redirect_url: str) -> dict:
    """Get the POST data for the redirect request. It parses the form data from the
    redirect page and returns the url and body for the redirect request.

    Args:
        client (httpx.Client): The HTTP client to use for making requests. Will add cookies
        and headers as needed.
        redirect_url (str): The URL to which the redirect request will be made.

    Returns:
        dict: The redirect URL and body for the redirect request. Keys are 'url' and 'body'.
    """

    r_redirect = client.get(redirect_url)
    r_redirect.raise_for_status()

    tree_redirect = html.fromstring(r_redirect.text)
    form = tree_redirect.xpath('//form[@name="f"]')[0]
    return {
        "url": form.attrib['action'],
        "body": {input_elem.attrib['name']: input_elem.attrib['value'] for input_elem in form.xpath('.//input')}
    }

def post_x_dot_com_redirect_form(client: httpx.Client, redirect_url: str, form_data: dict):
    """Post the redirect form data to the redirect URL.

    Args:
        client (httpx.Client): The HTTP client to use for making requests. Will add cookies
        and headers as needed.
        redirect_url (str): The URL to which the redirect request will be made.
        form_data (dict): The form data to be posted.
    """

    r = client.post(redirect_url, data=form_data)
    if r.status_code != 302:
        # Throw an error if the status code is not 302
        r.raise_for_status()
        # If it was a 2xx, still raise some error
        raise ValueError(f"Expected 302 status code, got {r.status_code}")


def get_x_dot_com_main_page_main_js_url(client: httpx.Client) -> dict[str, str]:
    """Get the main page of x.com using the mx parameter. 

    Args:
        client (httpx.Client): The HTTP client to use for making requests. Will add cookies
        and headers as needed.

    Returns:
        dict: The main.js URL and the nonce value. Keys are 'url' and 'nonce'.
    """

    r = client.get("https://x.com/?mx=1")
    r.raise_for_status()
    tree = html.fromstring(r.text)
    link_tag = tree.xpath('//link[contains(@href, "main.") and contains(@href, ".js")]')
    if not link_tag:
        raise ValueError("Failed to find main.js link in response")
    main_js_url = link_tag[0].attrib['href']
    nonce = link_tag[0].attrib['nonce']
    return {
        "url": main_js_url,
        "nonce": nonce
    }

def get_x_dot_com_obfuscated_api_details(client: httpx.Client, main_js_url: str) -> dict[int, dict]:
    """Get the obfuscated API details from the main.js file. 

    Args:
        client (httpx.Client): The HTTP client to use for making requests. Will add cookies
        and headers as needed.
        main_js_url (str): The URL of the main.js file.

    Returns:
        dict[int, dict]: A dictionary where the keys are the IDs of the API endpoints
        and the values are dictionaries containing the details of the API endpoints.
    """

    r_main_js = client.get(main_js_url)
    r_main_js.raise_for_status()
    return extract_api_details_from_obfuscated_javascript(r_main_js.text)

def save_new_x_api_details(api_details: dict[int, dict]) -> Path:
    """Save the new API details to a file in the application data folder.

    Args:
        api_details (dict[int, dict]): The new API details to save.

    Returns:
        Path: The path to the saved file.
    """

    cur_dt = datetime.datetime.now().strftime(r"%Y-%m-%d_%H-%M-%S")
    new_fp = app_data_folder / f"x_api_details_{cur_dt}.json"
    with open(new_fp, "w") as f:
        json.dump(api_details, f, indent=2)
    return new_fp


def update_global_api_details(api_details: dict[int, APIDetails]):
    """Update the global API details dictionary with the new API details.

    Args:
        api_details (dict[int, dict]): The new API details to update.
    """
    api_op_lookup_new = {}
    for api_op in APIOperation:
        logger.debug("Looking for details for %s", api_op)
        for _, details in api_details.items():
            if details["operationName"] == api_op.value:
                api_op_lookup_new[api_op] = details
                break
        else:
            raise ValueError(f"Failed to find details for {api_op} in the new API details")

    global api_details_lookup
    api_details_lookup.update(api_op_lookup_new)


def refresh_x_dot_com_api_details(user_agent: str | None = None) -> str:
    user_agent = user_agent or FakeUserAgent(
        fallback="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/",
        browsers=["chrome", "edge", "firefox", "safari"],
        os=["windows", "macos", "linux"],
        platforms="pc",
        min_percentage=50,
    ).random
    logger.info("Refreshing API details with user agent: %s", user_agent)
    with httpx.Client(
        headers={
            "User-Agent": user_agent,
        }
    ) as client:

        logger.debug("Requesting main page for x.com")
        redirect_url = get_x_dot_com_main_page_initial_redirect_url(client)
        logger.debug(f"Redirecting to: {redirect_url}")
        r_redirect_args = get_x_dot_com_redirect_post_data(client, redirect_url)

        logger.debug(f"Redirecting to: {r_redirect_args['url']} with body: {r_redirect_args['body']}")
        post_x_dot_com_redirect_form(client, r_redirect_args["url"], r_redirect_args["body"])

        logger.debug("Redirecting to main page with mx parameter")
        main_redirect_2_data = get_x_dot_com_main_page_main_js_url(client)

        logger.debug(f"Requesting main.js from: {main_redirect_2_data['url']}")
        api_details = get_x_dot_com_obfuscated_api_details(client, main_redirect_2_data["url"])

        new_fp = save_new_x_api_details(api_details)
        global x_api_details_file
        x_api_details_file = new_fp
        logger.info("Successfully extracted and saved API details to file: %s", new_fp.as_posix())

        update_global_api_details(api_details)


class XDotComAPIDetailsRefresher(threading.Thread):
    def __init__(self, interval: datetime.timedelta, user_agent: str | None = None):
        super().__init__(
            name="XDotComAPIDetailsRefresher",
            daemon=True,
        )
        self.interval = interval
        self.user_agent = user_agent
        self.stop_event = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            refresh_x_dot_com_api_details(self.user_agent)
            logger.info("Waiting for %s before refreshing again", self.interval)
            self.stop_event.wait(self.interval.total_seconds())

if __name__ == "__main__":
    logging.basicConfig(
        level=logger.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=f'{__name__}.log',
    )

    # Start the refresher script
    import time
    refresher = XDotComAPIDetailsRefresher(interval=datetime.timedelta(hours=6))
    logger.info("Starting refresher")
    refresher.start()
    time.sleep(10)
    logger.info("Stopping refresher")
    refresher.stop_event.set()
    logger.info("Joining refresher")
    refresher.join(1)
    logger.info("Refresher stopped")
    logger.info("Last saved API details file: %s", x_api_details_file.as_posix())
