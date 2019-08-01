from google.appengine.api import images
import ujson 
from PIL import Image
from models import Meme,Tag,Meme_and_Tag
import sys

def seed_data():

    #dog meme
    meme1_tags = ['when','your','dog','eats','your','philosophy','homework','sunset','beach']
    meme1_url = 'https://pics.me.me/when-your-dog-eats-your-philosophy-homework-36107763.png'
    
    meme2_tags = ['dj','djs',"aren't",'real','musicians','they','just','push','buttons','pianist','monkey','looking','away']
    meme2_url = 'https://preview.redd.it/wlfvzaftdtm21.jpg?width=640&crop=smart&auto=webp&s=6b07d830421190e6e36106a0f1c4b8df011e8151'
    
    meme3_tags = ['when','your','estimated','time','of','arrival','on','google','maps','goes','from','5:40','to','5:38','i','am','speed','cars','lightning','mcqueen']
    meme3_url = 'https://preview.redd.it/yezsyiqj3h731.jpg?width=640&crop=smart&auto=webp&s=dfe3abc581c0f0b2270e51f21090a8b9271344c1'

    tags = {}


    meme1 = Meme(image_url=meme1_url).put()
    meme1_tag_objects = []
    for tag in meme1_tags:
        if not tag in tags:
            tags[tag] = Tag(tag_name=tag).put()
        temp_meme_tag = Meme_and_Tag(meme=meme1,tag=tags[tag]).put()

    
    meme2 = Meme(image_url=meme2_url).put()
    meme2_tag_objects = []
    for tag in meme2_tags:
        if not tag in tags:
            tags[tag] = Tag(tag_name=tag).put()
        temp_meme_tag = Meme_and_Tag(meme=meme2,tag=tags[tag]).put()


    meme3 = Meme(image_url=meme3_url).put()
    meme3_tag_objects = []
    for tag in meme3_tags:
        if not tag in tags:
            tags[tag] = Tag(tag_name=tag).put()
        temp_meme_tag = Meme_and_Tag(meme=meme3,tag=tags[tag]).put()
