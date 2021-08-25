from datetime import timedelta
import json
import os
import requests

from attrdict import AttrDict
import tweepy
import yaml

consumer_key = os.environ["CONSUMER_KEY"]
consumer_secret = os.environ["CONSUMER_SECRET"]
access_token = os.environ["ACCESS_TOKEN_KEY"]
access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

# tweepy.StreamListener をオーバーライド
class MyStreamListener(tweepy.StreamListener):
    def __init__(self,user_list, print_test=False):
        self._user_list = user_list
        self._print_test = print_test
        super().__init__()

    def on_status(self, status):
        if self.is_invalid_tweet(status):
            if not self._print_test:
                post_to_slack(format_status(status))
            else:
                import ipdb; ipdb.set_trace()
                print(format_status(status))

    def is_invalid_tweet(self, status):
        """ツイートのフィルタリング"""
        if isinstance(status.in_reply_to_status_id, int):
            # リプライなら False
            return False
        elif "RT @" in status.text[0:4]:
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

def initialize(user_list, print_test=False):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    startStream(api.auth, [str(api.get_user(str(i)).id) for i in list(user_list)], print_test)

def startStream(auth, user_list, print_test=False):
    myStreamListener = MyStreamListener(user_list, print_test)
    myStream = tweepy.Stream(auth=auth, listener=myStreamListener)
    # myStream.userstream() #タイムラインを表示
    myStream.filter(follow=user_list)
    # myStream.filter(track=["#パラリンピック"]) #検索がしたい場合

def format_status(status):
    channel = '#curation'
    status.created_at += timedelta(hours=9) # 日本時間に
    username = str(status.user.name) + '@' + str(status.user.screen_name) + ' (from twitter)'
    if "RT @" in status.text[0:4]:
        tweet_url = status._json["retweeted_status"]["entities"]["urls"][0]["url"]
        text = f"【{username} さん】 RT URL: {tweet_url}"
    else:
        tweet_url = status.entities["urls"][0]["url"]
        text = f"【{username} さん】tweet URL: {tweet_url}"
    attachments = make_attachments(status)

    json_dat = {
        "channel": channel,
        "text": text,
        "attachments": attachments
    }
    json_dat = json.dumps(json_dat)
    return json_dat

def make_attachments(status):
    # TODO: RTの場合mediaは見れていない(?)
    if 'media' in status.entities:
        output = [
            {
                "blocks": [
                    make_context(status),
                    make_section(status)
                ]
            }
        ]
        images_blocks = [
            {
                "type": "image",
                "image_url": media["media_url"],
                "alt_text": "inspiration"
            } for media in status.extended_entities['media']
        ]
        output[0]["blocks"] = output[0]["blocks"] + images_blocks
        return output
    else:
        return [
            {
                "blocks": [
                    make_context(status),
                    make_section(status)
                ]
            }
        ]

def make_context(status):
    if "RT @" in status.text[0:4]:
        return {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": status._json["retweeted_status"]["user"]["profile_image_url"],
                    "alt_text": status._json["retweeted_status"]["user"]["name"]
                },
                {
                    "type": "mrkdwn",
                    "text": f"{status._json['retweeted_status']['user']['name']} tweet"
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

def make_section(status):
    if "RT @" in status.text[0:4]:
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": status._json["retweeted_status"]["extended_tweet"]["full_text"]
            }
        }
    else:
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": status.extended_tweet["full_text"]
            }
        }

def post_to_slack(json_dat):
    url = SLACK_WEBHOOK_URL
    requests.post(url, data=json_dat)

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

def main():
    config = load_config("./user_list.yaml")
    initialize(config.user_list, print_test=False)

if __name__ == "__main__":
    main()
