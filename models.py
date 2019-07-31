from google.appengine.ext import ndb

class Meme(ndb.Model):
    image_url = ndb.StringProperty(required=True)

class Tag(ndb.Model):
    tag_name = ndb.StringProperty(required=True)

class Meme_and_Tag(ndb.Model):
    meme = ndb.KeyProperty(Meme)
    tag = ndb.KeyProperty(Tag)

class Member(ndb.Model):
    display_name = ndb.StringProperty()
    email = ndb.StringProperty()
