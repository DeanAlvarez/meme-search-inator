import webapp2
import jinja2
import os

the_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class HomePage(webapp2.RequestHandler):
    pass

class ResultsPage(webapp2.RequestHandler):
    pass

class CreateAccount(webapp2.RequestHandler):
    pass

class LoginPage(webapp2.RequestHandler):
    pass

class LogoutPage(webapp2.RequestHandler):
    pass

class MessagePage(webapp2.RequestHandler):
    pass

class BlogPage(webapp2.RequestHandler):
    pass


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/Results', ResultsPage),
    ('/CreateAccount',CreateAccount),
    ('/Login', LoginPage),
    ('/Logout', LogoutPage),
    ('/Messages', MessagePage),
    ('/Blog', BlogPage)
], debug=True)
