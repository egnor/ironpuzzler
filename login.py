# Iron Puzzler team login handler

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import admin
import model
import urllib

def CookiePassword(team, request):
  pw = urllib.unquote(request.cookies.get("password", ""))
  return (pw == team.password) and pw or None


def GetTeamOrRedirect(game, request, response):
  try: team = model.Team.get_by_id(int(request.get("t")), parent=game)
  except Exception: team = None
  if not team:
    response.set_status(404)
    return None

  if request.path == "/login" or admin.GetAdminEmail(game): return team
  if CookiePassword(team, request): return team

  if request.body:
    response.set_status(403)  # Can't redeliver POST
  else:
    response.set_status(302)
    response.headers.add_header("Location",
        "/login?t=%d&u=%s" % (team.key().id(), urllib.quote(request.url)))
  return None


class LoginPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    props = {
      "error": self.request.get_all("error"),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "target": self.request.get("u"),
    }

    self.response.headers.add_header(
        "Set-Cookie", "password=; Max-Age=0; Path=/")
    self.response.out.write(template.render("login.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    target = self.request.get("u") or ("/team?t=%d" % team.key().id())
    password = self.request.get("pw")
    if password == team.password:
      self.redirect(target)
      self.response.headers.add_header("Set-Cookie",
          "password=%s; Max-Age=%d; Path=/" % (
          urllib.quote(password), 7*24*60*60))
    else:
      self.redirect("/login?t=%d&u=%s&error=password" % (
          team.key().id(), urllib.quote(target)))


app = webapp.WSGIApplication([("/login", LoginPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
