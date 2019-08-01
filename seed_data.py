from google.appengine.api import images
import ujson 
from PIL import Image
from models import Meme,Tag,Meme_and_Tag
import sys

def upload_memes(tags,url,all_tags):
    meme = Meme(image_url=url).put()
    meme_tag_objects = []
    for tag in tags:
        if not tag in all_tags:
            all_tags[tag] = Tag(tag_name=tag).put()
        temp_meme_tag = Meme_and_Tag(meme=meme,tag=all_tags[tag]).put()

def seed_data():

    #dog meme
    meme1_tags = ['when','your','dog','eats','your','philosophy','homework','sunset','beach']
    meme1_url = 'https://pics.me.me/when-your-dog-eats-your-philosophy-homework-36107763.png'
    
    meme2_tags = ['dj','djs',"aren't",'real','musicians','they','just','push','buttons','pianist','monkey','looking','away']
    meme2_url = 'https://preview.redd.it/yezsyiqj3h731.jpg?width=640&crop=smart&auto=webp&s=dfe3abc581c0f0b2270e51f21090a8b9271344c1'


    meme3_tags = ['when','your','estimated','time','of','arrival','on','google','maps','goes','from','5:40','to','5:38','i','am','speed','cars','lightning','mcqueen']
    meme3_url = 'https://preview.redd.it/wlfvzaftdtm21.jpg?width=640&crop=smart&auto=webp&s=6b07d830421190e6e36106a0f1c4b8df011e8151'


    all_tags = {}
    upload_memes(meme1_tags,meme1_url,all_tags)
    upload_memes(meme2_tags,meme2_url,all_tags)    
    upload_memes(meme3_tags,meme3_url,all_tags)    
