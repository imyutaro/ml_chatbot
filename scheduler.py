from datetime import datetime
from datetime import timedelta
import os

from rocketchat_API.rocketchat import RocketChat

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
SLACK_CHANNEL = "#curation"
ROCKETCHAT_ACCOUNT_NAME = os.environ["ROCKETCHAT_USER"]
ROCKETCHAT_PASSWORD = os.environ["ROCKETCHAT_PASSWORD"]
ROCKETCHAT_SERVER_URL = os.environ["ROCKETCHAT_SERVER_URL"]
ROCHETCHAT_CHANNEL = "curation_bot"

def post_rocketchat_reactions():
    # 前日反応のあった投稿をピックアップして再投稿
    post_base_url = f"{ROCKETCHAT_SERVER_URL}channel/{ROCHETCHAT_CHANNEL}?msg="
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")

    rocket = RocketChat(
        ROCKETCHAT_ACCOUNT_NAME,
        ROCKETCHAT_PASSWORD,
        server_url=ROCKETCHAT_SERVER_URL)
    match_post = []
    # スタンプ等のリアクションがあった投稿
    match_post += [i for i in rocket.channels_history(rocket.channels_info(channel="curation_bot").json()["channel"]["_id"],
                                                      count=200,
                                                      oldest=yesterday, latest=now).json()["messages"]
                   if i.get("reactions")]
    # 「attachmentsを使うのは自動投稿くらいだろう」という仮定からのフィルタリングした投稿
    match_post += [i for i in rocket.channels_history(rocket.channels_info(channel="curation_bot").json()["channel"]["_id"],
                                                      count=200,
                                                      oldest=yesterday, latest=now).json()["messages"]
                   if i.get("attachments") is None and i.get("t") is None]
    # ユニークな投稿のidを取得
    match_post_id = list(set([i.get(["_id"]) for i in match_post]))
    if match_post:
        text = "反応のあった投稿一覧\n"
        text += "\n".join([f"{post_base_url}{i}" for i in match_post_id])
    else:
        text = "反応があった投稿はありませんでした"
    channel = ROCHETCHAT_CHANNEL
    post_block = {
        "channel": channel,
        "text": text,
    }
    rocket.chat_post_message(
        **post_block
    )

def main():
    post_rocketchat_reactions()

if __name__ == '__main__':
    main()
