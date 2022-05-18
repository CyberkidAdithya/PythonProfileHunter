# Standard Python libraries.
# modules = ["argparse", "datetime", "json", "logging", "os", "random", "re", "sys", "time",]
# for module in modules:
#     exec("import {}".format(module))
import argparse
import datetime
import itertools    # Cyberkid
import json
import logging
import lxml.html    # Cyberkid
import os
import random
import re
import requests     # Cyberkid
import sys
import time

# Third party Python libraries.
import yagooglesearch

# def dummy():
#     import yagooglesearch
#     return
# dummy()

# Custom Python libraries.

__version__ = "1.0.0"

# Cyberkid begins
banner = '''
o--o           o-o            o-o        
|   |          |  \          |            
O--o    o  o   |   O   o-o    o-o     o-o 
|       |  |   |  /    | |       |   |    
o       o--O   o-o     o-o   o--o     o-o 
           |                              
        o--o                                
'''

print(banner)

# Cyberkid
def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = lxml.html.fromstring(response.text)
    proxies = set()
    for proxy_id in parser.xpath('//tbody/tr')[:100]:
        if proxy_id.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([proxy_id.xpath('.//td[1]/text()')[0], proxy_id.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return list(proxies)    # return list of https proxies

# Cyberkid
proxies = get_proxies()
print("{} proxies found!\nPROXY LIST: {}".format(len(proxies), proxies))
proxy_pool = itertools.cycle(proxies)

# Logging
ROOT_LOGGER = logging.getLogger("pydosc")
# ISO 8601 datetime format by default.
LOG_FORMATTER = logging.Formatter("%(asctime)s [%(processName)-12.12s] [%(threadName)-12.12s] [%(levelname)s] %(message)s")

# Setup file logging.
log_file_handler = logging.FileHandler("pydosc.py.log")
log_file_handler.setFormatter(LOG_FORMATTER)
ROOT_LOGGER.addHandler(log_file_handler)

# Setup console logging.
console_handler = logging.StreamHandler()
console_handler.setFormatter(LOG_FORMATTER)
ROOT_LOGGER.addHandler(console_handler)


class pydosc:
    """pydosc class object"""

    def __init__(
        self,
        google_dorks_file,
        domain="",
        # max_urls_per_dork=100,
        max_urls_per_dork=1,
        save_pydosc_results_to_json_file=False,
        proxies="",
        save_urls_to_file=True,
        # min_delay_secs=37,
        # max_delay_secs=60,
        min_delay_secs=1,
        max_delay_secs=10,
        disable_verify_ssl=False,
        verbosity=4,
    ):
        """Initialize pydosc class object."""

        # Run parameter checks.
        if not os.path.exists(google_dorks_file):
            print("Specify a valid file containing Google dorks with -g")
            sys.exit(0)

        if min_delay_secs < 0:
            print("Minimum delay between dork searches (-i) must be greater than 0")
            sys.exit(0)

        if max_delay_secs < 0:
            print("max_delay_secs (-x) must be greater than 0")
            sys.exit(0)

        if max_delay_secs <= min_delay_secs:
            print(
                "max_delay_secs (-x) must be greater than "
                "min_delay_secs (-i)"
            )
            sys.exit(0)

        if max_urls_per_dork < 0:
            print("max_urls_per_dork (-m) must be greater than 0")
            sys.exit(0)

        # All passed paramters look good, assign to the class object.
        self.google_dorks_file = google_dorks_file
        self.google_dorks = []
        # with open(google_dorks_file, "r") as fh:
        with open(google_dorks_file, "r", encoding='utf-8') as fh:
            for line in fh.read().splitlines():
                if line.strip():
                    self.google_dorks.append(line)
        self.domain = domain
        self.max_urls_per_dork = max_urls_per_dork  # maximum search result urls to return per dork
        self.save_pydosc_results_to_json_file = save_pydosc_results_to_json_file
        self.proxies = proxies.strip().strip(",").split(",")
        self.save_urls_to_file = save_urls_to_file
        self.min_delay_secs = min_delay_secs    # minimum delay between dork searches in seconds
        self.max_delay_secs = max_delay_secs    # maximum delay between dork searches in seconds
        self.disable_verify_ssl = disable_verify_ssl
        self.verbosity = verbosity

        # Fancy way of generating a list of 20 random values between min_delay_secs and
        # max_delay_secs.  A random value is selected between each different Google
        # dork search.
        """
        1) Generate a random list of values between min_delay_secs and
           max_delay_secs
        2) Round those values to the tenths place
        3) Re-case as a list
        4) Sort the list
        """
        self.delay_between_dork_searches_list = sorted(
            list(
                map(
                    lambda x: round(x, 1),
                    [
                        random.uniform(
                            min_delay_secs,
                            max_delay_secs,
                        )
                        for _ in range(20)
                    ],
                )
            )
        )

        self.base_file_name = f'pydosc_results_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
        # self.base_file_name = f'my_osint_links'
        self.total_urls_found = 0
        self.proxy_rotation_index = 0

        # Assign log level.
        ROOT_LOGGER.setLevel((6 - self.verbosity) * 10)

    def go(self):
        global proxy_pool   # Cyberkid
        """Start pydosc Google dork search."""

        initiation_timestamp = datetime.datetime.now().isoformat()

        ROOT_LOGGER.info(f"Initiation timestamp: {initiation_timestamp}")

        # Initialize starting dork number.
        dork_counter = 1

        total_dorks_to_search = len(self.google_dorks)

        # Initialize dictionary to track dork results.
        self.pydosc_results_dict = {
            "dorks": {},
            "initiation_timestamp": initiation_timestamp,
            "completion_timestamp": "",
        }

        for dork in self.google_dorks:

            # fmt: off
            self.pydosc_results_dict["dorks"][dork] = {
                "urls_size": 0,
                "urls": [],

            }
            # fmt: on

            try:
                dork = dork.strip()

                # Search for the URLs to collect.
                if self.domain:
                    query = f"site:{self.domain} {dork}"
                else:
                    query = dork

                """
                Google search web GUI message for large search string queries:
                    "the" (and any subsequent words) was ignored because we limit queries to 32 words.
                """
                # Search string is longer than 32 words.
                if len(query.split(" ")) > 32:
                    ignored_string = " ".join(query.split(" ")[32:])
                    ROOT_LOGGER.warning(
                        "Google limits queries to 32 words (separated by spaces):  Removing from search query: "
                        f"'{ignored_string}'"
                    )

                    # Update query variable.
                    updated_query = " ".join(query.split(" ")[0:32])

                    # If original query is in quotes, append a double quote to new truncated updated_query.
                    if query.endswith('"'):
                        updated_query = f'{updated_query}"'

                    ROOT_LOGGER.info(f"New search query: {updated_query}")

                    query = updated_query

                # Rotate through the list of proxies using modulus to ensure the index is in the self.proxies list.
                proxy_index = self.proxy_rotation_index % len(self.proxies)
                # proxy = self.proxies[proxy_index]     # Cyberkid
                proxy = "http://" + next(proxy_pool)    # Cyberkid
                self.proxy_rotation_index += 1

                # Instantiate a new yagooglesearch.SearchClient object for each Google dork.
                client = yagooglesearch.SearchClient(
                    query,
                    tbs="li:1",  # Verbatim search.
                    # num=100,  # Retrieve up to 100 Google search results at time.
                    # Max desired valid URLs to collect per dork.
                    # num = int(input("Enter the number of results you want (<50): ")),
                    num = 10,
                    max_search_result_urls_to_return=self.max_urls_per_dork,
                    proxy=proxy,
                    verify_ssl=not self.disable_verify_ssl,
                    verbosity=self.verbosity,
                )

                # Randomize the user agent for best results.
                client.assign_random_user_agent()

                ROOT_LOGGER.info(
                    f"Search ( {dork_counter} / {total_dorks_to_search} ) for Google dork [ {query} ] using "
                    f"User-Agent '{client.user_agent}' through proxy '{proxy}'"
                )

                dork_urls_list = client.search()

                # Remove any exploit-db.com URLs.
                for url in dork_urls_list:
                    # Ignore results from specific URLs like exploit-db.com, cert.org, and GHDB's Twitter account that
                    # may just be providing information about the vulnerability.  Keeping it simple with regex.
                    ignore_url_list = [
                        "https://www.kb.cert.org",
                        "https://www.exploit-db.com/",
                        "https://twitter.com/googlehacking/",
                        "https://linkedin.com/",    # requires account
                        "https://instagram.com/",   # requires account
                    ]
                    for ignore_url in ignore_url_list:
                        if re.search(ignore_url, url, re.IGNORECASE):
                            ROOT_LOGGER.warning(f"Removing {ignore_url} URL: {url}")
                            dork_urls_list.remove(url)

                dork_urls_list_size = len(dork_urls_list)

                # Google dork results found.
                if dork_urls_list:

                    ROOT_LOGGER.info(f"Results: {dork_urls_list_size} URLs found for Google dork: {dork}")

                    dork_urls_list_as_string = "\n".join(dork_urls_list)
                    ROOT_LOGGER.info(f"dork_urls_list:\n{dork_urls_list_as_string}")

                    self.total_urls_found += dork_urls_list_size

                    # Save URLs with valid results to an .txt file.
                    if self.save_urls_to_file:
                        with open(f"{self.base_file_name}.txt", "a") as fh:
                            print("writing.....")
                            fh.write(f"# {dork}\n")
                            for url in dork_urls_list:
                                fh.write(f"{url}\n")
                            fh.write("#" * 50 + "\n")

                    # fmt: off
                    self.pydosc_results_dict["dorks"][dork] = {
                        "urls_size": dork_urls_list_size,
                        "urls": dork_urls_list,
                    }
                    # fmt: on

                # No Google dork results found.
                else:
                    ROOT_LOGGER.info(f"Results: {dork_urls_list_size} URLs found for Google dork: {dork}")

            except KeyboardInterrupt:
                sys.exit(0)

            except Exception as e:
                ROOT_LOGGER.error(f"Error with dork: {dork}")
                ROOT_LOGGER.error(f"EXCEPTION: {e}")
                if type(e).__name__ == "SSLError" and (not self.disable_verify_ssl):
                    ROOT_LOGGER.info(
                        "If you are using self-signed certificates for an HTTPS proxy, try-rerunning with the -l "
                        "switch to disable verifying SSL/TLS certificates.  Exiting..."
                    )
                    sys.exit(1)

            dork_counter += 1

            # Only sleep if there are more dorks to search.
            if dork != self.google_dorks[-1]:
                pause_time = random.choice(self.delay_between_dork_searches_list)
                ROOT_LOGGER.info(f"Sleeping {pause_time} seconds before executing the next dork search...")
                time.sleep(pause_time)

        ROOT_LOGGER.info(
            f"Total URLs found for the {total_dorks_to_search} total dorks searched: {self.total_urls_found}"
        )

        completion_timestamp = datetime.datetime.now().isoformat()

        ROOT_LOGGER.info(f"Completion timestamp: {completion_timestamp}")
        self.pydosc_results_dict["completion_timestamp"] = completion_timestamp

        # Save pydosc_results_dict to a .json file.
        if self.save_pydosc_results_to_json_file:
            with open(f"{self.base_file_name}.json", "w") as fh:
                json.dump(self.pydosc_results_dict, fh, indent=4)

        return self.pydosc_results_dict


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=f"pydosc - Passive Google Dork v{__version__}")
    parser.add_argument(
        "-g", dest="google_dorks_file", action="store", required=True, help="File containing Google dorks, 1 per line."
    )
    parser.add_argument(
        "-d",
        dest="domain",
        action="store",
        required=False,
        help="Domain to scope the Google dork searches.  Not required.",
    )
    parser.add_argument(
        "-i",
        dest="min_delay_secs",
        action="store",
        required=False,
        type=int,
        # default=37,   # Cyberkid
        default=1,      # Cyberkid
        help="Minimum delay (in seconds) between a Google dork search.  Default: 37",
    )
    parser.add_argument(
        "-x",
        dest="max_delay_secs",
        action="store",
        required=False,
        type=int,
        # default=60,   # Cyberkid
        default=10,     # Cyberkid
        help="Maximum delay (in seconds) between a Google dork search.  Default: 60",
    )
    parser.add_argument(
        "-l",
        dest="disable_verify_ssl",
        action="store_true",
        required=False,
        default=False,
        help="Disable SSL/TLS validation.  Sometimes required if using an HTTPS proxy with self-signed certificates.",
    )
    parser.add_argument(
        "-m",
        dest="max_urls_per_dork",
        action="store",
        required=False,
        type=int,
        default=100,
        help="Maximum results to return per dork.  Default 100.",
    )
    parser.add_argument(
        "-p",
        dest="proxies",
        action="store",
        required=False,
        type=str,
        default="",
        help=(
            "Comma separated string of proxies to round-robin through.  Example: "
            "https://myproxy:8080,socks5h://127.0.0.1:9050,socks5h://127.0.0.1:9051 - The proxy scheme must confrom "
            "per the Python requests library: https://docs.python-requests.org/en/master/user/advanced/#proxies  See "
            "https://github.com/opsdisk/yagooglesearch for more information."
        ),
    )
    parser.add_argument(
        "-o",
        dest="save_pydosc_results_to_json_file",
        action="store_true",
        required=False,
        default=False,
        help=(
            "Save JSON dictionary to pydosc_results_<TIMESTAMP>.json file.  Contains more information than "
            "pydosc_results_<TIMESTAMP>.txt"
        ),
    )
    parser.add_argument(
        "-s",
        dest="save_urls_to_file",
        action="store_true",
        required=False,
        default=False,
        help="Save any URLS found for a dork to the pydosc_results_<TIMESTAMP>.txt file.",
    )
    parser.add_argument(
        "-v",
        dest="verbosity",
        action="store",
        type=int,
        default=4,
        help="Verbosity level (0=NOTSET, 1=CRITICAL, 2=ERROR, 3=WARNING, 4=INFO, 5=DEBUG).  Default: 4",
    )

    args = parser.parse_args()

    pydosc = pydosc(**vars(args))
    pydosc.go()

if not __name__ == '__main__':
    print("Hello World")
    initiation_timestamp = datetime.datetime.now().isoformat()

    ROOT_LOGGER.info(f"Initiation timestamp: {initiation_timestamp}")