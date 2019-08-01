import webapp2
import jinja2
import os
import time
from google.appengine.api import users
from google.appengine.ext import ndb
from models import Member
from seed_data import seed_data
from search import search

the_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

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

class LogoutPage(webapp2.RequestHandler):
    pass

class MessagePage(webapp2.RequestHandler):
    pass

class BlogPage(webapp2.RequestHandler):
    pass

class SeedData(webapp2.RequestHandler):
    def get(self):
        seed_data()
        self.response.write("test")

class qTest(webapp2.RequestHandler):
    def get(self):
        results = search('just eats monkey when your')
        out = ''
        for result in results:
            out += ("<img src="+result+">")
        self.response.write(out)

app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/Results', ResultsPage),
    ('/Registration', RegistrationPage),
    ('/Login',LoginPage),
    ('/Logout',LogoutPage),
    ('/Messages',MessagePage),
    ('/Blog', BlogPage),
    ('/SeedData',SeedData),
    ('/q',qTest)
    ], debug=True)
