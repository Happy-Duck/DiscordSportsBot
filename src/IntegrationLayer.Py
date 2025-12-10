from SportsAPIClient import SportsAPIClient
import aiohttp
import asyncio

class IntegrationLayer:
    
    def __init__(self):
        self.session = None
        self.sports_api_client = None
    
    # call this once in discord.py file
    async def initializer(self):
        self.session = aiohttp.ClientSession()
        self.sports_api_client = SportsAPIClient(self.session)
    
    async def get_player(self, first_name, last_name):
        # get player profile through last name and go through the list of player 
        list_of_potential_player = await self.sports_api_client.AF_get_player_profile(last_name)
        
        # process the error or get first person that pops up for now
        if (list_of_potential_player == 499 or list_of_potential_player == 500):
            return "Server is currently down. Please Come back Later"
        elif len(list_of_potential_player) == 0:
            return "No player with the last name exists. Please check if the last name spelling is correct"
        else:
            best_match = await self.fuzzy_algorithm(list_of_potential_player, first_name, last_name)
        
        return best_match
    
    
    async def get_player_and_stats(self, first_name, last_name, season = 2023):
        best_player = []
        # if id exists in the cache you shouldn't need the first part
        
        # else use get_player
        list_of_potential_player = await self.sports_api_client.AF_get_player_profile(last_name)
        
        # process the error or get first person that pops up for now
        if (list_of_potential_player == 499 or list_of_potential_player == 500):
            return "Server is currently down. Please Come back Later"
        elif len(list_of_potential_player) == 0:
            return "No player with the last name exists. Please check if the last name spelling is correct"
        else:
            best_match = await self.fuzzy_algorithm(list_of_potential_player, first_name=first_name, last_name=last_name)
        
        # call the stats
        player_profile = await self.sports_api_client.AF_get_player_stat(id = best_match['id'], season = season)
        if (player_profile == 499 or player_profile == 500):
            return "Server is currently down. Please Come Back Later"
        elif len(list_of_potential_player) == 0:
            return f"The player didn't seem to play on {season}"
            
        # return player_profile, player_statistics 
        return player_profile[0]['player'], player_profile[0]['statistics']

    # helper function I'm currently working on to give best matching player not yet done
    async def fuzzy_algorithm(self, list_of_potential_player, first_name, last_name):
        return list_of_potential_player[0]['player']


# # for testing for now
# async def main():
#     first_name = "Federico"
#     last_name = "Bernardeschi"

#     integration_layer = IntegrationLayer()           
#     await integration_layer.initializer()           

#     profile, stat = await integration_layer.get_player_and_stats(first_name, last_name)
#     # print(profile)
#     print(stat)
#     await integration_layer.session.close()

# asyncio.run(main())
