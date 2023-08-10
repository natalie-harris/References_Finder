from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options

import os
import time
import requests

# create a new Options object
chrome_options = Options()
# add the "--headless" argument
# chrome_options.add_argument("--headless")

download_dir = r'E:\NIMBioS\SBW\SBW Literature\References Finder'
prefs = {
    "download.default_directory": download_dir, 
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True  # It will not display PDF directly in chrome
}
chrome_options.add_experimental_option('prefs', prefs)

def wait_for_downloads_to_finish(download_dir, timeout=300):
    """
    Wait for the downloads in the provided directory to finish.
    Args:
        download_dir (str): The directory where Chrome saves downloads.
        timeout (int): Maximum time (in seconds) to wait for downloads to finish.
    Returns:
        bool: True if downloads finished within the timeout, False otherwise.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not any(fname.endswith('.crdownload') for fname in os.listdir(download_dir)):
            return True  # All downloads finished
        time.sleep(1)
    return False  # Timeout reached

def download_pdf(driver, link, download_dir):    
    # Navigate to the link to initiate download
    driver.get(link)

    time.sleep(1.5)
    
    # Wait for the download to finish
    if not wait_for_downloads_to_finish(download_dir):
        print("Warning: Not all downloads may have finished!")

def wait():
    input("Waiting... ")
    return

def is_link_valid(url):
    try:
        response = requests.head(url, allow_redirects=True)  # HEAD is faster than GET, since it doesn't download the body content
        return response.status_code == 200
    except requests.RequestException:
        return False

search_term = 'A recent spruce budworm outbreak in the Lower St. Lawrence and Gaspe Peninsula with reference to aerial spraying operations'
search_term = search_term.replace(' ', '+')
initial_url = 'https://google.com/'

# Set up Selenium driver
driver = webdriver.Chrome(options=chrome_options)
driver.get(initial_url)

wait()

new_url = f'https://scholar.google.com/scholar?q={search_term}'
driver.get(new_url)

try:
    pdf_link = driver.find_element(By.XPATH, "//a[contains(@href, 'download=true')]")
    href = pdf_link.get_attribute('href')
    if is_link_valid(href):
        download_pdf(driver, href, download_dir)
except NoSuchElementException:
    print("No PDF link found on the page.")

# Close the browser
driver.quit()