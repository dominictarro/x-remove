import datetime
import json
import logging
import logging.handlers
import os
import sys
from typing import TypedDict

import httpx
import quart
from dotenv import load_dotenv
from quart import request, jsonify

from x_remove.api_details_refresher import XDotComAPIDetailsRefresher, APIOperation, api_details_lookup
from x_remove.settings import app_data_folder

load_dotenv()

DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

log_dir = app_data_folder / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=DEFAULT_LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

file_handler = logging.handlers.TimedRotatingFileHandler(
    (log_dir / "x-remove.log").as_posix(),
    when="midnight",
    interval=1,
)
file_handler.suffix = r"%Y-%m-%d"
file_handler.setLevel(DEFAULT_LOG_LEVEL)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger("root").addHandler(file_handler)


# Start the refresher daemon
refresher = XDotComAPIDetailsRefresher(interval=datetime.timedelta(hours=6))
refresher.start()


class RemoveRequest(TypedDict):
    user_id: str
    target_user_id: str
    headers: dict


def parse_cookies(cookie_string: str | None) -> dict | None:
    if not cookie_string:
        return None
    cookies = {}
    for cookie in cookie_string.split(';'):
        name, value = cookie.strip().split('=', 1)
        cookies[name] = value
    return cookies


app = quart.Quart(__name__)

@app.route('/', methods=['GET'])
async def index():
    return await quart.render_template('index.html')

@app.route('/remove', methods=['POST'])
async def remove_follower():
    data: RemoveRequest = RemoveRequest(await request.json)

    for field in RemoveRequest.__required_keys__:
        if field not in data:
            logging.info(f"Rejecting request due to missing required parameter {field}")
            return jsonify({"error": f"Missing required parameter {field}", "target_user_id": data.get("target_user_id"), "user_id": data.get("user_id")}), 400

    for header_to_remove in ("Origin", "Referer",):
        if header_to_remove in data["headers"]:
            data["headers"].pop(header_to_remove)

    data["headers"]["User-Agent"] = request.headers["User-Agent"]
    query_id = api_details_lookup[APIOperation.REMOVE_FOLLOWER]["queryId"]
    url = f"https://x.com/i/api/graphql/{query_id}/RemoveFollower"
    payload = {
        "variables": {"target_user_id": str(data["target_user_id"])},
        "queryId": query_id,
    }
    logging.info(f"Requesting X remove follower {data['target_user_id']} from {data['user_id']}")

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url,
                json=payload,
                headers=data["headers"],
                cookies=parse_cookies(data.get("cookies")) or request.cookies,
            )
            r.raise_for_status()
            return jsonify({"message": "Follower removed successfully", "target_user_id": data["target_user_id"], "user_id": data["user_id"]}), 200
    except httpx.HTTPStatusError as e:
        logging.error("Failed to remove follower", exc_info=e, stack_info=True)
        return jsonify({"message": f"Failed to remove follower: {e}", "target_user_id": data["target_user_id"], "user_id": data["user_id"]}), e.response.status_code
    except Exception as e:
        logging.error("Failed to remove follower", exc_info=e, stack_info=True)
        return jsonify({"message": f"Failed to remove follower: {e}", "target_user_id": data["target_user_id"], "user_id": data["user_id"]}), 500


class ListRequest(TypedDict):
    user_id: str
    headers: dict
    cursor: str | None = None
    count: int = 20


@app.route('/list', methods=['POST'])
async def list_followers():
    data: ListRequest = ListRequest(await request.json)

    data["headers"]["User-Agent"] = request.headers["User-Agent"]

    query_id = api_details_lookup[APIOperation.LIST_FOLLOWERS]["queryId"]
    url = f"https://x.com/i/api/graphql/{query_id}/Followers"

    payload = {
        "variables": {
            "userId": data["user_id"],
            "count": data["count"],
            "includePromotedContent": False,
        },
        "features": {
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_enhance_cards_enabled": False,
        },
        "size": 2,
    }
    if data["cursor"]:
        payload["variables"]["cursor"] = data["cursor"]
        logging.info(f"Requesting X list followers for {data['user_id']} with cursor {data['cursor']}")

    payload["variables"] = json.dumps(payload["variables"])
    payload["features"] = json.dumps(payload["features"])
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                url,
                params=payload,
                headers=data["headers"],
                cookies=parse_cookies(data.get("cookies")) or request.cookies,
            )
            r.raise_for_status()
            return jsonify(r.json()), 200
    except httpx.HTTPStatusError as e:
        logging.error("Failed to list followers", exc_info=e, stack_info=True)
        return jsonify({"message": f"Failed to list followers: {e}", "user_id": data["user_id"]}), e.response.status_code
    except Exception as e:
        logging.error("Failed to list followers", exc_info=e, stack_info=True)
        return jsonify({"message": f"Failed to list followers: {e}", "user_id": data["user_id"]}), 500

if __name__ == '__main__':
    app.run(debug=True)
