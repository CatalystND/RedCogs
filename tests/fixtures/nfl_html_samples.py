"""Sample HTML responses from plaintextsports.com for testing

These fixtures allow testing NFL scraping logic without hitting the live website.
"""

NFL_SAMPLE_HTML = """
<html>
<body>
<h1>National Football League</h1>
<p>Wild Card Round</p>

<h2>Today, January 13</h2>
<a href="/nfl/game1">
+--------------+
|  4:30 PM ET |
| 5 LAR 12-5 |
| 4 CAR 8-9 |
+--------- FOX +
</a>

<a href="/nfl/game2">
+--------------+
|  8:15 PM ET |
| 6 GB 11-6 |
| 3 PHI 14-3 |
+-------- NBC +
</a>

<h2>Tomorrow, January 14</h2>
<a href="/nfl/game3">
+--------------+
|  1:00 PM ET |
| 7 PIT 10-7 |
| 2 BUF 13-4 |
+-------- CBS +
</a>

<a href="/nfl/game4">
+--------------+
|  4:30 PM ET |
| 1 KC 15-2 |
| 6 MIA 11-6 |
+-------- NBC +
</a>

<h2>Sunday, January 15</h2>
<a href="/nfl/game5">
+--------------+
|  3:00 PM ET |
| 4 TB 10-7 |
| 5 DAL 12-5 |
+-------- FOX +
</a>

<h1>National Basketball Association</h1>
<p>This should stop NFL parsing</p>
</body>
</html>
"""

NFL_NO_GAMES_HTML = """
<html>
<body>
<h1>National Football League</h1>
<p>No games scheduled</p>
<h1>National Basketball Association</h1>
</body>
</html>
"""

NFL_MALFORMED_HTML = """
<html>
<body>
<h1>National Football League</h1>
<a href="/nfl/game1">
+--MALFORMED--+
| BAD DATA |
| INCOMPLETE
</a>
<h1>National Basketball Association</h1>
</body>
</html>
"""

NFL_GAME_NO_NETWORK = """
<html>
<body>
<h1>National Football League</h1>
<p>Wild Card Round</p>

<h2>Today, January 13</h2>
<a href="/nfl/game1">
+--------------+
|  1:00 PM ET |
| KC 14-3 |
| BUF 13-4 |
+--------------+
</a>

<h1>National Basketball Association</h1>
</body>
</html>
"""
