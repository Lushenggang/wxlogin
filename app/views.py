from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect,HttpResponse
from ../redis import redis_db
from models import WXUserInfo

import json
import time
import urllib
import json

# Create your views here.

APPID="wx2d1d6aa2f86768d7"
APP_SECRET="6c909d49659ee0598ba1d46638388d11"
REDIRECT_URI="https://wyr.me/login/weixin"

def generate_url_params(info):
    lst=[]
    for key,value in info:
        lst.append("%s=%s"%(key,value))
    info_str="&".join(lst)
    return info_str

def login(request):
    check_login(request)

def check_login(request):
    if "user_wx_info" in request.session:
        token_id=request.session["user_wx_info"]
        token=redis_db.hget(token_id)
        data=json.loads(token)
        now_time=time.time()
        if now_time>data['access_time']+30*24*60*60:
            return wx_login(request)
        url="https://api.weixin.qq.com/sns/auth?%s"%([("access_token",data["access_token"]),("openid",data["openid"])])
        data=get_jsondata_by_url(url)
        if data.get("errcode")!=0:
            info=[("appid",APPID),("grant_type","refresh_token"),("refresh_token",data["refresh_token"])]
            url="https://api.weixin.qq.com/sns/oauth2/refresh_token?%s"%generate_url_params(info)
            data=get_jsondata_by_url(url)
            if "errcode" in data:
                return wx_login(request)
            data["access_token"]=now_time      
            redis_db.hset(data["openid"],json.dumps(data))
            refresh_user_info(user_data)
    return wx_login(request)

        
def wx_login(request):
    info=[
        ("appid",APPID),
        ("redirect_uri",REDIRECT_URI),
        ("response_type","code"),
        ("scope","snsapi_login"),
        ("state","xxx")] 
    url="https://open.weixin.qq.com/connect/qrconnect?%s#wechat_redirect"%generate_url_params(info)
    return HttpResponseRedirect(url)

def login_callback(request):
    code=request.GET.get('code')
    info=[
        ("appid",APPID),
        ("secret",APP_SECRET),
        ("code",code),
        ("grant_type","authorization_code"),
    ]
    url="https://api.weixin.qq.com/sns/oauth2/access_token?%s"%generate_url_params(info)
    now_time=time.time()
    data=get_jsondata_by_url(url)
    expires_in=data.get("expires_in")
    data["access_time"]=now_time
    access_token=data.get('access_token')
    openid=data.get('openid')
    redis_db.hset(openid,json_dumps(data))
    refresh_user_info(access_token,openid)
    return HttpResponse("%s"%user_data)

def refresh_user_info(access_token,openid):
    user_data=get_user_info_from_wechat(access_token,openid)
    save_user_info(user_data)

def get_jsondata_by_url(url):
    response=urllib.request.urlopen(url)
    response_json=response.read().decode("utf-8")
    print(response_json)
    data=json.loads(response_json)
    return data

def get_user_info_from_wechat(access_token,openid):
    info=[('access_token',access_token),('openid',openid)]
    url="https://api.weixin.qq.com/sns/userinfo?%s"%generate_url_params(info)
    data=get_jsondata_by_url(url)
    return data

def save_user_info(data):
    image_url=data["headimgurl"]
    response=urllib.request.urlopen(image_url)
    image_data=response.read()
    with open("../static/headimages/%s.jpg"%data["openid"],"wb") as image:
        image.write(image_data)
        image.flush()
    info_str=json.dumps(data)
    users=User.objects.all().filter(openid=data["openid"])
    if users:
        user=users[0]
        user.info_str=info_str
    else:
        user=WXUserInfo(openid=data["openid"],info_str=info_str)
    user.save()

def get_user_info_from_db(openid):
    users=WXUserInfo.objects.all().filter(openid=openid)
    if not users:
        return None
    user=users[0]
    info_str=user.info_str
    data=json.loads(info_str)
    return data

def index(request):
    return HttpResponse("<h1>login success</h1>")

def home(request):
    return HttpResponse("Hello~")


