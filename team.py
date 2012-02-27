# Iron Puzzler team page handler

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import login
import logging
import model
import puzzle


def NormalizeVector(vector, minimum, maximum, target):
  saved = vector[:]

  diff = target * len(vector) - sum(vector)
  remain = len(vector)
  if diff > 0:
    avail = [(maximum - v, i) for i, v in enumerate(vector)]
  else:
    avail = [(v - minimum, i) for i, v in enumerate(vector)]
  for amt, i in sorted(avail):
    if diff > 0:
      adjust = min(diff / remain, amt)
    else:
      adjust = max(diff / remain, -amt)
    vector[i] += adjust
    diff -= adjust
    remain -= 1

  logging.info("%s -> %s" % (saved, vector))


class TeamPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    props = {
      "error": self.request.get_all("error"),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "team_puzzles": [],
      "other_puzzles": [],
      "errata_puzzles": [],
    }

    puzzle_props = {}
    for p in sorted(model.Puzzle.all().ancestor(game), key=puzzle.SortKey):
      pp = puzzle_props[p.key()] = model.GetProperties(p)
      pp.update({
        "guess_count": 0,
        "solve_teams": set(),
        "comment_count": 0,
        "vote_count": 0,
      })
      if pp.get("errata"):
        props["errata_puzzles"].append(pp)
      if p.parent_key() == team.key():
        props["team_puzzles"].append(pp)
      else:
        props["other_puzzles"].append(pp)

    feedback_keys = [
        db.Key.from_path("Feedback", str(team.key()), parent=pp["key"])
        for pp in props["other_puzzles"]]
    for key, feedback in zip(feedback_keys, model.Feedback.get(feedback_keys)):
      pp = puzzle_props.get(key.parent())
      if pp: pp["feedback"] = model.GetProperties(
          feedback or model.Feedback(key=key))

    no_scores = model.Feedback().scores
    for review in model.Feedback.all().ancestor(team):
      pp = puzzle_props.get(review.key().parent())
      if pp:
        if review.comment and review.comment.strip(): pp["comment_count"] += 1
        pp["vote_count"] += 1

    for guess in model.Guess.all().ancestor(game):
      pp = puzzle_props.get(guess.parent_key())
      if not pp: continue

      if guess.answer in pp["answers"]:
        pp["solve_teams"].add(guess.team.key())

      if guess.team.key() == team.key():
        if guess.answer in pp["answers"]: pp["solve_time"] = guess.timestamp
        pp["guess_count"] += 1

    self.response.out.write(template.render("team.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    if game.voting_enabled:
      sr = range(len(model.Feedback().scores))
      puzzles = model.Puzzle.all().ancestor(game)
      feedback_keys = [
          db.Key.from_path("Feedback", str(team.key()), parent=p.key())
          for p in puzzles]
      feedback = {}
      for p, f in zip(puzzles, model.Feedback.get(feedback_keys)):
        if p.key().parent() == team.key(): continue  # No self voting
        n = p.number
        score = [self.request.get("score.%s.%d" % (n, s)) for s in sr]
        score_orig = [self.request.get("score.%s.%d.orig" % (n, s)) for s in sr]
        if (score != score_orig) or not f:
          if not f: f = model.Feedback(parent=p, key_name=str(team.key()))
          for s in sr: f.scores[s] = puzzle.NormalizeScore(score[s])
          if not self.request.get("normalize"): f.put()
        feedback.setdefault(p.key().name(), []).append(f)

      if self.request.get("normalize"):
        for flist in feedback.values():
          for i in range(len(flist[0].scores)):
            vector = [f.scores[i] for f in flist]
            NormalizeVector(vector, 0, 5, 3)
            for f, s in zip(flist, vector): f.scores[i] = round(s * 10) / 10.0
          for f in flist: f.put()

    self.redirect("/team?t=%d" % team.key().id())
    team.name = self.request.get("name") or team.name
    team.email = self.request.get("email")

    set_pw = self.request.get("set_password")
    confirm_pw = self.request.get("confirm_password")
    if set_pw or confirm_pw:
      if set_pw != confirm_pw:
        self.response.headers["location"] += "&error=set_password"
      else:
        team.password = set_pw

    team.put()


app = webapp.WSGIApplication([("/team", TeamPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
