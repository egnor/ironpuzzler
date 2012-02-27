# Iron Puzzler submission page handler

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import datetime
import re
import login
import model

from puzzle import MaybeGetPuzzle, NormalizeAnswer, NormalizeScore

# Forbid more than this many guesses in this many seconds.
SPAM_SECONDS = 60
SPAM_GUESSES = 2


class GuessPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)

    feedback = model.Feedback.get_or_insert(str(team.key()), parent=puzzle)

    props = {
      "error": self.request.get_all("error"),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "puzzle": model.GetProperties(puzzle),
      "feedback": model.GetProperties(feedback),
      "guesses": [],
      "solve_teams": set(),
    }

    for guess in model.Guess.all().ancestor(puzzle).order("-timestamp"):
      if guess.answer in puzzle.answers:
        props["solve_teams"].add(guess.team.key())
      if guess.team.key() == team.key():
        props["guesses"].append(model.GetProperties(guess))
        if guess.answer in puzzle.answers:
          props["guesses"][-1]["is_correct"] = True
          props.setdefault("solve_time", guess.timestamp)

    self.response.out.write(template.render("guess.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)

    self.redirect("/guess?t=%d&p=%s" % (team.key().id(), self.request.get("p")))

    if self.request.get("comment", None) is not None:
      feedback = model.Feedback(parent=puzzle, key_name=str(team.key()))
      feedback.comment = self.request.get("comment")
      if game.solving_enabled or game.voting_enabled:
        for s in range(len(feedback.scores)):
          feedback.scores[s] = NormalizeScore(self.request.get("score.%d" % s))
      feedback.put()
      self.redirect("/team?t=%d" % team.key().id())

    answer = NormalizeAnswer(self.request.get("answer", ""))
    if answer and game.solving_enabled:
      start_time = datetime.datetime.now() - datetime.timedelta(0, SPAM_SECONDS)
      guesses = model.Guess.all().ancestor(puzzle).filter("team", team.key())
      recent = guesses.filter("timestamp >=", start_time).fetch(SPAM_GUESSES)
      if answer in [g.answer for g in recent]:
        self.response.headers["location"] += "&error=dup"
      elif len(recent) >= SPAM_GUESSES:
        self.response.headers["location"] += "&error=spam"
      else:
        model.Guess(parent=puzzle, answer=answer, team=team).put()


app = webapp.WSGIApplication([("/guess", GuessPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
