# roblox_api.py - Roblox API Integration
import aiohttp
from typing import Optional, List, Dict

class RobloxAPI:
    def __init__(self):
        self.base_url = "https://users.roblox.com/v1"
        self.presence_url = "https://presence.roblox.com/v1"
        self.games_url = "https://games.roblox.com/v1"
        self.groups_url = "https://groups.roblox.com/v1"
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get Roblox user info by username"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/usernames/users",
                    json={"usernames": [username], "excludeBannedUsers": False}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("data") and len(data["data"]) > 0:
                            return data["data"][0]
                return None
            except Exception as e:
                print(f"Error fetching Roblox user by username: {e}")
                return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get Roblox user info by ID"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/users/{user_id}") as resp:
                    if resp.status == 200:
                        return await resp.json()
                return None
            except Exception as e:
                print(f"Error fetching Roblox user by ID: {e}")
                return None
    
    async def get_user_presence(self, user_ids: List[int]) -> Optional[Dict]:
        """Get presence info for users (online status, game they're in)"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.presence_url}/presence/users",
                    json={"userIds": user_ids}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                return None
            except Exception as e:
                print(f"Error fetching user presence: {e}")
                return None
    
    async def get_game_info(self, place_id: int) -> Optional[Dict]:
        """Get game information"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.games_url}/games/multiget-place-details?placeIds={place_id}"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and len(data) > 0:
                            return data[0]
                return None
            except Exception as e:
                print(f"Error fetching game info: {e}")
                return None
    
    async def get_user_groups(self, user_id: int) -> Optional[List[Dict]]:
        """Get groups a user is in"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.groups_url}/users/{user_id}/groups/roles"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", [])
                return None
            except Exception as e:
                print(f"Error fetching user groups: {e}")
                return None
    
    async def get_group_rank(self, user_id: int, group_id: int) -> Optional[Dict]:
        """Get user's rank in a specific group"""
        groups = await self.get_user_groups(user_id)
        if groups:
            for group in groups:
                if group.get("group", {}).get("id") == group_id:
                    return group.get("role")
        return None
    
    async def get_user_thumbnail(self, user_id: int, size: str = "150x150") -> str:
        """Get user's avatar thumbnail URL"""
        return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width={size.split('x')[0]}&height={size.split('x')[1]}&format=png"
    
    async def search_users(self, keyword: str, limit: int = 10) -> Optional[List[Dict]]:
        """Search for users by keyword"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/users/search?keyword={keyword}&limit={limit}"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", [])
                return None
            except Exception as e:
                print(f"Error searching users: {e}")
                return None