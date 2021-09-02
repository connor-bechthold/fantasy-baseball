from bs4 import BeautifulSoup
from bs4 import Comment
import numpy as np
import pandas as pd
import requests
from constants import teams_abbr
from helpers import string_to_date

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

    for boxscore_link in boxscore_links[:30]:

        boxscore = requests.get(boxscore_link)
        boxscore_soup = BeautifulSoup(boxscore.text, "html.parser")

        body = boxscore_soup.find("body")

        #getting the teams
        summary = body.find("div", {"class": "scorebox"})
        teams = summary.find_all("a", {"itemprop": "name"})
        team_one = teams_abbr[teams[0].text]
        team_two = teams_abbr[teams[1].text]

        #getting the date
        date_block = summary.find("div", {"class": "scorebox_meta"})
        date = string_to_date(date_block.find("div").text)

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
                    "AB": player[0] or 0,
                    "R": player[1] or 0,
                    "H": player[2] or 0,
                    "RBI": player[3] or 0,
                    "BB": player[4] or 0,
                    "SO": player[5] or 0,
                    "PA": player[6] or 0,
                    "BA": player[7] or 0,
                    "OBP": player[8] or 0,
                    "SLG": player[9] or 0,
                    "OPS": player[10] or 0,
                    "WPA": player[13] or 0,
                    "aLI": player[14] or 0,
                    "WPA+": player[15] or 0,
                    "WPA-": player[16][:-1] or 0,
                    "RE24": player[19] or 0
                }

                #update the cv with the new row
                stats_cv = stats_cv.append(player_entry, ignore_index=True)

    # print(stats_cv)
    # stats_cv.to_csv('Test.csv', line_terminator='\n', index=False)
    return stats_cv


def average_stats(data, games_back):
    """
    This function is passed in the dataframe computed from the previous function,
    and also the number of games the user wants to compile stats from. This is to ensure
    any one off games a player may have. For ex. if "games_back = 4", for each game, the stats from
    the last 4 games the player has played in will be compiled and averaged, and then trained against
    the OPS the player recorded for that game
    """
    cols = ["AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24"]

    #creating dataframe with new cols
    new_cols = [f"{stat}_{games_back}" for stat in cols]
    new_df = pd.DataFrame(columns=new_cols)

    #getting a list of unique players in the DF
    players = np.array(data.Player.value_counts().index)

    for player in players:
        player_data = data[data.Player == player]
        player_data = player_data.sort_values(by = "Date")
        
        for col in cols:
            averages = []
            for row in range(len(player_data)):
                #Check if the row should be looked at 
                if row < games_back:
                    averages.append(0)
                    continue
                
                average = player_data.iloc[row - games_back:row][f"{col}"].mean()
                averages.append(average)
            
            player_data[f"{col}_{games_back}"] = averages

        new_df = new_df.append(player_data, ignore_index=True)


    #combining all existing columns 
    new_df = new_df[[i for i in new_df.columns.to_list() if i not in new_cols] + [i for i in new_df.columns.to_list() if i in new_cols]]    
    new_df.sort_values(by = ['Player', 'Date'], inplace=True)
    new_df.to_csv('Test.csv', line_terminator='\n', index=False)   




#ex input from 2019 season
cheese = season_scraper("https://www.baseball-reference.com/leagues/majors/2019-schedule.shtml")
average_stats(cheese, 1)