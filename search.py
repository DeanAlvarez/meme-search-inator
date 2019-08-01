from models import *

def search(user_query):
    unicode_user_query = unicode(user_query)
    all_tag_objects = Tag.query().fetch()
    all_tag_dict = {}
       
    for tag_object in all_tag_objects:
        tag_name = tag_object.tag_name
        all_tag_dict[tag_name] = tag_object
        
    all_tag_objects = None

    words = unicode_user_query.split()

    #print(set(words))
    #print set(all_tag_dict.keys())

    user_query_tags = set()
    word_set = set()
    for word in words:
        word_set.add(word)
    

    for word in words:
        
        temp_set = set()
        temp_set.add(word)
        #print(temp_set <= (set(all_tag_dict)))

        
        if temp_set <= (set(all_tag_dict)):
            user_query_tags.add(word)

    #print(user_query_tags)
    
    freq_dict = {}

    for q_tag_name in user_query_tags:
        tag_query = Tag.query(Tag.tag_name==q_tag_name).fetch()
        tag_key = tag_query[0].key
        mat_query = Meme_and_Tag.query(Meme_and_Tag.tag==tag_key).fetch()
        for q in mat_query:
            meme_query = Meme.query(Meme.key==q.meme).fetch()
            for meme in meme_query:
                if( meme.key not in freq_dict ):
                    freq_dict[meme.key] = 1
                else:
                    freq_dict[meme.key] += 1

        #print(mat_query)
        #print(" ")

    #print(freq_dict)
    ordered_memes = []
    for item in sorted(freq_dict,key=freq_dict.get, reverse=True):
        #print item, freq_dict[item]
        meme = Meme.query(Meme.key==item).fetch()[0].image_url
        ordered_memes.append(meme)

    return ordered_memes
