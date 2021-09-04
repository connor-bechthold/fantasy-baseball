from bs4 import BeautifulSoup
from bs4 import Comment
import numpy as np
import pandas as pd
import requests
import pickle
from sklearn import linear_model
from sklearn.model_selection import train_test_split
from constants import teams_abbr


def season_scraper():

    """
    Scrapes the 2019, 2020, and 2021 seasons and creates a new dataframe with a compilation of those stats
    """

    data_frames = []

    seasons = ["https://www.baseball-reference.com/leagues/majors/2019-schedule.shtml", "https://www.baseball-reference.com/leagues/majors/2020-schedule.shtml", "https://www.baseball-reference.com/leagues/majors/2021-schedule.shtml"]

    for season in seasons:

        #getting the links to each boxscore
        boxscore_links = get_boxscore_links(season)

        #defining the columns needed
        data_columns = ["Date", "Team", "Player", "Position", "AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24", "Boxscore"]

        #creating the CV
        stats_cv = pd.DataFrame(columns = data_columns)

        stats_cv = scrape_boxscore_data(boxscore_links, stats_cv)

        data_frames.append(stats_cv)   

    merged_df = pd.concat(data_frames)
    merged_df.to_csv('Seasons.csv', line_terminator='\n', index=False)
    return merged_df


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
                
                average = "%.3f" % player_data.iloc[row - games_back:row][f"{col}"].mean()
                averages.append(average)
            
            player_data[f"{col}_{games_back}"] = averages

        new_df = new_df.append(player_data, ignore_index=True)
        print(player_data)


    #combining all existing columns 
    new_df = new_df[[i for i in new_df.columns.to_list() if i not in new_cols] + [i for i in new_df.columns.to_list() if i in new_cols]]    
    new_df.sort_values(by = ['Player', 'Date'], inplace=True)
    new_df.to_csv('AverageSeasons.csv', line_terminator='\n', index=False)  
    return new_df 


def create_model(data, games_back):

    """
    Trains and creates a linear regression model from the created dataframe, specifically using the
    input as the stats the player has accumulated over the past 2 games to predict what their OPS will be for 
    their next game
    """

    cols = ["AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24"]
    other_cols = [f"{col}_{games_back}" for col in cols]
    X = np.array(data[[col for col in other_cols]])
    y = np.array(data[["OPS"]])

    x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = linear_model.LinearRegression()

    model.fit(x_train, y_train)

    with open("OPSModel.pickle", "wb") as f:
        pickle.dump(model, f)

    print("Score:", model.score(x_test, y_test))


def get_boxscore_links(season):

    """
    Scrapes baseball reference for all the boxscore links on a given season page that is inputted as a parameter
    """

    boxscore_links = []

    season = requests.get(season)
    season_soup = BeautifulSoup(season.text, "html.parser")

    boxscore_tags = season_soup.find_all("a", string="Boxscore")

    for tag in boxscore_tags:
        href = tag.get("href")
        game_link = f"https://www.baseball-reference.com{href}"
        boxscore_links.append(game_link)

    return boxscore_links


def scrape_boxscore_data(boxscore_links, stats_cv):

    """
    Scrapes boxscore data from baseball reference given a link to the page, and adds it the dataframe passed in as a parameter
    """
    for boxscore_link in boxscore_links:

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
                    "RE24": player[19] or 0,
                    "Boxscore": boxscore_link
                }

                print(player_entry)

                #update the cv with the new row
                stats_cv = stats_cv.append(player_entry, ignore_index=True)

    return stats_cv

def string_to_date(date):
    """
    Converts a string date to a date in "YYYYMMDD" format
    """
    split = date.split(",")
    split = split[1:]
    month, day = split[0].strip().split(" ")
    if day in format_day:
        day = format_day[day]
    month = month_to_num[month]
    year = split[1]
    return f"{year.strip()}{month.strip()}{day.strip()}"


month_to_num = {
    "January": "01",
    "February": "02",
    "March": "03",
    "April": "04",
    "May": "05",
    "June": "06",
    "July": "07",
    "August": "08",
    "September": "09",
    "October": "10",
    "November": "11",
    "December": "12",
}


format_day = {
    "1": "01",
    "2": "02",
    "3": "03",
    "4": "04",
    "5": "05",
    "6": "06",
    "7": "07",
    "8": "08",
    "9": "09",
}