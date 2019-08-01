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


    meme4_tags = ['me','my',"mom's",'charger','damaged','mom','indiana','jones','stealing','swap']
    meme4_url = 'https://preview.redd.it/brufv00xata31.jpg?width=640&crop=smart&auto=webp&s=78873b95132f58011480d1e313648d38a7d74653'

    meme5_tags = ['*dad*',"dosen't",'want','dog','*family*','family','gets','anyway','dad','and','the','man','barbecue','barbecuing','lake']
    meme5_url = 'https://preview.redd.it/i0qdjsl7fgd31.jpg?width=640&crop=smart&auto=webp&s=d04cb03276fb56cba162dceb479c0e242b8084c8'

    meme6_tags = ['when','you','wake','up','first','at','a','the','sleepover','matrix','alien','pod']
    meme6_url = 'https://preview.redd.it/2gz4uascnl931.jpg?width=640&crop=smart&auto=webp&s=6850524ed8a6b995e4c891ad1ace7e06bd806757'

    meme7_tags = ["dosen't",'want','dog','*family*','family','gets','anyway','dad','a','the','racoon','drinking','beer','bottle']
    meme7_url = 'https://preview.redd.it/tlz6ecb3shd31.jpg?width=640&crop=smart&auto=webp&s=88f86ab852eebcd5ace22803d507d81fe2e23742'

    meme8_tags = ["dosen't",'want','dog','*family*','family','gets','anyway','dad','a','the','keanu','reeves','holding','beagal']
    meme8_url = 'https://i.kym-cdn.com/photos/images/newsfeed/001/523/529/68f.jpg'

    meme9_tags = ["dosen't",'want','dog','*family*','family','gets','anyway','dad','a','the','star','wars','starwars','han','solo','chewy','chewbaca']
    meme9_url = 'https://i.kym-cdn.com/photos/images/original/001/523/544/4d6.png'

    meme10_tags = ['dad',"dosen't",'want','dog','family','gets','anyway','and','the','rock','dwayne','johnson','little','french','bulldog']
    meme10_url = 'https://i.kym-cdn.com/photos/images/newsfeed/001/523/527/9fb.jpg'

    all_tags = {}
    upload_memes(meme1_tags,meme1_url,all_tags)
    upload_memes(meme2_tags,meme2_url,all_tags)    
    upload_memes(meme3_tags,meme3_url,all_tags)
    upload_memes(meme4_tags,meme4_url,all_tags)
    upload_memes(meme5_tags,meme5_url,all_tags)
    upload_memes(meme6_tags,meme6_url,all_tags)
    upload_memes(meme7_tags,meme7_url,all_tags)
    upload_memes(meme8_tags,meme8_url,all_tags)
    upload_memes(meme9_tags,meme9_url,all_tags)
    upload_memes(meme10_tags,meme10_url,all_tags)
