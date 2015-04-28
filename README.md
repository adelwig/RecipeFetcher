# Recipe-Fetcher
This is a small python program that goes to the USDA web site
(http://recipefinder.nal.usda.gov/), downloads all recipes and
ingredients into a SQLite database (the folder has a working version
of it called recipes.db) and then serves the web page that takes
user's input and suggests recipes.

Works in Python 2.7. 

Dependencies (need to be downloaded separately):
- urllib
- sqllite3
- web
- BeautifulSoup
