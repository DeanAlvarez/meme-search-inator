import webapp2
import jinja2
import os
import time
import datetime
from google.appengine.api import users
from google.appengine.ext import ndb
from models import Member

the_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class Message(ndb.Model):
    timestamp = ndb.StringProperty()
    sender = ndb.StringProperty()
    message = ndb.StringProperty()

class HomePage(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    data = {}
    if user:
        data["logged_in"] = True
        data["signout_url"] = users.create_logout_url('/')
        user = users.get_current_user()
        member_query = Member.query(Member.email == user.nickname())
        member = member_query.get()
        if member is None:
            data["logged_in"] = False
            data["login_url"] = users.create_login_url('/')
            data["register_url"] = users.create_login_url('/Registration')
        else:
            data["name"] = member.display_name
    else:
        data["logged_in"] = False
        data["login_url"] = users.create_login_url('/')
        data["register_url"] = users.create_login_url('/Registration')

    home_template = the_jinja_env.get_template('templates/HomePage.html')
    self.response.write(home_template.render(data))  # the response

class ResultsPage(webapp2.RequestHandler):
    pass

class RegistrationPage(webapp2.RequestHandler):
    def get(self):
        registration_template = the_jinja_env.get_template('templates/RegistrationPage.html')
        self.response.write(registration_template.render())  # the response

    def post(self):
        user = users.get_current_user()
        # Create a new member.
        member = Member(
            display_name = self.request.get('display_name'),
            email = user.nickname())
        # Store that Entity in Datastore.
        member.put()
        time.sleep(1)
        return webapp2.redirect("/")

class LoginPage(webapp2.RequestHandler):
    def get(self):
        login_url = users.create_login_url('/')
        login_html_element = '<a href="%s">Sign in</a>' % login_url
        self.response.write('Please log in.<br>' + login_html_element)

class MessagesPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        data = {}
        if user:
            member_query = Member.query(Member.email == user.nickname())
            member = member_query.get()
            data["logged_in"] = True
            data["message_list"] = Message.query().order(Message.timestamp)
            data["signout_url"] = users.create_logout_url('/')
            data["name"] = member.display_name
        else:
            data["logged_in"] = False
            data["login_url"] = users.create_login_url('/')
            data["register_url"] = users.create_login_url('/Registration')
        messages_template = the_jinja_env.get_template('templates/MessagesPage.html')
        self.response.write(messages_template.render(data))  # the response

    def post(self):
        user = users.get_current_user()
        member_query = Member.query(Member.email == user.nickname())
        member = member_query.get()
        now = datetime.datetime.now()
        #Create a new message.
        message = Message(
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S"),
            message = self.request.get('message'),
            sender = member.display_name
        )
        # Store that Entity in Datastore.
        message.put()
        time.sleep(1)
        return webapp2.redirect("/Messages")

class BlogPage(webapp2.RequestHandler):
    pass


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/Results', ResultsPage),
    ('/Registration', RegistrationPage),
    ('/Messages', MessagesPage),
    ('/Blog', BlogPage)
], debug=True)
