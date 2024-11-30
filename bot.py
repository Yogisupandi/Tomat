from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout
)
from colorama import *
from datetime import datetime
from fake_useragent import FakeUserAgent
from faker import Faker
from dotenv import load_dotenv
import asyncio, json, os, re

# Load environment variables from .env
load_dotenv()

# Fetch REFF_CODE from environment
REFF_CODE = os.getenv("REFF_CODE")

class Tomarket:
    def __init__(self) -> None:
        self.faker = Faker()
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Host': 'api-web.tomarket.ai',
            'Origin': 'https://mini-app.tomarket.ai',
            'Pragma': 'no-cache',
            'Referer': 'https://mini-app.tomarket.ai/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': FakeUserAgent().random
        }

    @staticmethod
    def clear_terminal():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def print_timestamp(message):
        print(
            f"{Fore.BLUE + Style.BRIGHT}[ {datetime.now().astimezone().strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{message}",
            flush=True
        )

    async def process_queries(self, lines_per_file: int):
        if not os.path.exists('queries.txt'):
            raise FileNotFoundError("File 'queries.txt' Not Found. Please Ensure It Exists")

        queries = [line.strip() for line in open('queries.txt', 'r') if line.strip()]
        if not queries:
            raise ValueError("File 'queries.txt' Is Empty")

        account_files = [f for f in os.listdir() if f.startswith('accounts-') and f.endswith('.json')]
        account_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0])) if account_files else []

        existing_accounts = {}
        for account_file in account_files:
            accounts_data = json.load(open(account_file, 'r'))
            accounts = accounts_data.get('accounts', [])
            for account in accounts:
                existing_accounts[account['first_name']] = account['token']

        for account_file in account_files:
            accounts_data = json.load(open(account_file, 'r'))
            accounts = accounts_data.get('accounts', [])

            new_accounts = []
            token_data_list = await self.generate_tokens(queries)
            for token_data in token_data_list:
                first_name = token_data['first_name']
                if first_name in existing_accounts:
                    for account in accounts:
                        if account['first_name'] == first_name:
                            account['token'] = token_data['token']
                else:
                    new_accounts.append(token_data)
                    existing_accounts[first_name] = token_data['token']

            accounts.extend(new_accounts)
            accounts = accounts[:lines_per_file]
            accounts_data['accounts'] = accounts

            if new_accounts:
                json.dump(accounts_data, open(account_file, 'w'), indent=4)
                self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ Updated '{account_file}' With {len(new_accounts)} New Token And Name ]{Style.RESET_ALL}")

            queries = queries[len(new_accounts):]
            if len(queries) == 0:
                break

        last_file_number = int(re.findall(r'\d+', account_files[-1])[0]) if account_files else 0

        for i in range(0, len(queries), lines_per_file):
            chunk = queries[i:i + lines_per_file]
            new_accounts = await self.generate_tokens(chunk)
            new_accounts = [acc for acc in new_accounts if acc['first_name'] not in existing_accounts]

            if new_accounts:
                last_file_number += 1
                accounts_file = f"accounts-{last_file_number}.json"

                for account in new_accounts:
                    existing_accounts[account['first_name']] = account['token']

                json.dump({'accounts': new_accounts}, open(accounts_file, 'w'), indent=4)
                self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ Successfully Generated Tokens In '{accounts_file}' ]{Style.RESET_ALL}")

    async def load_from_json(self, file_path):
        try:
            return [(account['token'], account['first_name']) for account in json.load(open(file_path, 'r'))['accounts']]
        except Exception as e:
            self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Error Occurred While Loading JSON: {str(e)} ]{Style.RESET_ALL}")
            return []

    async def generate_token(self, query: str):
        url = 'https://api-web.tomarket.ai/tomarket-game/v1/user/login'
        data = json.dumps({'init_data':query,'invite_code':REFF_CODE,'from':'','is_bot':False})
        headers = {
            **self.headers,
            'Content-Length': str(len(data)),
            'Content-Type': 'application/json'
        }
        await asyncio.sleep(3)
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                    response.raise_for_status()
                    generate_token = await response.json()
                    access_token = generate_token['data']['access_token']
                    first_name = generate_token['data']['fn'] or self.faker.first_name()
                    return {'token': access_token, 'first_name': first_name}
        except (Exception, ClientResponseError) as e:
            self.print_timestamp(
                f"{Fore.YELLOW + Style.BRIGHT}[ Failed To Process {query} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.RED + Style.BRIGHT}[ {str(e)} ]{Style.RESET_ALL}"
            )
            return None

    async def generate_tokens(self, queries):
        tasks = [self.generate_token(query) for query in queries]
        results = await asyncio.gather(*tasks)
        return [result for result in results if result is not None]
    
    async def input_reff_code(self, token):
        url = f"https://api-web.tomarket.ai/tomarket-game/v1/user/inviteCode"
        data = json.dumps({'invite_code':REFF_CODE})
        headers = {
            **self.headers,
            'Authorization': token,
            'Content-Length': str(len(data)),
            'Content-Type': 'application/json'
        }
        print(data)
        
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.post(url=url, headers=headers, data=data, ssl=False) as response:
                    response.raise_for_status()
                    result = await response.json()
                    if result['status'] == 0:
                        self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ Success Join Treasure Box with Reff Code: {REFF_CODE} ]{Style.RESET_ALL}")
                        await self.claim_treasure_box(token)
                    else:
                        return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Failed to Join Treasure Box: {result['message']} ]{Style.RESET_ALL}")
        except ClientResponseError as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Join Treasure Box: {str(e)} ]{Style.RESET_ALL}")
        except Exception as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Join Treasure Box: {str(e)} ]{Style.RESET_ALL}")
    
    async def claim_treasure_box(self, token):
        url = f"https://api-web.tomarket.ai/tomarket-game/v1//invite/openTreasureBox"
        headers = {
            **self.headers,
            'Authorization': token,
            'Content-Length': '0',
            'Content-Type': 'application/json'
        }
        
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.post(url=url, headers=headers, ssl=False) as response:
                    response.raise_for_status()
                    result = await response.json()
                    if result['status'] == 0:
                        return self.print_timestamp(f"{Fore.GREEN + Style.BRIGHT}[ You\'ve Got {result['data']['toma_reward']} $TOMA From Treasure Box ]{Style.RESET_ALL}")
                    else:
                        return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ Failed to Claim Treasure Box: {result['message']} ]{Style.RESET_ALL}")
        except ClientResponseError as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An HTTP Error Occurred While Claim Treasure Box: {str(e)} ]{Style.RESET_ALL}")
        except Exception as e:
            return self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ An Unexpected Error Occurred While Claim Treasure Box: {str(e)} ]{Style.RESET_ALL}")
    
    async def main(self, accounts):
        while True:
            try:
                self.print_timestamp(
                    f"{Fore.CYAN + Style.BRIGHT}[ Total Account {len(accounts)} ]{Style.RESET_ALL}"
                )

                for (token, first_name) in accounts:
                    self.print_timestamp(
                        f"{Fore.WHITE + Style.BRIGHT}[ Home ]{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT}[ {first_name} ]{Style.RESET_ALL}"
                    )
                    await self.input_reff_code(token=token)
                    await asyncio.sleep(1)

                self.print_timestamp(
                    f"{Fore.CYAN + Style.BRIGHT}[ Finished Processing All Account ]{Style.RESET_ALL}"
                )
                await asyncio.sleep(3)
                self.clear_terminal()   
            except Exception as error:
                self.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ {str(error)} ]{Style.RESET_ALL}")
                continue

if __name__ == '__main__':
    try:
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        init(autoreset=True)
        tomarket = Tomarket()
        tomarket.print_timestamp(
            f"{Fore.GREEN + Style.BRIGHT}[ 1 ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.BLUE + Style.BRIGHT}[ Generate Tokens ]{Style.RESET_ALL}"
        )
        tomarket.print_timestamp(
            f"{Fore.GREEN + Style.BRIGHT}[ 2 ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.BLUE + Style.BRIGHT}[ Use Existing accounts-*.json ]{Style.RESET_ALL}"
        )

        initial_choice = int(input(
            f"{Fore.BLUE + Style.BRIGHT}[ {datetime.now().astimezone().strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.YELLOW + Style.BRIGHT}[ Select Option ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
        ))
        if initial_choice == 1:
            lines_per_file = int(input(
                f"{Fore.BLUE + Style.BRIGHT}[ {datetime.now().astimezone().strftime('%x %X %Z')} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.YELLOW + Style.BRIGHT}[ How Much Accounts Each 'accounts-*.json'? ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            ))
            if lines_per_file <= 0:
                raise ValueError("The Number Must Be Greater Than Zero.")
            asyncio.run(tomarket.process_queries(lines_per_file=lines_per_file))

            account_files = [f for f in os.listdir() if f.startswith('accounts-') and f.endswith('.json')]
            account_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))
            if not account_files:
                raise FileNotFoundError("No 'accounts-*.json' Files Found In The Directory. Please Generate Tokens First By Selecting Option 1.")
        elif initial_choice == 2:
            account_files = [f for f in os.listdir() if f.startswith('accounts-') and f.endswith('.json')]
            account_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))
            if not account_files:
                raise FileNotFoundError("No 'accounts-*.json' Files Found In The Directory. Please Generate Tokens First By Selecting Option 1.")
        else:
            raise ValueError("Invalid Initial Choice. Please Run The Script Again And Choose A Valid Option")

        for i, accounts_file in enumerate(account_files, start=1):
            tomarket.print_timestamp(
                f"{Fore.GREEN + Style.BRIGHT}[ {i} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}[ {accounts_file} ]{Style.RESET_ALL}"
            )

        choice = int(input(
            f"{Fore.BLUE + Style.BRIGHT}[ {datetime.now().astimezone().strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.YELLOW + Style.BRIGHT}[ Select File You Want To Use ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
        )) - 1
        if choice < 0 or choice >= len(account_files):
            raise ValueError("Invalid Choice. Please Run The Script Again And Choose A Valid Option")

        selected_accounts_file = account_files[choice]
        accounts = asyncio.run(tomarket.load_from_json(selected_accounts_file))

        asyncio.run(tomarket.main(accounts))
    except (ValueError, IndexError, FileNotFoundError) as e:
        tomarket.print_timestamp(f"{Fore.RED + Style.BRIGHT}[ {str(e)} ]{Style.RESET_ALL}")
    except KeyboardInterrupt:
        sys.exit(0)