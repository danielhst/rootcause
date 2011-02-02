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
	depth = db.IntegerProperty()
	def evalDepth(self):
		if self.causedIssue:
			return self.causedIssue.evalDepth() + 1 
		return 0

def error(handler, message):	
	path = os.path.join(os.path.dirname(__file__), 'error.html')
	handler.response.out.write(template.render(path, {'message': message,}))

def addLoginValues(handler,values):
	if users.get_current_user():
		url = users.create_logout_url(handler.request.uri)
		url_linktext = 'Logout'
		login_header = "logado como " + users.get_current_user().nickname()
	else:
		url = users.create_login_url(handler.request.uri)
		url_linktext = 'Login'
		login_header = "voc&ecirc; est&aacute; An&ocirc;nimo"
	
	values["login_url"] = url 
	values["login_linktext"] = url_linktext 
	values["login_header"] = login_header 
	values["currentUser"] = users.get_current_user() 
		
		
class MainPage(webapp.RequestHandler):
	def get(self):
		page = self.request.get("page")
		if not page:
			page = 0
		issues = Issue.all().order('totalCauses').fetch(page * 50, (page + 1) * 50)
		template_values={
			'issues': issues,
			}
		path = os.path.join(os.path.dirname(__file__), 'panel.html')
		self.response.out.write(template.render(path, template_values))
		
class Random(webapp.RequestHandler):
    def get(self):
		randIndex = random.randint(1, 10)
		issue = Issue.all().order('priority').fetch(randIndex, randIndex + 1 )[0]
		if not issue:
			issue = Issue()
			issue.desc = "voc&ecirc; est&aacute; aqui!"
			existingCauses = None
		else:
			existingCauses = Issue.gql("WHERE causedIssue = :1 ORDER BY agreedBy DESC LIMIT 10", issue )
			issue.totalAsked += 1
			issue.priority += 1 # lower the priority every time it is viewed
			issue.put()
		
		template_values={
			'issue': issue,
			'existingCauses' : existingCauses,
			}
		
		addLoginValues(self, template_values)
		
		path = os.path.join(os.path.dirname(__file__), 'issue.html')
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
			}
		
		addLoginValues(self, template_values)
		
		path = os.path.join(os.path.dirname(__file__), 'issue.html')
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
		issue.depth = 0
		if self.request.get('parentIssueKey') != '':
			parentKey = db.Key.from_path('Issue', int(self.request.get('parentIssueKey')))
			issue.causedIssue = Issue.get(parentKey)
		if issue.causedIssue:
			issue.causedIssue.totalCauses += 1
			issue.causedIssue.priority += 1 #lower the priority when a cause is proposed
			issue.causedIssue.put()
			issue.depth = issue.causedIssue.depth + 1
		issue.put()
		self.redirect('/issue?id=' + str( issue.key().id() ))

		
class TreeLeafs(webapp.RequestHandler):		
	def get(self):
		counter = 0;
		leafs = Issue.all().filter("totalCauses =", 0).order("causedIssue")
		result = []
		for l in leafs:
			if not l.depth:
				l.depth = l.evalDepth()
				l.put()
			
			setattr(l, "leafColumn", counter * 200 )
			setattr(l, "leafRow", l.depth * 150 )
			
			depth = l.depth	
			result.append(l)
			counter += 1
			
		template_values={
			'leafs': result,
			}

		path = os.path.join(os.path.dirname(__file__), 'tree.html')
		self.response.out.write(template.render(path, template_values))
		

class TreeRoot(webapp.RequestHandler):	
	def get(self):
		root = db.get(db.Key.from_path('Issue',int(self.request.get("id"))))
		rootGiven = true
		if not root: 
			root = Issue.all().filter("depth=", 0).get()
			rootGiven = false
			
		childs = Issue.filter("causedIssue=", root ).order("agreedBy")
		

application = webapp.WSGIApplication([('/', MainPage),
									('/random', Random),
									('/newIssue', NewIssue),
									('/agree', Agree),
									('/issue', Item),
									('/tree', TreeRoot)],
									debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()