from datetime import datetime
from datetime import timedelta
import os

from rocketchat_API.rocketchat import RocketChat

# SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
# SLACK_CHANNEL = "#curation"
ROCKETCHAT_ACCOUNT_NAME = os.environ["ROCKETCHAT_USER"]
ROCKETCHAT_PASSWORD = os.environ["ROCKETCHAT_PASSWORD"]
ROCKETCHAT_SERVER_URL = os.environ["ROCKETCHAT_SERVER_URL"]
ROCKETCHAT_CHANNEL = "curation_bot"
ROCKETCHAT_DISCUSSION_CHANNEL = "discussion_curation_bot"

def post_rocketchat_reactions():
    # 前日反応のあった投稿をピックアップして再投稿
    post_base_url = f"{ROCKETCHAT_SERVER_URL}/channel/{ROCKETCHAT_CHANNEL}?msg="
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    yesterday = (datetime.now() - timedelta(days=1) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")

    rocket = RocketChat(
        user_id=ROCKETCHAT_ACCOUNT_NAME,
        auth_token=ROCKETCHAT_PASSWORD,
        server_url=ROCKETCHAT_SERVER_URL)

    match_post = []
    for i in rocket.channels_history(rocket.channels_info(channel="curation_bot").json()["channel"]["_id"],
                                                      count=500,
                                                      oldest=yesterday, latest=now).json()["messages"]:
        # スタンプ等のリアクションがあった投稿
        # or
        # 「attachmentsを使うのは自動投稿くらいだろう」という仮定からattachmentsがついていない投稿全てを所得する処理
        # （bot以外の投稿を全て取得するための処理）
        if (i.get("reactions")) or (i.get("attachments") is None and i.get("t") is None):
            match_post.append(i)
    match_post = sorted(match_post, key=lambda x: x["ts"])

    if match_post:
        emoji = ":smile:"
        text = f"反応のあった投稿一覧↓  #{ROCKETCHAT_DISCUSSION_CHANNEL}もご活用ください〜\n"
        for i in match_post:
            exist_reaction = i.get("reactions")
            if exist_reaction:
                # reactionの絵文字をメッセージの先頭に連結させるための処理
                reactions = " ".join(exist_reaction.keys())
            else:
                reactions = ""
            text += f"{reactions} {post_base_url}{i['_id']}\n"
    else:
        emoji = ":kanashimi:"
        text = "反応があった投稿はありませんでした"
    channel = ROCKETCHAT_CHANNEL
    post_block = {
        "channel": channel,
        "text": text,
        "emoji": emoji,
    }
    # 元Rocket.chatのチャンネルへ再投稿
    rocket.chat_post_message(
        **post_block
    )
    # ディスカッションチャンネルへ投稿
    post_block.update({"channel": ROCKETCHAT_DISCUSSION_CHANNEL})
    rocket.chat_post_message(
        **post_block
    )

def main():
    post_rocketchat_reactions()

if __name__ == '__main__':
    main()
