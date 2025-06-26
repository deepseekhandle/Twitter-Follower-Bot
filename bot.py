import aiohttp
import asyncio
import random
import logging
import re
from datetime import datetime
import sys
import os
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

# Constants
AUTH_URL = "https://takipciyurdu.com/api/twitter-takipci/auth"
CREDIT_URL = "https://takipciyurdu.com/api/twitter-takipci/credit"
FOLLOW_URL = "https://takipciyurdu.com/api/twitter-takipci/follow"
REFERRER = "https://takipciyurdu.com/twitter/twitter-takipci-hilesi"

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    handlers=[
        logging.FileHandler('follower_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class FollowerPanel:
    def __init__(self, total_follows):
        self.total_follows = total_follows
        self.completed = 0
        self.failed = 0
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        
    def update(self, success=True):
        if success:
            self.completed += 1
        else:
            self.failed += 1
        self.last_update = datetime.now()
        self.display()
        
    def display(self):
        # Clear console
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Calculate progress
        progress = (self.completed + self.failed) / self.total_follows * 100
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time = elapsed / (self.completed + self.failed) if (self.completed + self.failed) > 0 else 0
        remaining = (self.total_follows - (self.completed + self.failed)) * avg_time
        
        # Build the panel
        print(Fore.CYAN + "╔══════════════════════════════════════════════════╗")
        print(Fore.CYAN + "║" + Fore.YELLOW + "          TWITTER FOLLOWER BOT - STATUS PANEL       " + Fore.CYAN + "║")
        print(Fore.CYAN + "╠══════════════════════════════════════════════════╣")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Total Follows: {Fore.GREEN}{self.total_follows}".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Completed: {Fore.GREEN}{self.completed}".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Failed: {Fore.RED}{self.failed}".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Progress: {Fore.YELLOW}{progress:.1f}%".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Elapsed Time: {Fore.BLUE}{self.format_time(elapsed)}".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Estimated Remaining: {Fore.BLUE}{self.format_time(remaining)}".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "║" + Fore.WHITE + f" Last Update: {Fore.MAGENTA}{self.last_update.strftime('%H:%M:%S')}".ljust(50) + Fore.CYAN + "║")
        print(Fore.CYAN + "╚══════════════════════════════════════════════════╝")
        print("\n" + Fore.YELLOW + "Status: " + ("Running" if (self.completed + self.failed) < self.total_follows else "Completed"))
        
    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

async def get_auth_session():
    """Get authorization session details"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(AUTH_URL, headers={"accept": "application/json"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "token": data.get("token"),
                        "secret": data.get("secret"),
                        "apiId": data.get("apiId"),
                        "url": data.get("url").replace("twitter.com", "x.com")
                    }
                else:
                    error_msg = f"Failed to fetch auth URL. Status: {resp.status}"
                    logger.error(error_msg)
                    print(Fore.RED + error_msg)
                    return None
        except Exception as e:
            error_msg = f"Error getting auth session: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(Fore.RED + error_msg)
            return None

async def verify_pin_and_get_token(pin_code, session_data):
    """Verify PIN code and get access token"""
    payload = {
        "pinCode": pin_code,
        "token": session_data["token"],
        "secret": session_data["secret"],
        "ref_id": None,
        "apiId": session_data["apiId"]
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "referer": REFERRER,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(AUTH_URL, headers=headers, json=payload) as auth_resp:
                if auth_resp.status != 200:
                    error_msg = await auth_resp.text()
                    logger.error(f"PIN verification failed. Status: {auth_resp.status}. Error: {error_msg}")
                    print(Fore.RED + f"PIN verification failed: {error_msg}")
                    return None

                auth_json = await auth_resp.json()
                access_token = auth_json.get("accessToken") or auth_json.get("token") or auth_json.get("access_token")
                
                if not access_token:
                    error_msg = "Access token missing in API response"
                    logger.error(error_msg)
                    print(Fore.RED + error_msg)
                    return None
                
                return access_token
    except Exception as e:
        error_msg = f"Error during PIN verification: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(Fore.RED + error_msg)
        return None

async def get_credit_info(access_token):
    """Get user's credit information with detailed response"""
    headers = {
        "accept": "*/*",
        "authorization": f"bearer {access_token}",
        "referer": f"{REFERRER}/profile",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CREDIT_URL, headers=headers) as credit_resp:
                if credit_resp.status == 200:
                    credit_data = await credit_resp.json()
                    logger.info(f"Credit API Response: {credit_data}")
                    
                    credit = credit_data.get("credit")
                    message = credit_data.get("message", "No message")
                    refId = credit_data.get("refId", "N/A")
                    
                    print(Fore.GREEN + f"Credit Available: {credit}")
                    print(Fore.CYAN + f"API Message: {message}")
                    return credit, message
                
                error_msg = await credit_resp.text()
                logger.error(f"Credit check failed. Status: {credit_resp.status}. Error: {error_msg}")
                print(Fore.RED + f"Credit check failed: {error_msg}")
                return None, f"API Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error getting credit info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(Fore.RED + error_msg)
        return None, str(e)

async def send_follow_requests(access_token, credit):
    """Send follow requests with proper list checking"""
    headers = {
        "accept": "*/*",
        "authorization": f"bearer {access_token}",
        "referer": f"{REFERRER}/profile",
    }

    panel = FollowerPanel(credit)
    panel.display()

    try:
        async with aiohttp.ClientSession() as session:
            # First check if there are available accounts to follow
            async with session.get("https://takipciyurdu.com/api/twitter-takipci/list", 
                                 headers=headers) as list_resp:
                if list_resp.status != 200:
                    error_msg = await list_resp.text()
                    logger.error(f"List check failed. Status: {list_resp.status}. Error: {error_msg}")
                    return False, "Failed to check available accounts"
                
                list_data = await list_resp.json()
                pending_count = list_data.get("pendingListCount", 0)
                
                if pending_count <= 0:
                    return False, "No accounts available to follow (empty list)"
                
                logger.info(f"Found {pending_count} accounts available for following")

            # Now proceed with follow requests
            for i in range(credit):
                try:
                    # Check list again every 5 follows
                    if i > 0 and i % 5 == 0:
                        async with session.get("https://takipciyurdu.com/api/twitter-takipci/list", 
                                             headers=headers) as list_check:
                            if list_check.status == 200:
                                check_data = await list_check.json()
                                if check_data.get("pendingListCount", 0) <= 0:
                                    return True, f"Stopped early - no more accounts. Completed {i}/{credit} follows"
                    
                    async with session.post(FOLLOW_URL, headers=headers) as follow_resp:
                        if follow_resp.status != 200:
                            error_msg = await follow_resp.text()
                            logger.error(f"Follow {i+1}/{credit} failed. Status: {follow_resp.status}. Error: {error_msg}")
                            panel.update(success=False)
                            continue

                        follow_data = await follow_resp.json()
                        if follow_data.get("code") == 1:
                            panel.update(success=True)
                        else:
                            logger.warning(f"Follow {i+1}/{credit} returned non-success code. Response: {follow_data}")
                            panel.update(success=False)

                        # Random delay between 5-7 seconds
                        await asyncio.sleep(random.uniform(5, 7))
                except Exception as e:
                    logger.error(f"Error sending follow {i+1}/{credit}: {str(e)}")
                    panel.update(success=False)
                    continue

            return True, f"Completed {panel.completed}/{credit} follows successfully"

    except Exception as e:
        error_msg = f"Fatal error in follow process: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(Fore.RED + error_msg)
        return False, str(e)

async def main_flow():
    """Main workflow with improved error handling and logging"""
    print(Fore.YELLOW + "╔══════════════════════════════════════════════════╗")
    print(Fore.YELLOW + "║" + Fore.CYAN + "          TWITTER FOLLOWER BOT - STARTING          " + Fore.YELLOW + "║")
    print(Fore.YELLOW + "╚══════════════════════════════════════════════════╝")
    
    # Step 1: Get authorization
    print(Fore.CYAN + "\n[1/4] Getting authorization URL...")
    session_data = await get_auth_session()
    if not session_data:
        return

    print(Fore.GREEN + f"\nPlease visit this URL to authorize: {session_data['url']}")
    print(Fore.YELLOW + "After authorization, you'll receive a 7-digit PIN code")
    
    # Step 2: Get PIN from user
    while True:
        pin_code = input(Fore.CYAN + "\nEnter the 7-digit PIN: ").strip()
        if re.fullmatch(r"\d{7}", pin_code):
            break
        print(Fore.RED + "Invalid PIN format. Must be exactly 7 digits.")

    # Step 3: Verify PIN
    print(Fore.CYAN + "\n[2/4] Verifying PIN...")
    access_token = await verify_pin_and_get_token(pin_code, session_data)
    if not access_token:
        return

    # Step 4: Check credit
    print(Fore.CYAN + "\n[3/4] Checking available credit...")
    credit, message = await get_credit_info(access_token)
    
    if credit is None:
        return
        
    if credit <= 0:
        print(Fore.RED + "No sufficient credit available")
        return

    # Step 5: Confirm before proceeding
    confirm = input(Fore.CYAN + f"\n[4/4] Ready to send {credit} follows? (y/n): ").lower()
    if confirm != 'y':
        print(Fore.YELLOW + "Operation cancelled by user")
        return

    # Step 6: Send follows
    print(Fore.GREEN + "\nStarting follow process...")
    success, result = await send_follow_requests(access_token, credit)
    
    if success:
        print(Fore.GREEN + f"\n{result}")
    else:
        print(Fore.RED + f"\nFollow process failed: {result}")

    print(Fore.YELLOW + "\nProcess completed. Check follower_bot.log for details.")

if __name__ == "__main__":
    try:
        asyncio.run(main_flow())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nProcess interrupted by user")
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(Fore.RED + error_msg)
    finally:
        input(Fore.CYAN + "\nPress Enter to exit...")