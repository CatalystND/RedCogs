"""Sample HTML responses from bristolmountain.com for testing

These fixtures allow testing Bristol scraping logic without hitting the live website.
"""

BRISTOL_SAMPLE_HTML = """
<html>
<body>
<h3>Lifts</h3>
<table>
<tr><th>Lift</th><th>Status</th></tr>
<tr><td>Rocket Lodge</td><td>Open</td></tr>
<tr><td>Galaxy Six</td><td>Open</td></tr>
<tr><td>Comet Express</td><td>Closed</td></tr>
<tr><td>Sunset Six</td><td>Open</td></tr>
</table>

<h3>Easier Trails</h3>
<table>
<tr><th>Trail</th><th>Status</th><th>Surface</th><th>Comments</th></tr>
<tr><td>Lower Rocket</td><td>Open</td><td>Packed Powder</td><td></td></tr>
<tr><td>Sunset Run</td><td>Open</td><td>Machine Groomed</td><td></td></tr>
</table>

<h3>More Difficult Trails</h3>
<table>
<tr><th>Trail</th><th>Status</th><th>Surface</th><th>Comments</th></tr>
<tr><td>Upper Rocket</td><td>Open</td><td>Machine Groomed</td><td></td></tr>
<tr><td>Galaxy Glades</td><td>Closed</td><td>Natural</td><td>Needs more snow</td></tr>
</table>

<h3>Most Difficult Trails</h3>
<table>
<tr><td>Outer Limits</td><td>Closed</td><td>Natural</td><td></td></tr>
<tr><td>Free Fall</td><td>Open</td><td>Packed Powder</td><td></td></tr>
</table>

<h3>Extremely Difficult Trails</h3>
<table>
<tr><td>Expert Chute</td><td>Closed</td><td>Natural</td><td></td></tr>
</table>
</body>
</html>
"""

BRISTOL_NO_TABLES_HTML = """
<html>
<body>
<p>Conditions not available</p>
<p>Please check back later</p>
</body>
</html>
"""

BRISTOL_MINIMAL_HTML = """
<html>
<body>
<h3>Lifts</h3>
<table>
<tr><th>Lift</th><th>Status</th></tr>
<tr><td>Rocket Lodge</td><td>Open</td></tr>
</table>

<h3>Easier Trails</h3>
<table>
<tr><th>Trail</th><th>Status</th><th>Surface</th><th>Comments</th></tr>
<tr><td>Lower Rocket</td><td>Open</td><td>Packed Powder</td><td></td></tr>
</table>
</body>
</html>
"""
