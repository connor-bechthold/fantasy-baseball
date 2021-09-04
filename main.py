from pandas.io.parsers import read_csv
from helpers import season_scraper, average_stats, create_model, get_boxscore_links, scrape_boxscore_data 
import numpy as np
import pandas as pd
import pickle
import itertools
from os import path

#User sequencing

#First check if a pickle file exists. If it doesn't, then the model needs to be created
model_exists = path.exists("OPSModel.pickle")
if not model_exists:

    #Scrape the 2021, 2020, and 2019 seasons
    seasons_df = season_scraper()
    seasons_df = read_csv("Seasons.csv")

    #Get the averages for the past 2 games
    seasons_df = average_stats(seasons_df, 2)
    seasons_df = read_csv("AverageSeasons.csv")

    #Run the model
    create_model(seasons_df, 2)

#Scrape the new data
combined_df = pd.read_csv("Seasons.csv")

seasons = ["https://www.baseball-reference.com/leagues/majors/2019-schedule.shtml", "https://www.baseball-reference.com/leagues/majors/2020-schedule.shtml", "https://www.baseball-reference.com/leagues/majors/2021-schedule.shtml"]

#Get a list of the current boxscore links
df_boxscore_links = np.array(combined_df.Boxscore.value_counts().index).tolist()

bbref_boxscore_links = []

for season in seasons:
    bbref_boxscore_links.append(get_boxscore_links(season))

bbref_boxscore_links = list(itertools.chain(*bbref_boxscore_links))

for link in df_boxscore_links:
    bbref_boxscore_links.remove(link)

#If there are missing links, scrape them and add them to the dataframe
if len(bbref_boxscore_links):

    #defining the columns needed
    data_columns = ["Date", "Team", "Player", "Position", "AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24", "Boxscore"]

    #creating the CV
    new_cv = pd.DataFrame(columns = data_columns)

    new_cv = scrape_boxscore_data(bbref_boxscore_links, new_cv)

    combined_df = pd.concat([combined_df, new_cv])

    print(combined_df)

    combined_df.to_csv('Seasons.csv', line_terminator='\n', index=False)  

    combined_df = read_csv("Seasons.csv")



#Now that we have the most current version of the dataframe, we can predict the stats for every player on every team's last 2 games
teams = np.array(combined_df.Team.value_counts().index)

cols = ["AB", "R", "H", "RBI", "BB", "SO", "PA", "BA", "OBP", "SLG", "OPS", "WPA", "aLI", "WPA+", "WPA-", "RE24"]


#These lists will hold the stat averages for the players over their last 2 games, as well as the player names and the teams they play on
player_averages = []
player_names = []
player_teams = []


#Loop through every player on every team
for team in teams:
    team_games = combined_df.loc[combined_df["Team"] == team]
    dates = np.array(team_games.Date.value_counts().index)
    dates.sort()

    recent_games = pd.concat([(team_games.loc[team_games['Date'] == dates[-2]]), (team_games.loc[team_games['Date'] == dates[-1]])])

    players = np.array(recent_games.Player.value_counts().index)
    
    for player in players:
        average = []
        player_data = recent_games[recent_games.Player == player]

        for col in cols:
            col_average = "%.3f" % player_data.iloc[:len(player_data)][f"{col}"].mean()
            average.append(col_average)
        
        player_averages.append(average)
        player_names.append(player)
        player_teams.append(team)


#Load the model and input the data
pickle_in = open("OPSModel.pickle", "rb")
model = pickle.load(pickle_in)

predictions = model.predict(player_averages)

results = []

for x in range(len(predictions)):
    results.append(("%.3f" % predictions[x][0], player_names[x], player_teams[x]))

results.sort(key=lambda tuple: tuple[0], reverse=True)


#Write the output file, sorted by highest OPS to lowest 
output = open("output.txt", "w")
rank = 1
for player in results:
    output.write(str(rank) + " - ")
    output.write(str(player))
    output.write("\n")
    rank += 1
output.close()