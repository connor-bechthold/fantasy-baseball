from bs4 import BeautifulSoup
from bs4 import Comment
import pandas as pd
import requests
from constants import teams_abbr

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
    data_columns = ["Date", "Team", "Player", "Position", "AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24"]

    #creating the CV
    stats_cv = pd.DataFrame(columns = data_columns)

    for boxscore_link in boxscore_links:

        boxscore = requests.get(boxscore_link)
        boxscore_soup = BeautifulSoup(boxscore.text, "html.parser")

        body = boxscore_soup.find("body")

        #getting the date
        title = body.find('h1')
        split_title = title.text.split(",")
        date = f"{split_title[1].strip()}, {split_title[2].strip()}"

        #getting the teams
        summary = body.find("div", {"class": "scorebox"})
        teams = summary.find_all("a", {"itemprop": "name"})
        team_one = teams_abbr[teams[0].text]
        team_two = teams_abbr[teams[1].text]

        #getting the table data for both teams (note that this data is wrapped in a comment so extra steps need to be taken)
        table_sections = body.find_all("div", {"class": "table_wrapper"}, limit=2)

        tables = []
        for table in table_sections:
            data = table.find(string=lambda text: isinstance(text, Comment))
            parsed_data = BeautifulSoup(data, 'lxml')
            tables.append(parsed_data)


        for i in range(len(tables)):

            table = tables[i]
            rows = table.find_all('tr')
            rows = rows[1:len(rows) - 1]

            for row in rows:

                if row.get("class") == ['spacer']:
                    continue

                first_line = row.find('th')

                #getting the player name and position (we need to verify the player is not a pitcher in the case of the NL)
                name_and_position = first_line.text.split()

                position = name_and_position[-1]

                if position == 'P':
                    continue
                
                name = ' '.join(name_and_position[:-1])

                player = [stat.text.strip() for stat in row.find_all("td")]

                #From this data, construct a line in the CV
                # data_columns = ["Date", "Team", "Player", "Position", "AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24"]

                player_entry = {
                    "Date": date,
                    "Team": team_one if i == 0 else team_two,
                    "Player": name,
                    "Position": position,
                    "AB": player[0],
                    "R": player[1],
                    "H": player[2],
                    "RBI": player[3],
                    "BB": player[4],
                    "SO": player[5],
                    "PA": player[6],
                    "BA": player[7],
                    "OBP": player[8],
                    "SLG": player[9],
                    "OPS": player[10],
                    "WPA": player[13],
                    "aLI": player[14],
                    "WPA+": player[15],
                    "WPA-": player[16][:-1],
                    "RE24": player[19]
                }

                #update the cv with the new row
                stats_cv = stats_cv.append(player_entry, ignore_index=True)

    stats_cv.to_csv('Season.csv', line_terminator='\n', index=False)


#ex input from 2019 season
season_scraper("https://www.baseball-reference.com/leagues/majors/2019-schedule.shtml")