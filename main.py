from bs4 import BeautifulSoup
import pandas as pd
import requests

def season_scraper(season_url):
    """
    This function takes in a baseball reference URL for a given season
    and scrapes the stats for every player on every team
    """

    #getting the links to each boxscore
    boxscore_links = []

    season = requests.get(season_url)
    season_soup = BeautifulSoup(season.text, "html.parser")

    boxscore_tags = season_soup.find_all("a", string="Boxscore")

    for tag in boxscore_tags:
        href = tag.get("href")
        game_link = f"https://www.baseball-reference.com{href}"
        boxscore_links.append(game_link)

    #defining the columns needed
    data_columns = ["Date", "Team", "Player", "Position", "AB", "R", "H", "RBI", "BB", "SO", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24"]

    #creating the CV
    stats_cv = pd.DataFrame(columns = data_columns)

    #scraping each boxscore
    for link in boxscore_links:

        boxscore = requests.get(link)
        boxscore_soup = BeautifulSoup(boxscore.text, "html.parser")

        body = boxscore_soup.find("body")

        #getting the date
        title = body.find('h1')
        split_title = title.text.split(",")
        date = f"{split_title[1].strip()}, {split_title[2].strip()}"

        #getting the teams
        summary = body.find("div", {"class": "scorebox"})
        teams = summary.find_all("a", {"itemprop": "name"})
        team_one = teams[0].text
        team_two = teams[1].text
