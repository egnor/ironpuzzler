# Iron Puzzler team page handler

import logging
import urllib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import admin
import model

def GetTeam(game, request):
  try: team_id = int(request.get("t"))
  except Exception: return None
  return model.Team.get_by_id(team_id, parent=game)


def IsUserAuthorized(game, team, request):
  if admin.IsUserAdmin(game): return True
  password = urllib.unquote(request.cookies.get("team_password", ""))
  return password == team.password


class TeamPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = GetTeam(game, self.request)
    if not team: return self.error(404)

    props = {
      "error": dict([(e, 1) for e in self.request.get_all("error")]),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "user_ok": IsUserAuthorized(game, team, self.request),
    }

    self.response.out.write(template.render("team.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = GetTeam(game, self.request)
    if not team: return self.error(404)

    redirect_url = "/team?t=%d" % team.key().id()

    login_pw = self.request.get("login_password", default_value=None)
    if login_pw is not None:
      self.response.headers.add_header("Set-Cookie",
         "team_password=%s; Path=/; Max-Age=604800" % urllib.quote(login_pw))
      if login_pw != team.password: redirect_url += "&error=login_password"
      return self.redirect(redirect_url)

    if not IsUserAuthorized(game, team, self.request): return self.error(403)

    name = self.request.get("name")
    if name: team.name = name

    set_pw = self.request.get("set_password")
    confirm_pw = self.request.get("confirm_password")
    if set_pw or confirm_pw:
      if set_pw != confirm_pw:
        redirect_url += "&error=set_password"
      else:
        team.password = set_pw

    team.put()
    self.redirect(redirect_url)



app = webapp.WSGIApplication([("/team", TeamPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
