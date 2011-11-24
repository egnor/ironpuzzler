# Iron Puzzler administrative interface handler

import random
import re

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

MAX_TEAMS = 1000
PUZZLES_EACH = 2

def IsUserAdmin(game):
  if users.is_current_user_admin(): return True
  user = users.get_current_user()
  return user and (user.email() in game.admin_users)


class AdminPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(dest_url="/admin"))
      return

    game = model.GetGame()
    props = model.GetProperties(game)
    props["user_email"] = user.email()
    props["user_logout_url"] = users.create_logout_url(dest_url="/admin")
    props["user_ok"] = IsUserAdmin(game)
    props["teams"] = teams = []
    for team in model.Team.all().ancestor(game).order("name").fetch(MAX_TEAMS):
      team_props = model.GetProperties(team)
      if not team_props.get("numbers"):
        team_props["numbers"] = ["-", "-"]
      teams.append(team_props)

    self.response.out.write(template.render("admin.dj.html", props))

  def post(self):
    game = model.GetGame()
    if not IsUserAdmin(game):
      self.error(403)
      return

    ingredients = [self.request.get("ingredient%d" % i) for i in range(3)]
    admin_users = re.split(r'[,\s]+', self.request.get("admin_users"))
    game.ingredients = [i for i in ingredients if i]
    game.ingredients_visible = bool(self.request.get("ingredients_visible"))
    game.admin_users = [u for u in admin_users if u]
    game.login_enabled = bool(self.request.get("login_enabled"))
    game.put()

    if self.request.get("new_team"):
      team = model.Team(parent=game)
      team.name = self.request.get("new_team")
      team.password = self.request.get("new_password")
      team.put()

    if self.request.get("assign_numbers"):
      teams = model.Team.all().ancestor(game).order("name").fetch(MAX_TEAMS)
      for team in teams: team.numbers = []
      for p in range(PUZZLES_EACH):
        numbers = range(p * len(teams), (p + 1) * len(teams))
        random.shuffle(numbers)
        for team, n in zip(teams, numbers): team.numbers.append(n)
      for team in teams: team.put()

    self.redirect("/admin")


app = webapp.WSGIApplication([("/admin", AdminPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
