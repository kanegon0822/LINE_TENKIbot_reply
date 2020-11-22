from flask import Flask,request,abort
from linebot import LineBotApi,WebhookHandler
import linebot
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent,TextMessage,TextSendMessage
from linebot.models.events import FollowEvent
import os
import psycopg2
import requests
import json


app=Flask(__name__)

def get_connection():
    dsn=os.environ.get('DATABASE_URL')
    return psycopg2.connect(dsn)
conn=get_connection()
cur=conn.cursor()

linebot_api=LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])

handler=WebhookHandler(os.environ['CHANNEL_SECRET'])


# 取得した天気APIキーを入力
apiKey = os.environ['TENKI_API']
 


@app.route("/callback",methods=['POST'])
def callback():
    signature=request.headers["X-Line-Signature"]
    body=request.get_data(as_text=True)

    try:
        handler.handle(body,signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent,message=TextMessage)
def handle_message(event):
    profile=linebot_api.get_profile(event.source.user_id)

    if event.message.text=='停止':
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM USER_info WHERE user_id=%s',(profile.user_id,))
            conn.commit()
        cur.close()
        conn.close()
        linebot_api.reply_message(event.reply_token,TextSendMessage(text='配信を停止します'))
    
    elif event.message.text=='確認kanegon0822':
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM USER_info')
                table=cur.fetchall()
        cur.close()
        conn.close()
        linebot_api.reply_message(event.reply_token,TextSendMessage(text=table))
    
    elif '配信' in event.message.text:
        push_message=event.message.text
        push_message=push_message.split('配信')
        place=push_message[-1].replace(' ','')
        # ベースURL
        baseUrl = "http://api.openweathermap.org/data/2.5/weather?"
        # 天気取得URL作成
        completeUrl = baseUrl + "q=" + place+"&appid=" + apiKey 
        # 天気レスポンス
        response = requests.get(completeUrl) 
        # レスポンスの内容をJSONフォーマットからPythonフォーマットに変換
        cityData = response.json()

        if cityData["cod"] != "404": 
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO USER_info (user_name, user_id, place) VALUES (%s,%s,%s)',(profile.display_name,profile.user_id,place))
                conn.commit()
            cur.close()
            conn.close()
            linebot_api.reply_message(event.reply_token,TextSendMessage(text='配信を受け付けました'))
        else:
            linebot_api.reply_message(event.reply_token,TextSendMessage(text='登録地が存在しません。\nもう一度、最初から入力してください。'))

    else:
        linebot_api.reply_message(event.reply_token,TextSendMessage(text=
            '天気予報を配信させる場合は「配信[登録地]」を\n配信を停止させる場合は「停止」を\n入力してください。\n※例えば、東京の場合は「配信tokyo」と入力します。'
        ))

@handler.add(FollowEvent)
def handle_follow(event):
    linebot_api.reply_message(event.reply_token,TextSendMessage(text=
        '登録ありがとうございます！！\n天気予報を配信させる場合は「配信[登録地]」を\n配信を停止させる場合は「停止」を\n入力してください。\n※例えば、東京の場合は「配信tokyo」と入力します。'
    ))


if __name__=='__main__':
    app.run()

