from datetime import timedelta
import json
import os
import requests

from attrdict import AttrDict
from rocketchat_API.rocketchat import RocketChat
import tweepy
import yaml

TWITTER_CONSUMER_KEY = os.environ["CONSUMER_KEY"]
TWITTER_CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
TWITTER_ACCESS_TOKEN = os.environ["ACCESS_TOKEN_KEY"]
TWITTER_ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_CHANNEL = "#curation"
ROCKETCHAT_ACCOUNT_NAME = os.environ["ROCKETCHAT_USER"]
ROCKETCHAT_PASSWORD = os.environ["ROCKETCHAT_PASSWORD"]
ROCKETCHAT_SERVER_URL = os.environ["ROCKETCHAT_SERVER_URL"]
ROCHETCHAT_CHANNEL = "curation_bot"

# tweepy.StreamListener をオーバーライド
class MyStreamListener(tweepy.StreamListener):
    def __init__(self,user_list, print_test=False,
                 is_slack_post=True, is_rocketchat_post=True):
        self._user_list = user_list
        self._print_test = print_test
        self._is_slack_post = is_slack_post
        self._is_rocketchat_post = is_rocketchat_post
        super().__init__()

    def on_status(self, status):
        if self.is_invalid_tweet(status):
            if not self._print_test:
                if self._is_slack_post:
                    post_to_slack(format_status(status, chat_format="slack"))
                if self._is_rocketchat_post:
                    post_to_rocketchat(format_status(status, chat_format="rocketchat"))
            else:
                try:
                    format_status(status)
                except Exception:
                    import ipdb; ipdb.set_trace()
                print(format_status(status))

    def is_invalid_tweet(self, status):
        """ツイートのフィルタリング"""
        if isinstance(status.in_reply_to_status_id, int):
            # リプライなら False
            return False
        elif "@" in status.text[0]:
            # リプライなら False
            return False
        elif hasattr(status, "retweeted_status"):  # Check if Retweet
            if status.user.id_str in set(self._user_list):
                # user_listのRTならTrue
                return True
            else:
                # RT なら False
                return False
        else:
            return True

    def on_error(self, status_code):
        if status_code == 420:
            return False

def initialize(user_list, print_test=False,
               is_slack_post=True, is_rocketchat_post=True):
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    startStream(api.auth, [str(api.get_user(str(i)).id) for i in list(user_list)], print_test,
                is_slack_post=is_slack_post, is_rocketchat_post=is_rocketchat_post)

def startStream(auth, user_list, print_test=False,
                is_slack_post=True, is_rocketchat_post=True):
    myStreamListener = MyStreamListener(user_list, print_test,
                                        is_slack_post=is_slack_post,
                                        is_rocketchat_post=is_rocketchat_post)
    myStream = tweepy.Stream(auth=auth, listener=myStreamListener)
    # myStream.userstream() #タイムラインを表示
    # myStream.filter(track=["#パラリンピック"]) #検索がしたい場合
    myStream.filter(follow=user_list)

def format_status(status, chat_format="slack"):
    if chat_format == "slack":
        channel = SLACK_CHANNEL
    elif chat_format == "rocketchat":
        channel = ROCHETCHAT_CHANNEL
    status.created_at += timedelta(hours=9) # 日本時間に
    username = str(status.user.name) + '@' + str(status.user.screen_name) + ' (from twitter)'
    base_url = "https://twitter.com/twitter/statuses/"
    tweet_url = base_url + status.id_str
    if hasattr(status, "retweeted_status"):  # Check if Retweet
        text = f"【{username} さん】 RT URL : {tweet_url}"
    else:
        text = f"【{username} さん】tweet URL : {tweet_url}"
    if chat_format == "slack":
        attachments = make_attachments_slack(status)
    elif chat_format == "rocketchat":
        attachments = make_attachments_rocketchat(status)

    post_block = {
        "channel": channel,
        "text": text,
        "attachments": attachments
    }
    return post_block

def make_attachments_rocketchat(status):
    if hasattr(status, "retweeted_status"):  # Check if Retweet
        try:
            text = status.retweeted_status.extended_tweet["full_text"]
        except AttributeError:
            text = status.retweeted_status.text
        try:
            # rocketchatは1つずつしか画像を載せられない
            media = status.retweeted_status.extended_tweet["entities"]["media"][0]
        except:
            media = None
        attachments = [{
            "author_icon": status.retweeted_status.user.profile_image_url,
            "author_name": f"{status.retweeted_status.user.name} tweet",
            "author_link": f"https://twitter.com/{status.retweeted_status.user.screen_name}",
            "color": "#8AC75A",
            "text": text.replace("\n", "</br>"),
            "image_url": media
        }]
    else:
        try:
            text = status.extended_tweet["full_text"]
        except AttributeError:
            text = status.text
        try:
            media = status.extended_tweet["entities"]["media"][0]
        except:
            media = None
        attachments = [{
            "author_icon": status.user.profile_image_url,
            "author_name": f"{status.user.name} tweet",
            "author_link": f"https://twitter.com/{status.user.screen_name}",
            "color": "#8AC75A",
            "text": text.replace("\n", "</br>"),
            "image_url": media
        }]

    return attachments

def make_attachments_slack(status):
    try:
        if hasattr(status, "retweeted_status"):  # Check if Retweet
            media = status.retweeted_status.extended_tweet["entities"]["media"]
            output = [
                {
                    "blocks": [
                        make_context_slack(status),
                        make_section_slack(status)
                    ]
                }
            ]
            images_blocks = [
                {
                    "type": "image",
                    "image_url": m["media_url"],
                    "alt_text": "inspiration"
                } for m in media
            ]
        else:
            media = status.extended_tweet["entities"]["media"]
            output = [
                {
                    "blocks": [
                        make_context_slack(status),
                        make_section_slack(status)
                    ]
                }
            ]
            images_blocks = [
                {
                    "type": "image",
                    "image_url": m["media_url"],
                    "alt_text": "inspiration"
                } for m in media
            ]
        output[0]["blocks"] = output[0]["blocks"] + images_blocks
        return output
    except:
        return [
            {
                "blocks": [
                    make_context_slack(status),
                    make_section_slack(status)
                ]
            }
        ]

def make_context_slack(status):
    if hasattr(status, "retweeted_status"):  # Check if Retweet
        return {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": status.retweeted_status.user.profile_image_url,
                    "alt_text": status.retweeted_status.user.name
                },
                {
                    "type": "mrkdwn",
                    "text": f"{status.retweeted_status.user.name} tweet"
                }
            ]
        }
    else:
        return {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": status.user.profile_image_url,
                    "alt_text": status.user.name
                },
                {
                    "type": "mrkdwn",
                    "text": f"{status.user.name} tweet"
                }
            ]
        }

def make_section_slack(status):
    if hasattr(status, "retweeted_status"):  # Check if Retweet
        try:
            text = status.retweeted_status.extended_tweet["full_text"]
        except AttributeError:
            text = status.retweeted_status.text
    else:
        try:
            text = status.extended_tweet["full_text"]
        except AttributeError:
            text = status.text
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }

def post_to_slack(post_block):
    json_dat = json.dumps(post_block)
    requests.post(SLACK_WEBHOOK_URL, data=json_dat)

def post_to_rocketchat(post_block):
    # 私はaliasが使えない(権限の問題?)
    RocketChat(
        ROCKETCHAT_ACCOUNT_NAME,
        ROCKETCHAT_PASSWORD,
        server_url=ROCKETCHAT_SERVER_URL).chat_post_message(
            **post_block
        )

def load_config(config_path: str) -> AttrDict:
    """config(yaml)ファイルを読み込む

    Parameters
    ----------
    config_path : string
        config fileのパスを指定する

    Returns
    -------
    config : attrdict.AttrDict
        configを読み込んでattrdictにしたもの
    """
    with open(config_path, 'r', encoding='utf-8') as fi_:
        return AttrDict(yaml.load(fi_, Loader=yaml.SafeLoader))

def main(print_test=False, is_slack_post=True, is_rocketchat_post=True):
    config = load_config("./user_list.yaml")
    initialize(config.user_list, print_test=print_test,
               is_slack_post=is_slack_post, is_rocketchat_post=is_rocketchat_post)

if __name__ == "__main__":
    main()
