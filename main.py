import cgi
import os
import random

from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

class Issue(db.Model):
	author = db.UserProperty()
	desc = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)
	causedIssue = db.SelfReferenceProperty()
	agreedBy = db.IntegerProperty(default=0)
	totalCauses = db.IntegerProperty(default=0)
	totalAsked = db.IntegerProperty(default=0)
	priority = db.IntegerProperty(default=0)

def error(handler, message):	
	path = os.path.join(os.path.dirname(__file__), 'error.html')
	handler.response.out.write(template.render(path, {'message': message,}))

		
class MainPage(webapp.RequestHandler):
    def get(self):
		query = Issue.all().order('priority')
		totalIssues = query.count(1)
		if totalIssues == 0:
			issue = Issue()
			issue.desc = "voc&ecirc; est&aacute; aqui"
			existingCauses = query
		else:
			issue = query.get()
			existingCauses = Issue.gql("WHERE causedIssue = :1 ORDER BY agreedBy DESC LIMIT 10", issue )
			issue.totalAsked += 1
			issue.priority += 1 # lower the priority every time it is viewed
			issue.put()
		
		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'
      
		template_values={
			'issue': issue,
			'existingCauses' : existingCauses,
			'currentUser' : users.get_current_user(),
			'url': url,
			'url_linktext': url_linktext,
			}

		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))


class Item(webapp.RequestHandler):
	def get(self):
		key = db.Key.from_path('Issue',int(self.request.get("id")))
		issue = db.get(key)
		
		if not issue: 
			error(self, "N&atilde;o foi poss&iacute;vel achar o item " + str( self.request.get("id") ) )
			return
			
		existingCauses = Issue.gql("WHERE causedIssue = :1 ORDER BY agreedBy DESC LIMIT 10", issue )
		
		issue.totalAsked += 1
		issue.priority += 1 # lower the priority every time it is viewed
		issue.put()
		
		if users.get_current_user():
			url = users.create_logout_url(self.request.uri)
			url_linktext = 'Logout'
			login_header = "logado como " + users.get_current_user().nickname()
		else:
			url = users.create_login_url(self.request.uri)
			url_linktext = 'Login'
			login_header = "voc&ecirc; est&aacute; An&ocirc;nimo"
		
		template_values={
			'issue': issue,
			'issue_id' : issue.key().id(),
			'existingCauses' : existingCauses,
			'currentUser' : users.get_current_user(),
			'url': url,
			'url_linktext': url_linktext,
			'login_header': login_header,
			}

		path = os.path.join(os.path.dirname(__file__), 'index.html')
		self.response.out.write(template.render(path, template_values))

class Agree(webapp.RequestHandler):
	def get(self):
		key = db.Key.from_path('Issue',int(self.request.get("id")))
		issue = db.get(key)
		
		if not issue: 
			error(self, "N&atilde;o foi poss&iacute;vel achar o item " + str( self.request.get("id") ) )
			return
		
		issue.agreedBy += 1
		issue.priority -= 1 # higher priority when is agreed
		issue.put()
		print 'Content-Type: text/plain'
		print issue.agreedBy
		
		
class NewIssue(webapp.RequestHandler):
	def post(self):
		issue = Issue()

		if users.get_current_user():
			issue.author = users.get_current_user()

		issue.desc = self.request.get('newCause')
		if self.request.get('parentIssueKey') != '':
			parentKey = db.Key.from_path('Issue', int(self.request.get('parentIssueKey')))
			issue.causedIssue = Issue.get(parentKey)
		if issue.causedIssue:
			issue.causedIssue.totalCauses += 1
			issue.causedIssue.priority += 1 #lower the priority when a cause is proposed
			issue.causedIssue.put()
		issue.put()
		self.redirect('/issue?id=' + str( issue.key().id() ))

application = webapp.WSGIApplication([('/', MainPage),
									('/newIssue', NewIssue),
									('/agree', Agree),
									('/issue', Item)],
									debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()