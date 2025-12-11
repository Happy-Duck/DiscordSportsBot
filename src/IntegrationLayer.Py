from SportsAPIClient import SportsAPIClient
import aiohttp
import asyncio
import unicodedata

class IntegrationLayer:
    
    def __init__(self):
        self.session = None
        self.sports_api_client = None
    
    # call this once in discord.py file
    async def initializer(self):
        self.session = aiohttp.ClientSession()
        self.sports_api_client = SportsAPIClient(self.session)
    
    async def string_match_algorithm(self, list_of_potential_player, first_name, last_name):
        first_name = first_name.lower()
        last_name = last_name.lower()
        
        trickled_list = []
        first_names = []
        # Then do exact search to see if the desired name is present
        for player in list_of_potential_player:
            if player['player']['firstname'] == None or player['player']['lastname'] == None:
                continue
            # normalize first and last name first
            normalized_first_name = unicodedata.normalize('NFD', player['player']['firstname']).lower()
            normalized_last_name = unicodedata.normalize('NFD', player['player']['lastname']).lower()
            
            player['player']['firstname'] =  normalized_first_name
            player['player']['lastname'] = normalized_last_name
            
            if (first_name in normalized_first_name and last_name in normalized_last_name):
                trickled_list.append(player)
                first_names.append(player['player']['firstname'])
        print("first_names")
        print(trickled_list)
        
        if (len(trickled_list) == 1):
            return trickled_list
        else:
            return first_names
    
    async def get_player_and_stats(self, first_name, last_name, season = 2023):
        best_player = []
        # if id exists in the cache you shouldn't need the first part
        
        # else use get_player
        list_of_potential_player = await self.sports_api_client.AF_get_player_profile(last_name)
        
        # process the error or get first person that pops up for now
        if (list_of_potential_player == 499 or list_of_potential_player == 500):
            return "failure", "Server is currently down. Please Come back Later"
        elif len(list_of_potential_player) == 0:
            return "failure", "No player with the first and last name exists. Please check if the first and last name spelling is correct"
        else:
            best_match = await self.string_match_algorithm(list_of_potential_player, first_name=first_name, last_name=last_name)
            if len(best_match) == 0:
                return "failure", "No player with the first and last name exists. Please check if the first and last name spelling is correct"
            elif len(best_match) > 1:
                matching_players =  ", ".join(best_match)
                return "failure", f"there's many players with the first name including {matching_players} Please retry with any one of these more precise first name"
            elif len(best_match) == 1:
                best_match = best_match[0]['player']
        
        # call the stats
        player_profile = await self.sports_api_client.AF_get_player_stat(id = best_match['id'], season = season)
        if (player_profile == 499 or player_profile == 500):
            return "failure", "Server is currently down. Please Come Back Later"
        elif len(list_of_potential_player) == 0:
            return "failure", f"The player didn't seem to play on {season}"
            
        # return player_profile, player_statistics 
        return player_profile[0]['player'], player_profile[0]['statistics']

# # for testing for now
# async def main():
#     first_name = "Lionel"
#     last_name = "Messi"

#     integration_layer = IntegrationLayer()           
#     await integration_layer.initializer()           

#     profile, stat = await integration_layer.get_player_and_stats(first_name, last_name)
#     # print(profile)
#     print(stat)
#     await integration_layer.session.close()

# asyncio.run(main())
